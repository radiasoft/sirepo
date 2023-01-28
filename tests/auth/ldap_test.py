# -*- coding: utf-8 -*-
"""Test ldap

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest
from pykern.pkdebug import pkdlog, pkdp


def test_happy_path():
    from pykern.pkcollections import PKDict
    from pykern import pkunit

    res = PKDict(
        email="vagrant@radiasoft.net",
        password="vagrant",
    )
    r, u = _call_login(res)
    pkunit.pkeq(200, r.status_as_int())
    pkunit.pkre("location.*/complete-registration", r.content_as_str())
    pkunit.pkne(None, u)


def test_cred_validation():
    from pykern.pkcollections import PKDict
    from pykern import pkunit

    res = PKDict(
        email="any-user",
        password="",
    )
    r = _call_login(res)[0]
    pkunit.pkok("form_error" in r.content_as_str(), "did not return form_error")


def test_incorrect_creds():
    from pykern.pkcollections import PKDict
    from pykern import pkunit

    res = PKDict(
        email="not-a-user",
        password="any-password",
    )
    r = _call_login(res)[0]
    pkunit.pkok("form_error" in r.content_as_str(), "did not return form_error")


def _call_login(res):
    from pykern import pkinspect
    from sirepo import srunit
    import sys

    sys.modules["ldap"] = pkinspect.this_module()
    with srunit.quest_start(cfg={"SIREPO_AUTH_METHODS": "ldap"}) as qcall:
        from pykern.pkcollections import PKDict

        r = qcall.call_api(
            "authLdapLogin",
            data=PKDict(
                simulationType="myapp",
                email=res.email,
                password=res.password,
            ),
        )
        m = qcall.auth_db.model("AuthEmailUser")
        u = m.unchecked_search_by(unverified_email=res.email)
        return r, u


# Mock ldap.INVALID_CREDENTIALS
class INVALID_CREDENTIALS(Exception):
    pass


def initialize(*args, **kwargs):
    """Mock ldap.initialize"""
    from pykern.pkcollections import PKDict

    # Mock ldap.simple_bind_s
    def _bind(dn, password):
        if (
            dn != "mail=vagrant@radiasoft.net,ou=users,dc=example,dc=com"
            or password != "vagrant"
        ):
            raise INVALID_CREDENTIALS

    return PKDict(simple_bind_s=lambda x, y: _bind(x, y))
