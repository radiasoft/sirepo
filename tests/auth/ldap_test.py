"""Test ldap

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


def setup_module(module):
    import os

    os.environ.update(
        SIREPO_AUTH_LDAP_EMAIL_DOMAIN="radiasoft.net",
    )
    _mock_ldap3()


def test_happy_path():
    from pykern import pkunit

    r, u = _call_login("happy", "some-good-pw")
    pkunit.pkeq("/myapp#/complete-registration", r.content_as_redirect().uri)
    pkunit.pkne(None, u)


def test_cred_deviance():
    from pykern import pkunit

    for x in (("any-user", ""), ("not-a-user", "any-password")):
        pkunit.pkeq(
            "Invalid user and/or password",
            _call_login(*x)[0].content_as_object().form_error,
        )


def _call_login(user, password):
    from pykern.pkcollections import PKDict
    from sirepo import srunit
    from pykern.pkdebug import pkdp

    with srunit.quest_start(cfg={"SIREPO_AUTH_METHODS": "ldap"}) as qcall:
        r = qcall.call_api_sync(
            "authLdapLogin",
            body=PKDict(
                simulationType="myapp",
                user=user,
                password=password,
            ),
        )
        return (
            r,
            qcall.auth_db.model("AuthEmailUser").unchecked_search_by(
                unverified_email=user + "@radiasoft.net",
            ),
        )


def _mock_ldap3():
    from pykern import pkinspect
    import sys

    m = pkinspect.this_module()
    m.core = m
    m.exceptions = m
    sys.modules["ldap3"] = m
    sys.modules["ldap3.core"] = m
    sys.modules["ldap3.core.exceptions"] = m


class LDAPException(Exception):
    """mock ldap3.core.exceptions.LDAPException"""

    description = "invalidCredentials"


def Connection(*args, **kwargs):
    """Mock ldap3.Connection"""
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp

    def _bind(dn, password):
        """mock ldap3.Connection.bind"""
        if dn != "mail=happy,ou=users,dc=example,dc=com" or password != "some-good-pw":
            raise LDAPException()

    return PKDict(bind=lambda: _bind(kwargs["user"], kwargs["password"]))


def Server(*args, **kwargs):
    """Mock ldap3.Server"""
    return None
