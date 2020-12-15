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
        _create_user()
        return sirepo.http_reply.gen_redirect('jupyterHub')
    return sirepo.uri_router.call_api(
        'authGithubLogin',
        kwargs=PKDict(simulation_type='jupyterhublogin'),
    )

@sirepo.api_perm.require_user
def api_redirectJupyterHub():
    u = unchecked_jupyterhub_user_name()
    if u:
        return sirepo.http_reply.gen_redirect('jupyterHub')
    if not cfg.rs_jupyter_migrate:
        if not u:
            _create_user()
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


def _create_user(github_handle=None, add_randomness=True):
    """Create a Jupyter user and possibly migrate their data from old jupyter.

    Keywords:
      migration user: A user with data at the old jupyter
      jupyter user: The user of new jupyter

    A few interesting cases to keep in mind:
      1. User selects to migrate and they have old data. We should never add
         randomness to the user's github handle because we need it to identify
         their user dir.
      2. User signs into sirepo under one@any.com. They migrate their data using
         GitHub handle y. They sign into sirepo under two@any.com. They choose
         to migrate GitHub handle y again. We should let them know that they
         have already migrated.
      3. one@any.com signs up for jupyter and does not migrate data. They are
         given the username one. two@any.com signs up for jupyter and they
         migrate their data. They have the github handle one. They should be
         alerted that they can't migrate that GitHub handle.

    Args:
        github_handle (str): The user's github handle
        add_randomness (bool): Whether or not to add_randomness to the username if needed

    """
    def __existing_migration_user_new_jupyter_user(github_handle):
        return github_handle and _user_dir(user_name=github_handle).exists() \
            and not JupyterhubUser.search_by(user_name=github_handle)

    def __user_name():
        n = github_handle or sirepo.auth.user_name()
        assert n, 'must supply a name'
        if __existing_migration_user_new_jupyter_user(github_handle):
            # TODO(e-carlin): If the new jupyter user changes their handle to be
            # the handle of an existing but unmigrated migration user then the
            # new jupyter user will get the data of the existing migration user.
            # No way to protect against this.
            return n
        if not github_handle:
            n = re.sub(
                '\W+',
                _HUB_USER_SEP,
                # Get the local part of the email. Or in the case of another auth
                # method (ex github) it won't have an '@' so it will just be their
                # user name, handle, etc.
                n.split('@')[0],
            )
        if __user_name_exists(n) and add_randomness:
            # The username already exists. Add some randomness to try and create
            # a unique user name.
            n += _HUB_USER_SEP + sirepo.util.random_base62(3).lower()
        if __user_name_exists(n):
            pkdlog(f'conflict with existing user_name={n}')
            raise sirepo.util.SRException(
                'jupyterNameConflict',
                PKDict(
                    sim_type='jupyterhublogin',
                    isMigration=bool(github_handle),
                ),
            )
        return n

    def __user_name_exists(user_name):
        return JupyterhubUser.search_by(user_name=user_name) \
            or _user_dir(user_name=user_name).exists()

    # Only add randomness when specified or to GitHub handles that we don't have
    # record of. *DO NOT* add randomness to handles we have record of. The handle
    # needs to be used to identify the user dir.
    add_randomness = add_randomness or \
        (github_handle and not __user_name_exists(github_handle))
    with sirepo.auth_db.thread_lock:
        JupyterhubUser(
            uid=sirepo.auth.logged_in_user(),
            user_name=__user_name(),
        ).save()
        pkio.mkdir_parent(_user_dir())


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
    n = kwargs.user_name
    _create_user(github_handle=n, add_randomness=False)
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
