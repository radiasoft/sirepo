# -*- coding: utf-8 -*-
u"""Jupyterhub login

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdexc
import importlib
import jupyterhub.auth
import os
import py.error
import random
import sirepo.auth
import sirepo.auth.email
import sirepo.auth_db
import sirepo.cookie
import sirepo.server
import sirepo.util
import sqlalchemy
import string
import tornado.web

cfg = None

JupyterhubUser = None


class Authenticator(jupyterhub.auth.Authenticator):
    # Do not prompt with jupyterhub login page. self.authenticate()
    # will handle login using Sirepo functionality
    auto_login = True
    refresh_pre_spawn = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        sirepo.server.init()

    async def authenticate(self, handler, data):
        c = handler.get_cookie(sirepo.cookie.cfg.http_name)
        if not c:
            c = ''
        sirepo.cookie.set_cookie_for_jupyterhub(f'{sirepo.cookie.cfg.http_name}={c}')
        try:
            sirepo.auth.require_user()
        except sirepo.util.SRException as e:
            r = e.sr_args.get('routeName')
            if r:
                handler.redirect(f'/jupyterhublogin#/{r}')
                raise tornado.web.Finish()
            raise
        return _get_or_create_user()

    async def refresh_user(self, user, handler=None):
        assert handler, \
            'Need the handler to get the cookie'
        c = handler.get_cookie(sirepo.cookie.cfg.http_name)
        if not c:
            return False
        sirepo.cookie.set_cookie_for_jupyterhub(
            f'{sirepo.cookie.cfg.http_name}={c}'
        )

        try:
            sirepo.auth.require_user()
        except sirepo.util.SRException:
            return False
        return True


def get_user_name():
    with sirepo.auth_db.thread_lock:
        u = JupyterhubUser.search_by(uid=sirepo.auth.logged_in_user())
        if u:
            return u.user_name
    return None


def init():
    import sirepo.srdb
    global cfg

    if cfg:
        return
    cfg = pkconfig.init(
        db_root=(
            pkio.py_path(sirepo.srdb.root()).join('jupyterhub'),
            pkio.py_path,
            'the root path of jupyterhub',
        ),
        uri_root=('jupyter', str, 'the root path of jupyterhub'),
    )
    sirepo.auth_db.init_model(_init_model)


def _get_or_create_user():
    n = get_user_name()
    if n:
        # Existing JupyterhubUser
        return n
    # Create new JupyterhubUser
    u = sirepo.auth.email.AuthEmailUser.search_by(
        uid=sirepo.auth.logged_in_user(),
    )
    # TODO(e-carlin): if we are logged in but delete the run dir
    # (happens in dev, maybe in prod if we delete a logged in user)
    # then this assert will fail. Maybe we should just log the user
    # out and go to the home page which is what seems to be done when
    # a similar scenario happens in non-jupyter apps
    assert u and u.user_name, \
        f'must be existing AuthEmailUser to create JupyterhubUser u={u}'
    p = u.user_name.split('@')
    n = '@'.join(p[:-1])
    # TODO(e-carlin): we need to make the username safe (docker acceptable volume mount chars, no ../../ etc)
    # jupyterhub uses minrk/escapism
    for i in range(5):
        try:
            cfg.db_root.join(n).mkdir()
            break
        except py.error.EEXIST:
            if i == 0:
                n += '_' + p[-1].split('.')[0]
                continue
            if i == 1:
                n += '_'
            n += random.choice(string.ascii_lowercase)
    else:
        raise RuntimeError(f'unable to generate unique jupyterhub user dir n={n}')
    with sirepo.auth_db.thread_lock:
        u = JupyterhubUser(
            uid=u.uid,
            user_name=n,
        )
        u.save()
        return u.user_name


def _init_model(base):
    global JupyterhubUser

    class JupyterhubUser(base):
        __tablename__ = 'jupyterhub_user_t'
        uid = sqlalchemy.Column(sqlalchemy.String(8), primary_key=True)
        user_name = sqlalchemy.Column(sqlalchemy.String(100), nullable=False)
