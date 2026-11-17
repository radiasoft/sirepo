"""OIDC over HTTP with a local provider and signed ID tokens.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import pytest


@pytest.fixture(scope="module", params=[False, True], ids=["unmoderated", "moderated"])
def service(request):
    from authlib.jose import JsonWebKey, JsonWebToken
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from pykern import pkio, pkunit
    from sirepo import const, srunit
    import base64
    import hashlib
    import json
    import os
    import requests
    import secrets
    import subprocess
    import threading
    import time
    import urllib.parse

    p = PKDict(
        moderated=request.param,
        key=JsonWebKey.generate_key("RSA", 2048, is_private=True),
        codes={},
        claims={},
        omit_id_token=False,
        token_error=False,
        wrong_key=False,
        jwks_error=False,
        missing_claim=False,
        discovery_issuer=None,
        exchanges=0,
        token_started=threading.Event(),
        token_release=threading.Event(),
        block_token=False,
    )

    class Provider(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urllib.parse.urlsplit(self.path)
            if path.path == "/.well-known/openid-configuration":
                return self._json(
                    dict(
                        issuer=p.discovery_issuer or p.issuer,
                        authorization_endpoint=p.issuer + "/authorize",
                        token_endpoint=p.issuer + "/token",
                        jwks_uri=p.issuer + "/jwks",
                    )
                )
            if path.path == "/jwks":
                if p.jwks_error:
                    return self._json(dict(error="unavailable"), status=503)
                return self._json(dict(keys=[p.key.as_dict(is_private=False)]))
            assert path.path == "/authorize"
            args = {k: v[0] for k, v in urllib.parse.parse_qs(path.query).items()}
            assert args["response_type"] == "code"
            assert args["scope"] == "openid email profile"
            assert args["code_challenge_method"] == "S256"
            assert args["client_id"] == "sirepo-test"
            assert args["redirect_uri"] == p.callback
            code = secrets.token_urlsafe(24)
            p.codes[code] = args
            self.send_response(302)
            self.send_header(
                "Location",
                p.callback
                + "?"
                + urllib.parse.urlencode(dict(code=code, state=args["state"])),
            )
            self.end_headers()

        def do_POST(self):
            assert self.path == "/token"
            assert (
                self.headers["Authorization"]
                == "Basic " + base64.b64encode(b"sirepo-test:test-secret").decode()
            )
            args = {
                k: v[0]
                for k, v in urllib.parse.parse_qs(
                    self.rfile.read(int(self.headers["Content-Length"])).decode()
                ).items()
            }
            assert args["grant_type"] == "authorization_code"
            assert args["redirect_uri"] == p.callback
            request = p.codes.pop(args["code"])
            assert (
                request["code_challenge"]
                == base64.urlsafe_b64encode(
                    hashlib.sha256(args["code_verifier"].encode()).digest()
                )
                .rstrip(b"=")
                .decode()
            )
            p.exchanges += 1
            if p.block_token:
                p.token_started.set()
                assert p.token_release.wait(timeout=10)
            if p.token_error:
                return self._json(dict(error="invalid_grant"), status=400)
            claims = dict(
                iss=p.issuer,
                sub="provider-subject",
                aud="sirepo-test",
                iat=int(time.time()),
                exp=int(time.time()) + 300,
                nonce=request["nonce"],
                email="oidc@example.com",
                email_verified=True,
            )
            claims.update(p.claims)
            if p.missing_claim:
                claims.pop("exp")
            token = dict(access_token="test-access-token", token_type="Bearer")
            if not p.omit_id_token:
                token["id_token"] = (
                    JsonWebToken(["RS256"])
                    .encode(
                        {"alg": "RS256"},
                        claims,
                        (
                            JsonWebKey.generate_key("RSA", 2048, is_private=True)
                            if p.wrong_key
                            else p.key
                        ),
                    )
                    .decode()
                )
            return self._json(token)

        def log_message(self, *args):
            pass

        def _json(self, data, status=200):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())

    provider = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=provider.serve_forever, daemon=True)
    thread.start()
    p.issuer = f"http://127.0.0.1:{provider.server_port}"
    port = pkunit.unbound_localhost_tcp_port(
        const.TEST_PORT_RANGE.start, const.TEST_PORT_RANGE.stop
    )
    p.url = f"http://127.0.0.1:{port}"
    p.callback = p.url + "/auth-oidc-callback"
    env = PKDict(os.environ).pkupdate(
        SIREPO_AUTH_METHODS="guest:oidc",
        SIREPO_AUTH_OIDC_ISSUER=p.issuer,
        SIREPO_AUTH_OIDC_CLIENT_ID="sirepo-test",
        SIREPO_AUTH_OIDC_CLIENT_SECRET="test-secret",
        SIREPO_AUTH_OIDC_REDIRECT_URI=p.callback,
        SIREPO_FEATURE_CONFIG_SIM_TYPES="myapp",
        SIREPO_FEATURE_CONFIG_MODERATED_SIM_TYPES="myapp" if p.moderated else "",
        SIREPO_FEATURE_CONFIG_UI_WEBSOCKET="0",
        SIREPO_FEATURE_CONFIG_IS_REGISTRATION_MODERATED=str(int(p.moderated)),
        SIREPO_SMTP_SERVER="dev",
        SIREPO_PKCLI_SERVICE_IP="127.0.0.1",
        SIREPO_PKCLI_SERVICE_PORT=str(port),
        SIREPO_PKCLI_SERVICE_USE_RELOADER="0",
    )
    srunit.http_client(env=env, sim_types="myapp", port=port)
    env.pop("PYKERN_PKUNIT_TEST_FILE", None)
    try:
        with open(str(pkunit.work_dir().join("server.log")), "w") as log:
            proc = subprocess.Popen(
                ("sirepo", "service", "server"),
                env=env,
                cwd=str(pkunit.work_dir()),
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                for _ in range(100):
                    assert proc.poll() is None, "server exited; see server.log"
                    try:
                        requests.get(
                            p.url + "/auth-state", timeout=1
                        ).raise_for_status()
                        break
                    except requests.exceptions.ConnectionError:
                        time.sleep(0.1)
                else:
                    pytest.fail("server did not start; see server.log")
                yield p
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        assert "Traceback" not in pkio.read_text(pkunit.work_dir().join("server.log"))
    finally:
        provider.shutdown()
        provider.server_close()
        thread.join(timeout=5)


def test_login_registration_and_cookie_recovery(service):
    from pykern import pkunit
    import requests
    import sqlite3

    p = service
    with requests.Session() as session:
        assert _state(p, session).isLoggedIn is False
        callback = _authorize(p, session)
        r = session.get(callback, allow_redirects=False)
        assert _redirect(r) == "/myapp#/oidc-registration"
        state = _state(p, session)
        assert state.visibleMethods == ["guest", "oidc"]
        assert state.isLoggedIn is False
        with sqlite3.connect(str(pkunit.work_dir().join("db", "auth.db"))) as db:
            assert db.execute("SELECT uid FROM auth_email_user_t").fetchall() == []
            assert db.execute("SELECT uid FROM user_registration_t").fetchall() == []
        if p.moderated:
            for reason in (None, "", " \t", 12):
                r = session.post(
                    p.url + "/auth-oidc-complete-registration",
                    json=dict(
                        simulationType="myapp",
                        displayName="OIDC User",
                        reason=reason,
                    ),
                )
                assert r.status_code == 500
                assert _state(p, session).isLoggedIn is False
        r = session.post(
            p.url + "/auth-oidc-complete-registration",
            json=dict(
                simulationType="myapp",
                displayName="OIDC User",
                reason="Research with OIDC",
            ),
        )
        r.raise_for_status()
        state = _state(p, session)
        assert state.needCompleteRegistration is False
        assert state.method == "oidc"
        assert state.userName == "oidc@example.com"
        uid = state.uid
        assert (
            session.post(
                p.url + "/auth-oidc-complete-registration",
                json=dict(
                    simulationType="myapp", displayName="Replay", reason="Replay"
                ),
            ).json()["srException"]["routeName"]
            == "loginFail"
        )
        with sqlite3.connect(str(pkunit.work_dir().join("db", "auth.db"))) as db:
            rows = db.execute(
                "SELECT status FROM user_role_moderation_t WHERE uid=?",
                (uid,),
            ).fetchall()
            assert rows == ([("pending",)] if p.moderated else [])
            if p.moderated:
                db.execute(
                    "INSERT INTO user_role_t (uid, role) VALUES (?, 'sim_type_myapp')",
                    (uid,),
                )
        session.cookies.clear()
        assert _state(p, session).isLoggedIn is False
        assert (
            _redirect(session.get(_authorize(p, session), allow_redirects=False))
            == "/myapp#/simulations"
        )
        state = _state(p, session)
        assert state.uid == uid
        assert state.displayName == "OIDC User"
        assert (
            _redirect(session.get(p.url + "/auth-logout", allow_redirects=False)) == "/"
        )
        assert _state(p, session).isLoggedIn is False


@pytest.mark.parametrize("existing", [True, False], ids=["existing-user", "new-user"])
def test_guest_simulations(service, existing):
    from pykern import pkunit
    import requests
    import sqlite3

    p = service
    with requests.Session() as session:
        _state(p, session)
        r = session.post(p.url + "/auth-guest-login/myapp")
        r.raise_for_status()
        guest_uid = _state(p, session).uid
        assert (
            session.post(
                p.url + "/save-moderation-reason",
                json=dict(simulationType="myapp", reason="Guest request"),
            ).status_code
            == 403
        )
        r = session.post(
            p.url + "/new-simulation",
            json=dict(simulationType="myapp", name="Guest simulation", folder="/"),
        )
        r.raise_for_status()
        sid = r.json()["models"]["simulation"]["simulationId"]
        if not existing:
            p.claims = {"email": "guest-migration@example.com"}
        try:
            _redirect(session.get(_authorize(p, session), allow_redirects=False))
            state = _state(p, session)
            assert (state.uid != guest_uid) == existing
            if not existing:
                session.post(
                    p.url + "/auth-oidc-complete-registration",
                    json=dict(
                        simulationType="myapp",
                        displayName="Former Guest",
                        reason="Guest migration test",
                    ),
                ).raise_for_status()
                if p.moderated:
                    with sqlite3.connect(
                        str(pkunit.work_dir().join("db", "auth.db"))
                    ) as db:
                        db.execute(
                            "INSERT OR IGNORE INTO user_role_t (uid, role) VALUES (?, 'sim_type_myapp')",
                            (_state(p, session).uid,),
                        )
            r = session.post(
                p.url + "/simulation-list", json=dict(simulationType="myapp")
            )
            r.raise_for_status()
            assert sid in [s["simulationId"] for s in r.json()]
        finally:
            p.claims = {}


def test_registration_expiry_and_browser_binding(service):
    from pykern import pkunit
    import requests
    import sqlite3

    p = service
    p.claims = {"email": "abandoned@example.com"}
    try:
        with requests.Session() as session, requests.Session() as stranger:
            _redirect(session.get(_authorize(p, session), allow_redirects=False))
            _state(p, stranger)
            data = dict(
                simulationType="myapp", displayName="Abandoned User", reason="Research"
            )
            assert (
                stranger.post(
                    p.url + "/auth-oidc-complete-registration", json=data
                ).json()["srException"]["routeName"]
                == "loginFail"
            )
            with sqlite3.connect(str(pkunit.work_dir().join("db", "auth.db"))) as db:
                db.execute(
                    "UPDATE auth_oidc_login_t SET expires='1970-01-01 00:00:00' WHERE email=?",
                    ("abandoned@example.com",),
                )
            assert (
                session.post(
                    p.url + "/auth-oidc-complete-registration", json=data
                ).json()["srException"]["routeName"]
                == "loginFail"
            )
            assert _state(p, session).isLoggedIn is False
            with sqlite3.connect(str(pkunit.work_dir().join("db", "auth.db"))) as db:
                assert (
                    db.execute(
                        "SELECT uid FROM auth_email_user_t WHERE unverified_email=?",
                        ("abandoned@example.com",),
                    ).fetchall()
                    == []
                )
    finally:
        p.claims = {}


def test_moderation_request_and_approval(service):
    from pykern import pkunit
    import requests
    import sqlite3

    p = service
    if not p.moderated:
        return
    role = "sim_type_myapp"
    with requests.Session() as applicant, requests.Session() as moderator:
        _redirect(applicant.get(_authorize(p, applicant), allow_redirects=False))
        uid = _state(p, applicant).uid
        with sqlite3.connect(str(pkunit.work_dir().join("db", "auth.db"))) as db:
            db.execute("DELETE FROM user_role_t WHERE uid=? AND role=?", (uid, role))
            db.execute("DELETE FROM user_role_moderation_t WHERE uid=?", (uid,))
        r = applicant.post(
            p.url + "/simulation-list", json=dict(simulationType="myapp")
        )
        assert r.json()["srException"]["routeName"] == "moderationRequest"
        r = applicant.post(
            p.url + "/save-moderation-reason",
            json=dict(simulationType="myapp", reason="OIDC application access"),
        )
        assert r.json()["state"] == "ok", r.text
        r = applicant.post(
            p.url + "/simulation-list", json=dict(simulationType="myapp")
        )
        assert r.json()["srException"]["routeName"] == "moderationPending"
        p.claims = {"email": "moderator@example.com"}
        try:
            _redirect(moderator.get(_authorize(p, moderator), allow_redirects=False))
            moderator.post(
                p.url + "/auth-oidc-complete-registration",
                json=dict(
                    simulationType="myapp",
                    displayName="Moderator",
                    reason="Moderating requests",
                ),
            ).raise_for_status()
            moderator_uid = _state(p, moderator).uid
            with sqlite3.connect(str(pkunit.work_dir().join("db", "auth.db"))) as db:
                db.execute(
                    "INSERT INTO user_role_t (uid, role) VALUES (?, 'adm')",
                    (moderator_uid,),
                )
            r = moderator.post(
                p.url + "/adm-moderate",
                json=dict(uid=uid, role=role, status="approve"),
            )
            assert r.json()["state"] == "ok", r.text
        finally:
            p.claims = {}
        r = applicant.post(
            p.url + "/simulation-list", json=dict(simulationType="myapp")
        )
        assert isinstance(r.json(), list), r.text


@pytest.mark.parametrize("registration", [False, True])
def test_logout_cancels_pending_flow(service, registration):
    from pykern import pkunit
    import requests
    import sqlite3

    p = service
    p.claims = {"email": "logout-pending@example.com"} if registration else {}
    try:
        with requests.Session() as session:
            callback = _authorize(p, session)
            if registration:
                _redirect(session.get(callback, allow_redirects=False))
            saved = session.cookies.copy()
            exchanges = p.exchanges
            _redirect(session.get(p.url + "/auth-logout", allow_redirects=False))
            session.cookies.clear()
            session.cookies.update(saved)
            if registration:
                r = session.post(
                    p.url + "/auth-oidc-complete-registration",
                    json=dict(
                        simulationType="myapp", displayName="Canceled", reason="Test"
                    ),
                )
                assert r.json()["srException"]["routeName"] == "loginFail"
            else:
                _login_failure(session.get(callback, allow_redirects=False))
            assert _state(p, session).isLoggedIn is False
            assert p.exchanges == exchanges
            with sqlite3.connect(str(pkunit.work_dir().join("db", "auth.db"))) as db:
                assert (
                    db.execute(
                        "SELECT uid FROM auth_email_user_t WHERE unverified_email=?",
                        ("logout-pending@example.com",),
                    ).fetchall()
                    == []
                )
    finally:
        p.claims = {}


@pytest.mark.parametrize("change", ["logout", "new-guest", "registered-login"])
def test_context_change_during_token_exchange(service, change):
    from concurrent.futures import ThreadPoolExecutor
    import requests

    p = service
    p.block_token = True
    p.token_started.clear()
    p.token_release.clear()
    try:
        with requests.Session() as session, requests.Session() as callback_browser:
            callback = _authorize(p, session)
            callback_browser.cookies.update(session.cookies)
            with ThreadPoolExecutor(max_workers=1) as executor:
                result = executor.submit(
                    callback_browser.get, callback, allow_redirects=False
                )
                try:
                    assert p.token_started.wait(timeout=5)
                    if change == "logout":
                        _redirect(
                            session.get(p.url + "/auth-logout", allow_redirects=False)
                        )
                    elif change == "new-guest":
                        session.post(
                            p.url + "/auth-guest-login/myapp"
                        ).raise_for_status()
                        uid = _state(p, session).uid
                    else:
                        p.block_token = False
                        _redirect(
                            session.get(_authorize(p, session), allow_redirects=False)
                        )
                        uid = _state(p, session).uid
                finally:
                    p.token_release.set()
                response = result.result(timeout=10)
                _login_failure(response)
                assert "Set-Cookie" not in response.headers
            assert _state(p, callback_browser).isLoggedIn is False
            if change == "logout":
                assert _state(p, session).isLoggedIn is False
            else:
                assert _state(p, session).uid == uid
    finally:
        p.block_token = False
        p.token_release.set()


@pytest.mark.parametrize("registration", [False, True])
@pytest.mark.parametrize("initial_guest", [False, True])
def test_changed_guest_context(service, registration, initial_guest):
    import requests

    p = service
    p.claims = {"email": "context-change@example.com"} if registration else {}
    try:
        with requests.Session() as session:
            _state(p, session)
            if initial_guest:
                session.post(p.url + "/auth-guest-login/myapp").raise_for_status()
            callback = _authorize(p, session)
            if registration:
                _redirect(session.get(callback, allow_redirects=False))
            saved = session.cookies.copy()
            # A different tab establishes a new guest login.
            if initial_guest:
                session.get(p.url + "/auth-logout")
            session.post(p.url + "/auth-guest-login/myapp").raise_for_status()
            uid = _state(p, session).uid
            if registration:
                r = session.post(
                    p.url + "/auth-oidc-complete-registration",
                    json=dict(
                        simulationType="myapp",
                        displayName="Wrong Context",
                        reason="Test",
                    ),
                )
                assert r.json()["srException"]["routeName"] == "loginFail"
            else:
                _login_failure(session.get(callback, allow_redirects=False))
            assert _state(p, session).uid == uid
            assert _state(p, session).isGuestUser is True
            # Even a saved pre-switch cookie cannot revive the canceled flow.
            session.cookies.clear()
            session.cookies.update(saved)
            if registration:
                assert (
                    session.post(
                        p.url + "/auth-oidc-complete-registration",
                        json=dict(
                            simulationType="myapp", displayName="Replay", reason="Test"
                        ),
                    ).json()["srException"]["routeName"]
                    == "loginFail"
                )
            else:
                _login_failure(session.get(callback, allow_redirects=False))
    finally:
        p.claims = {}


def test_non_guest_login_cannot_be_replaced(service):
    import requests

    p = service
    with requests.Session() as session:
        _redirect(session.get(_authorize(p, session), allow_redirects=False))
        uid = _state(p, session).uid
        exchanges = p.exchanges
        _login_failure(
            session.get(p.url + "/auth-oidc-login/myapp", allow_redirects=False)
        )
        assert _state(p, session).uid == uid
        assert p.exchanges == exchanges


def test_email_identity(service):
    import requests

    p = service
    with requests.Session() as session:
        _redirect(session.get(_authorize(p, session), allow_redirects=False))
        uid = _state(p, session).uid
        try:
            p.claims = {"sub": "different-subject", "email": "OIDC@example.com"}
            session.cookies.clear()
            _redirect(session.get(_authorize(p, session), allow_redirects=False))
            assert _state(p, session).uid == uid
            p.claims = {"email": "new-address@example.com"}
            session.cookies.clear()
            _redirect(session.get(_authorize(p, session), allow_redirects=False))
            state = _state(p, session)
            assert state.isLoggedIn is False
        finally:
            p.claims = {}


@pytest.mark.parametrize(
    "claims",
    [
        {"iss": "https://wrong.example"},
        {"aud": "wrong-client"},
        {"aud": ["sirepo-test", "other-client"], "azp": "other-client"},
        {"nonce": "wrong-nonce"},
        {"exp": 1},
        {"iat": 9999999999},
        {"sub": ""},
        {"email_verified": False},
        {"email_verified": "true"},
        {"email_verified": None},
    ],
)
def test_invalid_claims(service, claims):
    from pykern import pkio, pkunit
    import requests

    service.claims = claims
    log = pkunit.work_dir().join("server.log")
    offset = len(pkio.read_text(log))
    try:
        with requests.Session() as session:
            r = session.get(_authorize(service, session), allow_redirects=False)
            _login_failure(r)
            assert _state(service, session).isLoggedIn is False
            if "email_verified" in claims:
                assert "OIDC identity validation failed" in pkio.read_text(log)[offset:]
    finally:
        service.claims = {}


def test_state_binding_consumption_and_denial(service):
    import requests
    import urllib.parse

    p = service
    with requests.Session() as session, requests.Session() as stranger:
        callback = _authorize(p, session)
        exchanges = p.exchanges
        _login_failure(stranger.get(callback, allow_redirects=False))
        _login_failure(
            session.get(callback + "&state=duplicate", allow_redirects=False)
        )
        state = urllib.parse.parse_qs(urllib.parse.urlsplit(callback).query)["state"][0]
        _login_failure(
            session.get(
                p.callback + "?state=" + state + "&error=access_denied",
                allow_redirects=False,
            )
        )
        _login_failure(session.get(callback, allow_redirects=False))
        assert p.exchanges == exchanges
        callback = _authorize(p, session)
        saved = session.cookies.copy()
        assert (
            _redirect(session.get(callback, allow_redirects=False))
            == "/myapp#/simulations"
        )
        session.cookies.clear()
        session.cookies.update(saved)
        exchanges = p.exchanges
        _login_failure(session.get(callback, allow_redirects=False))
        assert p.exchanges == exchanges


def test_expired_and_replaced_state(service):
    from pykern import pkunit
    import requests
    import sqlite3
    import urllib.parse

    p = service
    with requests.Session() as session:
        old = _authorize(p, session)
        callback = _authorize(p, session)
        old_state = urllib.parse.parse_qs(urllib.parse.urlsplit(old).query)["state"][0]
        with sqlite3.connect(str(pkunit.work_dir().join("db", "auth.db"))) as db:
            assert (
                db.execute(
                    "SELECT state FROM auth_oidc_login_t WHERE state=?", (old_state,)
                ).fetchall()
                == []
            )
        exchanges = p.exchanges
        _login_failure(session.get(old, allow_redirects=False))
        state = urllib.parse.parse_qs(urllib.parse.urlsplit(callback).query)["state"][0]
        with sqlite3.connect(str(pkunit.work_dir().join("db", "auth.db"))) as db:
            db.execute(
                "UPDATE auth_oidc_login_t SET expires=? WHERE state=?",
                ("1970-01-01 00:00:00", state),
            )
        _login_failure(session.get(callback, allow_redirects=False))
        assert p.exchanges == exchanges
        with sqlite3.connect(str(pkunit.work_dir().join("db", "auth.db"))) as db:
            assert db.execute(
                "SELECT state FROM auth_oidc_login_t WHERE state=?", (state,)
            ).fetchall() == [(state,)]
        # Expired requests from any browser are pruned on the next new login.
        with requests.Session() as another:
            _authorize(p, another)
        with sqlite3.connect(str(pkunit.work_dir().join("db", "auth.db"))) as db:
            assert (
                db.execute(
                    "SELECT state FROM auth_oidc_login_t WHERE state=?", (state,)
                ).fetchall()
                == []
            )


def test_discovery_issuer(service):
    from pykern import pkio, pkunit
    import requests

    service.discovery_issuer = "https://wrong.example"
    log = pkunit.work_dir().join("server.log")
    offset = len(pkio.read_text(log))
    try:
        with requests.Session() as session:
            _login_failure(
                session.get(
                    service.url + "/auth-oidc-login/myapp", allow_redirects=False
                )
            )
            assert "OIDC discovery failed" in pkio.read_text(log)[offset:]
    finally:
        service.discovery_issuer = None


@pytest.mark.parametrize(
    "error,stage",
    [
        ("omit_id_token", "token exchange"),
        ("token_error", "token exchange"),
        ("jwks_error", "signing-key retrieval"),
        ("wrong_key", "ID-token validation"),
        ("missing_claim", "ID-token validation"),
    ],
)
def test_token_failure(service, error, stage):
    from pykern import pkio, pkunit
    import requests

    service[error] = True
    log = pkunit.work_dir().join("server.log")
    offset = len(pkio.read_text(log))
    try:
        with requests.Session() as session:
            callback = _authorize(service, session)
            _login_failure(session.get(callback, allow_redirects=False))
            assert _state(service, session).isLoggedIn is False
            assert f"OIDC {stage} failed" in pkio.read_text(log)[offset:]
            _login_failure(session.get(callback, allow_redirects=False))
    finally:
        service[error] = False


def _authorize(provider, session):
    import requests

    r = session.get(provider.url + "/auth-oidc-login/myapp", allow_redirects=False)
    r = requests.get(_redirect(r), allow_redirects=False, timeout=5)
    assert r.status_code == 302
    return r.headers["Location"]


def _login_failure(response):
    from pykern import pkjson
    import re

    assert response.status_code == 200
    match = re.search(r"/\*sr_exception=(.*?)\*/", response.text)
    assert match, response.text
    error = pkjson.load_any(match.group(1))
    assert error.routeName == "loginFail"
    assert error.params.method == "oidc"
    assert error.params.reason == "oauth-state"


def _redirect(response):
    import re

    assert response.status_code == 200
    match = re.search(r'window.location = "([^"]+)"', response.text)
    assert match, response.text
    return match.group(1)


def _state(provider, session):
    from pykern import pkjson
    import re

    r = session.get(provider.url + "/auth-state", timeout=5)
    r.raise_for_status()
    return pkjson.load_any(re.search(r"(\{.*\})", r.text).group(1))
