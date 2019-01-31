# -*- coding: utf-8 -*-
u"""authentication and authorization routines

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern import pkcollections
from pykern import pkinspect
from sirepo import api_perm
from sirepo import cookie
from sirepo import http_reply
from sirepo import util


login_module = None


def all_uids():
    if not login_module:
        return []
    return login_module.all_uids()


@api_perm.allow_visitor
def api_userState():
    v = pkcollections.Dict(
        # means "have some type of auth method" and is logged out
        is_logged_out=False,
        user_state=None,
    )
    if login_module:
        s = login_module.set_default_state()
        if s:
            v.user_state = pkcollections.Dict(
                authMethod=s.auth_method,
                displayNameSet=s.display_name_set,
                loginState=s.login_state,
                userName=s.user_name,
            )
            v.is_logged_out = s.is_logged_out
    return http_reply.render_static('user-state', 'js', v)


def assert_api_call(func):
    p = getattr(func, api_perm.ATTR)
    a = api_perm.APIPerm
    if p == a.REQUIRE_USER:
        if not cookie.has_sentinel():
            util.raise_unauthorized(
                'cookie does not have a sentinel: perm={} func={}',
                p,
                func.__name__,
            )
    elif p == a.ALLOW_VISITOR:
        pass
    elif p == a.ALLOW_COOKIELESS_USER:
        cookie.set_sentinel()
        if login_module:
            login_module.set_default_state()
    elif p == a.ALLOW_LOGIN:
#TODO(robnagler) need state so that set_user can happen
        cookie.set_sentinel()
    else:
        raise AssertionError('unexpected api_perm={}'.format(p))


def assert_api_def(func):
    try:
        assert isinstance(getattr(func, api_perm.ATTR), api_perm.APIPerm)
    except Exception as e:
        raise AssertionError(
            'function needs api_perm decoration: func={} err={}'.format(
                func.__name__,
                e,
            ),
        )


def init_apis(app):
    from sirepo import uri_router

    uri_router.register_api_module()


def register_login_module():
    global login_module

    m = pkinspect.caller_module()
    assert not login_module, \
        'login_module already registered: old={} new={}'.format(login_module, m)
    login_module = m
