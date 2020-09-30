# -*- coding: utf-8 -*-
u"""API's for jupyterhublogin sim

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig, pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
import py.error
import re
import random
import sirepo.api_perm
import sirepo.auth
import sirepo.auth_db
import sirepo.auth_db
import sirepo.events
import sirepo.http_reply
import sirepo.http_request
import sirepo.jupyterhub
import sirepo.srdb
import sirepo.uri_router
import sirepo.util
import string
import sqlalchemy

cfg = None

JupyterhubUser = None


@sirepo.api_perm.require_user
def api_migrateRsJupyterhubData(simulation_type):
    _create_user()
    return sirepo.uri_router.call_api(
            'authGithubLogin',
            kwargs=PKDict(simulation_type=simulation_type),
        )


@sirepo.api_perm.require_user
def api_redirectJupyterHub():
    _create_user()
    return sirepo.http_reply.gen_redirect('jupyterHub')

def _event_logout():
   flask.g.jupyterhub_logout = True

def _event_end_api(resp):
   # if flask.g.jupyterhub_logout:
   #     resp.delete_cookie(...jupyterhub)
    # TODO(e-carlin): remove jupyter cookies
    pass

def logged_in_user_name():
    with sirepo.auth_db.thread_lock:
        u = JupyterhubUser.search_by(
            uid=sirepo.auth.logged_in_user(check_path=False),
        )
        if u:
            return u.user_name
        return None


def init_apis(*args, **kwargs):
    # TODO(e-carlin): register a logout api with events
    global cfg

    if cfg:
        return
    cfg = pkconfig.init(
        dst_db_root=(
            pkio.py_path(sirepo.srdb.root()).join('jupyterhub'),
            pkio.py_path,
            'existing jupyter user db (ex /srv/jupyterhub)',
        ),
        src_db_root=(
            pkio.py_path('/dev/null'),
            pkio.py_path,
            'new jupyter user db',
        ),
        uri_root=('jupyter', str, 'the root uri of jupyterhub'),
    )
    sirepo.auth_db.init_model(_init_model)
    sirepo.events.register(
        sirepo.events.GITHUB_AUTHORIZED,
        _handle_github_authorized,
    )

# TODO(e-carlin): sort
def _handle_github_authorized(kwargs):
    with sirepo.auth_db.thread_lock:
        s = cfg.src_db_root.join(kwargs.user_name)
        u = logged_in_user_name()
        assert u, 'need logged in JupyterhubUser'
        d = cfg.dst_db_root.join(u)
        try:
            # TODO(e-carlin): use rename not move since on same partition py_path.rename (maybe os.rename)
            s.rename(d)
        except py.error.ENOTDIR:
            # TODO(e-carlin): Maybe raise an error letting the user know
            # They may have given the wrong github creds
            pkdlog(
                'Tried to migrate existing rs jupyter directory={} but not found. Ignoring.',
                s,
            )
            pkio.mkdir_parent(d)
    # TODO(e-carlin): /jupyter /juptyerHub ???
    raise sirepo.util.Redirect('jupyter')

def _create_user():
    def __user_name(logged_in_user_name):
        n = re.sub(
            '\W+',
            '_',
            logged_in_user_name.split('@')[0],
        )
        u = JupyterhubUser.search_by(
            user_name=n,
        )
        if u:
            n += random.choice(string.ascii_lowercase)
        return n

    with sirepo.auth_db.thread_lock:
        if logged_in_user_name():
            return
        # TODO(e-carlin): sirepo.auth.logged_in_user_name()
        u = sirepo.auth.email.AuthEmailUser.search_by(
            uid=sirepo.auth.logged_in_user(check_path=False),
        )
# TODO(e-carlin): Is below still True ??
# TODO(e-carlin): if we are logged in but delete the run dir
# (happens in dev, maybe in prod if we delete a logged in user)
# then this assert will raise.
# It would be ideal to log the user out and redirect to / as done
# in non-jupyter apps but since we are outside of the flask context
# accessing the sirepo cookie and redirecting is challenging.
# Return None will display 403 for user which is fine for now.
        assert u, 'must have existing logged in user to create JupyterhubUser'
        JupyterhubUser(
            uid=u.uid,
            user_name=__user_name(u.user_name),
        ).save()
        return


def _init_model(base):
    global JupyterhubUser

    class JupyterhubUser(base):
        __tablename__ = 'jupyterhub_user_t'
        uid = sqlalchemy.Column(sqlalchemy.String(8), primary_key=True)
        user_name = sqlalchemy.Column(
            sqlalchemy.String(100),
            nullable=False,
            unique=True,
        )
