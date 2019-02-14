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
from sirepo import user_state


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
    p = getattr(func, api_perm.ATTR)
    a = api_perm.APIPerm

    def _e(route, err):
        pkdlog(
            'srException: err={} route={} perm={} func={}',
            err,
            route,
            p,
            func.__name__,
        )
        return http_reply.gen_sr_exception(route)

    if p in (a.REQUIRE_COOKIE_SENTINEL, a.REQUIRE_USER):
        if not cookie.has_sentinel():
            return _e(
                'missingCookies',
                'cookie does not have a sentinel',
            )
        elif p == a.REQUIRE_USER:
            e = user_state.require_user()
            if e:
                return _e(*e)
    elif p == a.ALLOW_VISITOR:
        pass
    elif p in (a.ALLOW_COOKIELESS_SET_USER, a.ALLOW_COOKIELESS_REQUIRE_USER):
        cookie.set_sentinel()
        if p == a.ALLOW_COOKIELESS_REQUIRE_USER:
            e = user_state.require_user()
            if e:
                return _e(*e)
    else:
        raise AssertionError('unexpected api_perm={}'.format(p))
    return None
