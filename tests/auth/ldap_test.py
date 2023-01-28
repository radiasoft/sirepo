# -*- coding: utf-8 -*-
"""Test ldap

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_happy_path():
    from pykern import pkunit

    r, u = _call_login("vagrant@radiasoft.net", "vagrant")
    pkunit.pkeq(200, r.status_as_int())
    pkunit.pkre("location.*/complete-registration", r.content_as_str())
    pkunit.pkne(None, u)


def test_cred_validation():
    from pykern import pkunit

    pkunit.pkre(
        "Invalid user and/or password",
        _call_login("any-user", "")[0]._SReply__attrs.content,
    )


def test_incorrect_creds():
    from pykern import pkunit

    pkunit.pkre(
        "Invalid user and/or password",
        _call_login("not-a-user", "any-password")[0]._SReply__attrs.content,
    )


def _call_login(email, password):
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
                email=email,
                password=password,
            ),
        )
        m = qcall.auth_db.model("AuthEmailUser")
        u = m.unchecked_search_by(unverified_email=email)
        return r, u


# mock ldap.INVALID_CREDENTIALS
class INVALID_CREDENTIALS(Exception):
    pass


def initialize(*args, **kwargs):
    """Mock ldap.initialize"""
    from pykern.pkcollections import PKDict

    # mock ldap.simple_bind_s
    def _bind(dn, password):
        if (
            dn != "mail=vagrant@radiasoft.net,ou=users,dc=example,dc=com"
            or password != "vagrant"
        ):
            raise INVALID_CREDENTIALS

    return PKDict(simple_bind_s=lambda x, y: _bind(x, y))
