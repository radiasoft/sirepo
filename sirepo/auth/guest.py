# -*- coding: utf-8 -*-
u"""Email login support

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import auth

#: User can see it
AUTH_METHOD_VISIBLE = True

#: Used by user_db
UserModel = None

#: module handle
this_module = pkinspect.this_module()

@api_perm.require_cookie_sentinel
def api_guestAuthLogin():
    """You have to be an anonymous or logged in user at this point"""
    auth.login(this_module)


def auth_login_hook():
    pass


def auth_logout_hook():
    auth.clear_user()
