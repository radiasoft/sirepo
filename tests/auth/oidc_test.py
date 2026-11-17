"""OIDC email account resolution and configuration.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


@pytest.fixture(scope="module")
def qcall():
    from sirepo import srunit

    with srunit.quest_start(
        cfg={
            "SIREPO_AUTH_METHODS": "oidc",
            "SIREPO_AUTH_OIDC_ISSUER": "https://idp.example",
            "SIREPO_AUTH_OIDC_CLIENT_ID": "sirepo",
            "SIREPO_AUTH_OIDC_CLIENT_SECRET": "test-secret",
            "SIREPO_AUTH_OIDC_REDIRECT_URI": "https://sirepo.example/auth-oidc-callback",
            "SIREPO_FEATURE_CONFIG_SIM_TYPES": "myapp",
            "SIREPO_FEATURE_CONFIG_IS_REGISTRATION_MODERATED": "0",
        }
    ) as q:
        yield q


def test_accounts(qcall):
    from pykern import pkunit

    uid = _login(qcall, "subject", "Existing@Example.com")
    pkunit.pkeq(True, qcall.auth.need_complete_registration(uid))
    qcall.auth.complete_registration("Existing User")
    roles = qcall.auth_db.model("UserRole").get_roles(uid)
    pkunit.pkeq(uid, _login(qcall, "different-subject", "EXISTING@example.com"))
    pkunit.pkeq("existing@example.com", qcall.auth.user_name(uid))
    pkunit.pkeq(uid, qcall.auth.unchecked_get_user("existing@example.com"))
    pkunit.pkeq("Existing User", qcall.auth.user_display_name(uid))
    pkunit.pkeq(roles, qcall.auth_db.model("UserRole").get_roles(uid))
    changed = _login(qcall, "subject", "changed@example.com")
    pkunit.pkne(uid, changed)
    pkunit.pkeq("changed@example.com", qcall.auth.user_name(changed))
    pkunit.pkeq(uid, _login(qcall, "subject", "existing@example.com"))
    pkunit.pkne(uid, _login(qcall, "other-subject", "other@example.com"))


def test_link_existing_and_pending(qcall):
    from pykern import pkunit

    uid = qcall.auth.logged_in_user()
    pkunit.pkeq(uid, _login(qcall, "email-subject", "OTHER@example.com"))
    qcall.auth_db.model("AuthEmailUser", unverified_email="pending@example.com").save()
    uid = _login(qcall, "pending-subject", "pending@example.com")
    pkunit.pkeq("pending@example.com", qcall.auth.user_name(uid))


def test_invalid_accounts(qcall):
    from sirepo import util

    for sub, email, verified in (
        ("bad", "valid@example.com", False),
        ("bad", "valid@example.com", "true"),
        ("bad", "not-an-email", True),
        ("", "valid@example.com", True),
        ("x" * 256, "valid@example.com", True),
    ):
        with pytest.raises(util.Forbidden):
            _login(qcall, sub, email, verified)
    qcall.auth_db.model(
        "AuthEmailUser",
        user_name="renamed@example.com",
        unverified_email="old@example.com",
    ).save()
    with pytest.raises(util.Forbidden):
        _login(qcall, "conflict", "old@example.com")


def test_moderation(qcall, monkeypatch):
    from pykern import pkunit
    from sirepo import feature_config

    monkeypatch.setitem(feature_config.cfg(), "is_registration_moderated", True)
    from sirepo import util
    from sirepo.auth import oidc

    qcall.auth.reset_state()
    with pytest.raises(util.Redirect):
        oidc._registration_or_login(
            qcall,
            "unregistered@example.com",
            "myapp",
        )
    assert (
        qcall.auth_db.model("AuthEmailUser").unchecked_search_by(
            user_name="unregistered@example.com"
        )
        is None
    )
    pkunit.pkeq(
        "Existing User",
        qcall.auth.user_display_name(_login(qcall, "subject", "existing@example.com")),
    )


def test_urls(qcall):
    from sirepo.auth import oidc

    for url in (
        "https://idp.example",
        "http://localhost:9000",
        "http://127.0.0.1:9000",
    ):
        assert oidc._cfg_url(url) == url
    for url in (
        "http://idp.example",
        "//idp.example",
        "https://user:password@idp.example",
        "https://idp.example/#fragment",
        "javascript:alert(1)",
    ):
        with pytest.raises(AssertionError):
            oidc._cfg_url(url)


def test_periodic_cleanup(qcall):
    import asyncio
    import datetime
    from sirepo import srtime
    from sirepo.auth import oidc

    m = qcall.auth_db.model("AuthOidcLogin")
    now = srtime.utc_now()
    for state, email, expires in (
        ("expired-auth", None, now - datetime.timedelta(seconds=1)),
        (
            "expired-registration",
            "expired@example.com",
            now - datetime.timedelta(seconds=1),
        ),
        ("live-auth", None, now + datetime.timedelta(minutes=5)),
        ("live-registration", "live@example.com", now + datetime.timedelta(minutes=5)),
    ):
        m.new(
            state=state,
            email=email,
            expires=expires,
            nonce="nonce",
            verifier="verifier",
            simulation_type="myapp",
        ).save()
    qcall.auth_db.commit()
    asyncio.run(oidc._cleanup(None))
    for state in ("expired-auth", "expired-registration"):
        assert (
            qcall.auth_db.model("AuthOidcLogin").unchecked_search_by(state=state)
            is None
        )
    for state in ("live-auth", "live-registration"):
        assert qcall.auth_db.model("AuthOidcLogin").unchecked_search_by(state=state)
    assert oidc._CLEANUP_CRON._period == 60 * 60
    assert oidc._CLEANUP_CRON._coro_func == oidc._cleanup


@pytest.mark.parametrize(
    "email,consumed,expired,authorization,registration",
    [
        (None, False, False, True, False),
        (None, True, False, False, False),
        ("pending@example.com", False, False, False, True),
        ("pending@example.com", True, False, False, False),
        (None, False, True, False, False),
        ("pending@example.com", False, True, False, False),
    ],
)
def test_pending_states(qcall, email, consumed, expired, authorization, registration):
    import datetime
    from sirepo import srtime

    pending = qcall.auth_db.model(
        "AuthOidcLogin",
        email=email,
        consumed=consumed,
        expires=srtime.utc_now() + datetime.timedelta(minutes=-1 if expired else 1),
    )
    assert pending.is_pending_authorization() is authorization
    assert pending.is_pending_registration() is registration


def _login(qcall, subject, email, verified=True):
    from sirepo import util
    from sirepo.auth import oidc

    with pytest.raises(util.Redirect):
        oidc._login(
            qcall,
            oidc._email_user(
                qcall,
                oidc._validated_email(
                    {"sub": subject, "email": email, "email_verified": verified}
                ),
            ),
            "myapp",
        )
    return qcall.auth.logged_in_user()
