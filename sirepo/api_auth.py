# -*- coding: utf-8 -*-
"""authentication and authorization routines

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from sirepo import api_perm
import sirepo.auth
import sirepo.cookie
import sirepo.util


def assert_api_def(func):
    try:
        assert isinstance(getattr(func, api_perm.ATTR), api_perm.APIPerm)
    except Exception as e:
        raise AssertionError(
            "function needs api_perm decoration: func={} err={}".format(
                func.__name__,
                e,
            ),
        )


def check_api_call(func):
    expect = getattr(func, api_perm.ATTR)
    a = api_perm.APIPerm
    if expect in (
        a.ALLOW_SIM_TYPELESS_REQUIRE_EMAIL_USER,
        a.REQUIRE_COOKIE_SENTINEL,
        a.REQUIRE_USER,
        a.REQUIRE_ADM,
    ):
        if not sirepo.cookie.has_sentinel():
            raise sirepo.util.SRException("missingCookies", None)
        if expect == a.REQUIRE_USER:
            sirepo.auth.require_user()
        elif expect == a.ALLOW_SIM_TYPELESS_REQUIRE_EMAIL_USER:
            sirepo.auth.require_email_user()
        elif expect == a.REQUIRE_ADM:
            sirepo.auth.require_adm()
    elif expect == a.ALLOW_VISITOR:
        pass
    elif expect == a.INTERNAL_TEST:
        if not pkconfig.channel_in_internal_test():
            sirepo.util.raise_forbidden("Only available in internal test")
    elif expect in (a.ALLOW_COOKIELESS_SET_USER, a.ALLOW_COOKIELESS_REQUIRE_USER):
        sirepo.cookie.set_sentinel()
        if expect == a.ALLOW_COOKIELESS_REQUIRE_USER:
            sirepo.auth.require_user()
    elif expect == a.REQUIRE_AUTH_BASIC:
        sirepo.auth.require_auth_basic()
    else:
        raise AssertionError("unhandled api_perm={}".format(expect))


def maybe_sim_type_required_for_api(func):
    return getattr(func, api_perm.ATTR) not in api_perm.SIM_TYPELESS_PERMS
