"""OIDC email account resolution and configuration.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


@pytest.fixture(scope="module")
def _qcall():
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


@pytest.fixture
def qcall(_qcall):
    _qcall.auth.reset_state()
    return _qcall


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

    uid = _login(qcall, "email-subject", "linked@example.com")
    pkunit.pkeq(uid, _login(qcall, "different-subject", "LINKED@example.com"))
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

    uid = _login(qcall, "subject", "moderated-existing@example.com")
    qcall.auth.complete_registration("Existing User")
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
        qcall.auth.user_display_name(
            _login(qcall, "subject", "moderated-existing@example.com")
        ),
    )
    pkunit.pkeq(uid, qcall.auth.logged_in_user())


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


@pytest.mark.parametrize(
    "value,domain,verified,required,expected",
    [
        ("Person@Example.org", None, True, True, "person@example.org"),
        ("Person", "example.org", None, False, "person@example.org"),
        ("Person@Other.org", "example.org", None, False, "person@other.org"),
        ("Person", None, None, False, None),
        ("bad name", "example.org", None, False, None),
        (["Person"], "example.org", None, False, None),
        (None, "example.org", None, False, None),
        ("Person@Example.org", None, None, True, None),
        ("Person@Example.org", None, False, False, None),
        ("Person@Example.org", None, "true", False, None),
        ("Person@Example.org", None, 1, False, None),
        ("x" * 250, "example.org", None, False, None),
    ],
)
def test_email_mapping(qcall, monkeypatch, value, domain, verified, required, expected):
    from sirepo import util
    from sirepo.auth import oidc

    monkeypatch.setitem(oidc._cfg, "email_claim", "directory_user")
    monkeypatch.setitem(oidc._cfg, "email_domain", domain)
    monkeypatch.setitem(oidc._cfg, "require_verified_email", required)
    claims = dict(sub="subject", directory_user=value, email="ignored@example.org")
    if verified is not None:
        claims["email_verified"] = verified
    if expected is None:
        with pytest.raises(util.Forbidden):
            oidc._validated_email(claims)
    else:
        assert oidc._validated_email(claims) == expected


def test_email_domain(qcall):
    from sirepo.auth import oidc

    assert oidc._cfg_email_domain("Example.ORG") == "example.org"
    for domain in ("@example.org", "https://example.org", "bad domain", "a@b.org"):
        with pytest.raises(AssertionError):
            oidc._cfg_email_domain(domain)


@pytest.mark.parametrize(
    "changes,message",
    [
        (dict(scopes=("email", "profile")), "scopes must include openid"),
        (dict(email_claim=None), "email_claim must not be empty"),
        (
            dict(email_domain="example.org", require_verified_email=True),
            "email_domain requires require_verified_email=false",
        ),
    ],
)
def test_invalid_identity_config(qcall, monkeypatch, changes, message):
    from sirepo.auth import oidc

    cfg = oidc._cfg.copy()
    cfg.update(changes)
    monkeypatch.setattr(oidc, "_cfg", cfg)
    monkeypatch.setattr(oidc.pkconfig, "init", lambda **kwargs: cfg)
    with pytest.raises(AssertionError, match=message):
        oidc.init_apis()


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
