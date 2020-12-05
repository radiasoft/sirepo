# -*- coding: utf-8 -*-
u"""API's for jupyterhublogin sim

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
import flask
import py.error
import random
import re
import sirepo.api_perm
import sirepo.auth
import sirepo.auth_db
import sirepo.events
import sirepo.http_reply
import sirepo.http_request
import sirepo.srdb
import sirepo.uri_router
import sirepo.util
import sqlalchemy
import string

cfg = None

#: Used by auth_db. Sirepo record of each jupyterhub user.
JupyterhubUser = None

_HUB_USER_SEP = '_'


@sirepo.api_perm.require_user
def api_migrateJupyterhub():
    if not cfg.rs_jupyter_migrate:
        sirepo.util.raise_forbidden('migrate not enabled')
    d = sirepo.http_request.parse_json()
    if not d.doMigration:
        return sirepo.http_reply.gen_redirect('jupyterHub')
    return sirepo.uri_router.call_api(
        'authGithubLogin',
        kwargs=PKDict(simulation_type='jupyterhublogin'),
    )


@sirepo.api_perm.require_user
def api_redirectJupyterHub():
    is_new_user = _create_user_if_not_found()
    if not cfg.rs_jupyter_migrate or not is_new_user:
        return sirepo.http_reply.gen_redirect('jupyterHub')
    return sirepo.http_reply.gen_json_ok()


def unchecked_jupyterhub_user_name(have_simulation_db=True):
    return _unchecked_hub_user(sirepo.auth.logged_in_user(check_path=have_simulation_db))


def init_apis(*args, **kwargs):
    global cfg

    cfg = pkconfig.init(
        user_db_root_d=(
            pkio.py_path(sirepo.srdb.root()).join('jupyterhub', 'user'),
            pkio.py_path,
            'Jupyterhub user db',
        ),
        rs_jupyter_migrate=(False, bool, 'give user option to migrate data from jupyter.radiasoft.org'),
        uri_root=('jupyter', str, 'the root uri of jupyterhub'),
    )
    pkio.mkdir_parent(cfg.user_db_root_d)
    sirepo.auth_db.init_model(_init_model)
    sirepo.events.register(PKDict(
        auth_logout=_event_auth_logout,
        end_api_call=_event_end_api_call,
    ))
    if cfg.rs_jupyter_migrate:
        sirepo.events.register(PKDict(
            github_authorized=_event_github_authorized,
        ))


def _create_user_if_not_found():
    def __user_name(logged_in_user_name):
        assert logged_in_user_name, 'must supply a name'
        n = re.sub(
            '\W+',
            _HUB_USER_SEP,
            # Get the local part of the email. Or in the case of another auth
            # method (ex github) it won't have an '@' so it will just be their
            # user name, handle, etc.
            logged_in_user_name.split('@')[0],
        )
        u = JupyterhubUser.search_by(user_name=n)
        if u or _user_dir(user_name=n).exists():
            # The username already exists. Add a random letter to try and create
            # a unique user name.
            n += _HUB_USER_SEP + sirepo.util.random_base62(3).lower()

        assert not _user_dir(user_name=n).exists(), \
            f'conflict with existing user_dir={n}'
        return n

    if unchecked_jupyterhub_user_name():
        return False
    with sirepo.auth_db.thread_lock:
        JupyterhubUser(
            uid=sirepo.auth.logged_in_user(),
            user_name=__user_name(sirepo.auth.user_name()),
        ).save()
    pkio.mkdir_parent(_user_dir())
    return True


def _event_auth_logout(kwargs):
    flask.g.jupyterhub_logout_user_name = _unchecked_hub_user(kwargs.uid)


def _event_end_api_call(kwargs):
    u = flask.g.get('jupyterhub_logout_user_name', None)
    if not u:
       return
    for c in (
            ('jupyterhub-hub-login', 'hub'),
            (f'jupyterhub-user-{u}', f'user/{u}'),
    ):
        kwargs.resp.delete_cookie(
            c[0],
            # Trailing slash is required in paths
            path=f'/{cfg.uri_root}/{c[1]}/',
        )


def _event_github_authorized(kwargs):
    d = _user_dir()
    JupyterhubUser.update_user_name(
        sirepo.auth.logged_in_user(),
        kwargs.user_name,
    )
    pkio.unchecked_remove(d)
    # User may not have been a user originally so need to create their dir.
    # If it exists (they were a user) it is a no-op.
    pkio.mkdir_parent(_user_dir())
    raise sirepo.util.Redirect('jupyter')


def _init_model(base):
    global JupyterhubUser

    class JupyterhubUser(base):
        __tablename__ = 'jupyterhub_user_t'
        uid = sqlalchemy.Column(base.STRING_ID, primary_key=True)
        user_name = sqlalchemy.Column(
            base.STRING_NAME,
            nullable=False,
            unique=True,
        )

        @classmethod
        def update_user_name(cls, uid, user_name):
            with sirepo.auth_db.thread_lock:
                cls._session.query(cls).get(uid).user_name = user_name
                cls._session.commit()

def _unchecked_hub_user(uid):
    with sirepo.auth_db.thread_lock:
        u = JupyterhubUser.search_by(uid=uid)
        if u:
            return u.user_name
        return None


def _user_dir(user_name=None):
    if not user_name:
        user_name = unchecked_jupyterhub_user_name()
        assert user_name, 'must have user to get dir'
    return cfg.user_db_root_d.join(user_name)
