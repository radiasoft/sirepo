# -*- coding: utf-8 -*-
"""Test ldap

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest

# module must have ldap.INVALID_CREDENTIALS
INVALID_CREDENTIALS = Exception


def test_happy_path():
    from pykern.pkcollections import PKDict
    from pykern import pkinspect
    from sirepo import srunit
    import sys

    sys.modules["ldap"] = pkinspect.this_module()

    with srunit.quest_start(cfg={"SIREPO_AUTH_METHODS": "ldap"}) as qcall:
        from pykern import pkunit
        from sirepo import auth_db

        r = qcall.call_api(
            "authLdapLogin",
            data=PKDict(
                simulationType="myapp",
                email="vagrant@radiasoft.net",
                password="vagrant",
            ),
        )
        pkunit.pkeq(200, r.status_as_int())
        pkunit.pkre("location.*/complete-registration", r.content_as_str())

        m = qcall.auth_db.model("AuthEmailUser")
        u = m.unchecked_search_by(unverified_email="vagrant@radiasoft.net")
        pkunit.pkne(None, u)


def test_cred_validation():
    from pykern.pkcollections import PKDict
    from pykern import pkinspect
    from sirepo import srunit
    import sys

    sys.modules["ldap"] = pkinspect.this_module()

    with srunit.quest_start(cfg={"SIREPO_AUTH_METHODS": "ldap"}) as qcall:
        from pykern import pkunit

        r = qcall.call_api(
            "authLdapLogin",
            data=PKDict(
                simulationType="myapp",
                email="",
                password="",
            ),
        )
        pkunit.pkok("error" in r.content_as_str(), "did not return error state")


def test_invalid_creds():
    from pykern.pkcollections import PKDict
    from pykern import pkinspect
    from sirepo import srunit
    import sys

    sys.modules["ldap"] = pkinspect.this_module()

    with srunit.quest_start(cfg={"SIREPO_AUTH_METHODS": "ldap"}) as qcall:
        from pykern import pkunit

        r = qcall.call_api(
            "authLdapLogin",
            data=PKDict(
                simulationType="myapp",
                email="badEmail",
                password="badPassword",
            ),
        )
        pkunit.pkok("error" in r.content_as_str(), "did not return error state")


def initialize(*args, **kwargs):
    """Simulate ldap.initialize"""
    from pykern.pkcollections import PKDict

    # Simulate ldap.simple_bind_s
    def _bind(dn, password):
        if (
            dn != "mail=vagrant@radiasoft.net,ou=users,dc=example,dc=com"
            or password != "vagrant"
        ):
            raise INVALID_CREDENTIALS

    return PKDict(simple_bind_s=lambda x, y: _bind(x, y))
