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
from sirepo import util


def assert_api_call(func):
    p = getattr(func, api_perm.ATTR)
    a = api_perm.APIPerm
    if p == a.REQUIRE_COOKIE_SENTINEL:
        if not cookie.has_sentinel():
            util.raise_unauthorized(
                'cookie does not have a sentinel: perm={} func={}',
                p,
                func.__name__,
            )
        # cookie_name is no longer used, remove from cookie
        cookie.unchecked_remove(_REMOVED_COOKIE_NAME)
    elif p == a.ALLOW_VISITOR:
        pass
    elif p == a.ALLOW_COOKIELESS_SET_USER:
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
