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
from sirepo import auth
from sirepo import cookie
from sirepo import http_reply
import sirepo.auth.basic


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
    e = None
    if p in (a.REQUIRE_COOKIE_SENTINEL, a.REQUIRE_USER):
        if not sirepo.cookie.has_sentinel():
            e = (
                'missingCookies',
                'cookie does not have a sentinel',
            )
        elif p == a.REQUIRE_USER:
            e = auth.require_user()
    elif p == a.ALLOW_VISITOR:
        pass
    elif p in (a.ALLOW_COOKIELESS_SET_USER, a.ALLOW_COOKIELESS_REQUIRE_USER):
        sirepo.cookie.set_sentinel()
        if p == a.ALLOW_COOKIELESS_REQUIRE_USER:
            e = auth.require_user()
    elif p == a.REQUIRE_AUTH_BASIC:
        # user gets cookied so don't need to check db
        if auth.require_user
        e = sirepo.auth.basic.require_user()
        if e:
            # returns a challenge response
            return e
    else:
        raise AssertionError('unexpected api_perm={}'.format(p))
    if not e:
        return None
    pkdlog(
        'srException: err={} route={} perm={} func={}',
        e[1],
        e[0],
        p,
        func.__name__,
    )
    return http_reply.gen_sr_exception(e[0])
