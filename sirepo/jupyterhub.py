# -*- coding: utf-8 -*-
u"""Jupyterhub login

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdexc, pkdlog
import importlib
import jupyterhub.auth
import os
import py.error
import random
import shutil
import sirepo.auth
import sirepo.auth.email
import sirepo.auth_db
import sirepo.cookie
import sirepo.server
import sirepo.srdb
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
        return _get_or_create_user(check_path=False)

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


def get_user_name(check_path=True):
    with sirepo.auth_db.thread_lock:
        u = JupyterhubUser.search_by(
            uid=sirepo.auth.logged_in_user(check_path=check_path),
        )
        if u:
            return u.user_name
    return None


def init():
    global cfg

    if cfg:
        return
    cfg = pkconfig.init(
        db_root=(
            pkio.py_path(sirepo.srdb.root()).join('jupyterhub'),
            pkio.py_path,
            'the path of jupyterhub user db (ex /srv/jupyterhub)',
        ),
        uri_root=('jupyter', str, 'the root uri of jupyterhub'),
    )
    sirepo.auth_db.init_model(_init_model)


def migrate_rs_data(rs_user_name):
    u = _get_or_create_user()
    with sirepo.auth_db.thread_lock:
        j = JupyterhubUser.search_by(
            uid=sirepo.auth.logged_in_user()
        )
        # TODO(e-carlin): u.uid doesn't work _get_or_create_user should return user model
        assert j, f'no JupyterhubUser with uid={u.uid}'
        s = cfg.db_root.join(rs_user_name)
        d = cfg.db_root.join(j.user_name)
        pkio.unchecked_remove(d)
        try:
            shutil.move(s, d)
        except FileNotFoundError:
            pkdlog(
                'Tried to migrate existing rs jupyter directory={} but not found. Ignoring.',
                s,
            )
        # TODO(e-carlin): Maybe don't set it to True in the case where source
        # dir wasn't found? They may have given the wrong github creds and want
        # to try migrating again.
        j.rs_migration_done = True
        j.save()

def _get_or_create_user(check_path=True):
    def _make_user_name_safe(s):
        _SAFE_CHARS = string.ascii_letters + '-' + '_'
        res = ''
        for c in s:
            if c not in _SAFE_CHARS:
                c = '_'
            res += c
        return res
    n = get_user_name(check_path=check_path)
    if n:
        # Existing JupyterhubUser
        return n
    # Create new JupyterhubUser
    u = sirepo.auth.email.AuthEmailUser.search_by(
        uid=sirepo.auth.logged_in_user(check_path=check_path),
    )
    # TODO(e-carlin): if we are logged in but delete the run dir
    # (happens in dev, maybe in prod if we delete a logged in user)
    # then this assert will raise.
    # It would be ideal to log the user out and redirect to / as done
    # in non-jupyter apps but since we are outside of the flask context
    # accessing the sirepo cookie and redirecting is challenging.
    # Return None will display 403 for user which is fine for now.
    if not u or not u.user_name:
        return None
    p = u.user_name.split('@')
    n = '@'.join(p[:-1])
    for i in range(5):
        # TODO(e-carlin): discuss _make_user_name_safe with rn. Username
        # will be used in paths so things like ../ must be escaped. In
        # addition they will be used in cookie names so I believe only
        # ascii_letters, '-' and '_' are valid. Also consider docker volumes.
        # we use pyisemail in sirepo.auth so maybe that is enough
        n = _make_user_name_safe(n)
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
        rs_migration_done = sqlalchemy.Column(sqlalchemy.Boolean())
        rs_migration_prompt_dimsissed = sqlalchemy.Column(sqlalchemy.Boolean())
        uid = sqlalchemy.Column(sqlalchemy.String(8), primary_key=True)
        user_name = sqlalchemy.Column(sqlalchemy.String(100), nullable=False)
