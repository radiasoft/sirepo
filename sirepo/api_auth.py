# -*- coding: utf-8 -*-
u"""authentication and authorization routines

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from sirepo import api_perm
from sirepo import auth
from sirepo import cookie
import sirepo.util


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


def check_api_call(func):
    expect = getattr(func, api_perm.ATTR)
    a = api_perm.APIPerm
    if expect in (a.REQUIRE_COOKIE_SENTINEL, a.REQUIRE_USER):
        if not cookie.has_sentinel():
            raise sirepo.util.SRException('missingCookies', None)
        if expect == a.REQUIRE_USER:
            auth.require_user()
    elif expect == a.ALLOW_VISITOR:
        pass
    elif expect == a.INTERNAL_TEST:
        if not pkconfig.channel_in_internal_test():
            sirepo.util.raise_forbidden('Only available in internal test')
    elif expect in (a.ALLOW_COOKIELESS_SET_USER, a.ALLOW_COOKIELESS_REQUIRE_USER):
        cookie.set_sentinel()
        if expect == a.ALLOW_COOKIELESS_REQUIRE_USER:
            auth.require_user()
    elif expect == a.REQUIRE_AUTH_BASIC:
        auth.require_auth_basic()
    else:
        raise AssertionError('unhandled api_perm={}'.format(expect))
