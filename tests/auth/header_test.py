"""Header authentication configuration and account policies.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


@pytest.fixture(scope="module")
def qcall():
    from sirepo import srunit

    with srunit.quest_start(
        cfg={
            "SIREPO_AUTH_METHODS": "header",
            "SIREPO_AUTH_HEADER_TKN": "proxy-test-secret",
            "SIREPO_FEATURE_CONFIG_SIM_TYPES": "myapp",
        },
    ) as q:
        yield q


def test_accounts(qcall):
    from pykern import pkunit

    u = _authenticate(qcall, "existing@example.com")
    pkunit.pkeq(True, qcall.auth.need_complete_registration(u))
    qcall.auth.complete_registration("Existing User")
    qcall.auth.reset_state()
    pkunit.pkeq(u, _authenticate(qcall, "EXISTING@example.com"))
    pkunit.pkeq("Existing User", qcall.auth.user_display_name(u))
    pkunit.pkeq(u, qcall.auth.unchecked_get_user("existing@example.com"))
    roles = qcall.auth_db.model("UserRole").get_roles(u)
    v = _authenticate(qcall, "different")
    pkunit.pkne(u, v)
    pkunit.pkeq(u, _authenticate(qcall, "existing@example.com"))
    pkunit.pkeq(roles, qcall.auth_db.model("UserRole").get_roles(u))


def test_pending_and_conflicting_accounts(qcall):
    from pykern import pkunit
    from sirepo import util

    qcall.auth_db.model("AuthEmailUser", unverified_email="pending@example.com").save()
    qcall.auth_db.model(
        "AuthEmailUser",
        unverified_email="old@example.com",
        user_name="renamed@example.com",
    ).save()
    u = _authenticate(qcall, "pending@example.com")
    pkunit.pkeq(
        u,
        qcall.auth_db.model("AuthEmailUser")
        .search_by(unverified_email="pending@example.com")
        .uid,
    )
    with pkunit.pkexcept(util.Forbidden):
        _authenticate(qcall, "old@example.com")


def test_registration_moderation(qcall, monkeypatch):
    from pykern import pkunit
    from sirepo import feature_config, util

    u = _authenticate(qcall, "registered-user")
    qcall.auth.complete_registration("Registered User")
    monkeypatch.setitem(feature_config.cfg(), "is_registration_moderated", True)
    with pkunit.pkexcept(util.Forbidden):
        _authenticate(qcall, "unregistered-user")
    pkunit.pkeq(
        None,
        qcall.auth_db.model("UserRegistration").unchecked_search_by(
            display_name="unregistered-user"
        ),
    )
    qcall.auth.reset_state()
    pkunit.pkeq(u, _authenticate(qcall, "registered-user"))


def test_removed_role(qcall):
    from pykern import pkunit
    from sirepo import util

    u = _authenticate(qcall, "disabled-user")
    qcall.auth.complete_registration("Disabled User")
    qcall.auth_db.model("UserRole").delete_all_for_column_by_values("uid", [u])
    qcall.auth.reset_state()
    pkunit.pkeq(u, _authenticate(qcall, "disabled-user"))
    with pkunit.pkexcept(util.Forbidden):
        qcall.auth.require_user()
    pkunit.pkeq([], qcall.auth_db.model("UserRole").get_roles(u))


def test_header_names(qcall):
    from pykern import pkunit
    from sirepo.auth import header

    for n in ("", "bad header", "bad:header", "Cookie", "authorization"):
        with pkunit.pkexcept("invalid proxy authentication header"):
            header._cfg_header(n)
    for n in ("x-custom-user", "X-CUSTOM-USER", "X-Custom-User"):
        pkunit.pkeq("X-Custom-User", header._cfg_header(n))


def test_cookie_precedence(qcall, monkeypatch):
    from pykern import pkunit
    from sirepo import util
    from sirepo.auth import header
    from tornado.httputil import HTTPHeaders

    u = _authenticate(qcall, "cookie-user")

    def _unexpected(*args, **kwargs):
        pkunit.pkfail("cookie authentication must not query account models")

    with monkeypatch.context() as m:
        m.setattr(type(qcall.auth_db), "model", _unexpected)
        for headers in (
            {},
            {"X-Sirepo-User": "different", "X-Sirepo-Auth-Token": "proxy-test-secret"},
            {"X-Sirepo-User": "different"},
            {"X-Sirepo-Auth-Token": "wrong"},
            {"X-Sirepo-User": "", "X-Sirepo-Auth-Token": ""},
        ):
            qcall.sreq.http_headers = HTTPHeaders(headers)
            with pkunit.pkexcept(util.Redirect):
                header.authenticate(qcall, "myapp")
            pkunit.pkeq(u, qcall.auth.logged_in_user())
    pkunit.pkeq(True, qcall.auth.need_complete_registration(u))
    qcall.auth.complete_registration("Cookie User")
    qcall.auth.require_user()
    qcall.auth_db.model("UserRole").delete_all_for_column_by_values("uid", [u])
    with pkunit.pkexcept(util.Forbidden):
        qcall.auth.require_user()


def test_ordinary_request(qcall, monkeypatch):
    from pykern import pkunit
    from sirepo.auth import header

    def _unexpected(*args, **kwargs):
        pkunit.pkfail("ordinary requests must not invoke proxy authentication")

    monkeypatch.setattr(header, "authenticate", _unexpected)
    qcall.auth.reset_state()
    qcall.call_api_sync("authState").destroy()
    pkunit.pkeq(False, qcall.auth.is_logged_in())


def _authenticate(qcall, username):
    from sirepo import util
    from sirepo.auth import header
    from tornado.httputil import HTTPHeaders

    qcall.auth.reset_state()
    qcall.sreq.http_headers = HTTPHeaders(
        {"X-Sirepo-User": username, "X-Sirepo-Auth-Token": "proxy-test-secret"}
    )
    with pytest.raises(util.Redirect):
        header.authenticate(qcall, "myapp")
    return qcall.auth.logged_in_user()
