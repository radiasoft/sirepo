# -*- coding: utf-8 -*-
"""authentication and authorization routines

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
import sirepo.api_perm
import sirepo.auth
import sirepo.util


def assert_api_def(func):
    try:
        assert isinstance(getattr(func, sirepo.api_perm.ATTR), sirepo.api_perm.APIPerm)
    except Exception as e:
        raise AssertionError(
            "function needs api_perm decoration: func={} err={}".format(
                func.__name__,
                e,
            ),
        )


def check_api_call(qcall, func):
    expect = getattr(func, sirepo.api_perm.ATTR)
    a = sirepo.api_perm.APIPerm
    if expect in (
        a.ALLOW_SIM_TYPELESS_REQUIRE_EMAIL_USER,
        a.REQUIRE_COOKIE_SENTINEL,
        a.REQUIRE_USER,
        a.REQUIRE_PLAN,
        a.REQUIRE_ADM,
        a.REQUIRE_PREMIUM,
    ):
        if not qcall.cookie.has_sentinel():
            raise sirepo.util.SRException("missingCookies", None)
        if expect == a.REQUIRE_PLAN:
            qcall.auth.require_plan()
        elif expect == a.REQUIRE_USER:
            qcall.auth.require_user()
        elif expect == a.ALLOW_SIM_TYPELESS_REQUIRE_EMAIL_USER:
            qcall.auth.require_email_user()
        elif expect == a.REQUIRE_ADM:
            qcall.auth.require_adm()
        elif expect == a.REQUIRE_PREMIUM:
            qcall.auth.require_premium()
    elif expect == a.ALLOW_VISITOR:
        pass
    elif expect == a.INTERNAL_TEST:
        if not pkconfig.channel_in_internal_test():
            raise sirepo.util.Forbidden("Only available in internal test")
    elif expect in (a.ALLOW_COOKIELESS_SET_USER, a.ALLOW_COOKIELESS_REQUIRE_USER):
        qcall.cookie.set_sentinel()
        if expect == a.ALLOW_COOKIELESS_REQUIRE_USER:
            qcall.auth.require_user()
    elif expect == a.REQUIRE_AUTH_BASIC:
        qcall.auth.require_auth_basic()
    else:
        raise AssertionError("unhandled api_perm={}".format(expect))


def maybe_sim_type_required_for_api(func):
    return getattr(func, sirepo.api_perm.ATTR) not in sirepo.api_perm.SIM_TYPELESS_PERMS
