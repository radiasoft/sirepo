# -*- coding: utf-8 -*-
u"""authentication and authorization routines

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import cookie
from sirepo import sr_api_perm
from sirepo import util


def assert_api_call(func):
    p = getattr(func, sr_api_perm.ATTR)
    a = sr_api_perm.APIPerm
    if p == a.REQUIRE_USER:
        if not cookie.has_sentinel():
            util.raise_forbidden(
                'cookie does not have a sentinel: perm={} func={}',
                p,
                func.__name__,
            )
    elif p == a.ALLOW_VISITOR:
        pass
    elif p == a.ALLOW_COOKIELESS_USER:
        cookie.set_sentinel()
    elif p == a.ALLOW_LOGIN:
#TODO(robnagler) need state so that set_user can happen
        cookie.set_sentinel()
    else:
        raise AssertionError('unexpected sr_api_perm={}'.format(p))


def assert_api_def(func):
    try:
        assert isinstance(getattr(func, sr_api_perm.ATTR), sr_api_perm.APIPerm)
    except Exception as e:
        raise AssertionError(
            'function needs sr_api_perm decoration: func={} err={}'.format(
                func.__name__,
                e,
            ),
        )
