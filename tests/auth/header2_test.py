"""Header authentication through real HTTP and WebSocket requests.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import pytest


@pytest.fixture(scope="module")
def client():
    from pykern import pkio, pkunit
    from sirepo import const, srunit
    import os
    import requests
    import subprocess
    import time

    p = str(
        pkunit.unbound_localhost_tcp_port(
            const.TEST_PORT_RANGE.start, const.TEST_PORT_RANGE.stop
        )
    )
    env = PKDict(os.environ).pkupdate(
        SIREPO_AUTH_METHODS="header",
        SIREPO_AUTH_HEADER_TKN="proxy-test-secret",
        SIREPO_AUTH_HEADER_USERNAME_HEADER="x-proxy-user",
        SIREPO_AUTH_HEADER_TOKEN_HEADER="x-proxy-token",
        SIREPO_FEATURE_CONFIG_SIM_TYPES="myapp",
        SIREPO_FEATURE_CONFIG_UI_WEBSOCKET="0",
        SIREPO_PKCLI_SERVICE_IP="127.0.0.1",
        SIREPO_PKCLI_SERVICE_PORT=p,
        SIREPO_PKCLI_SERVICE_USE_RELOADER="0",
    )
    c = srunit.http_client(env=env, sim_types="myapp", port=p)
    c.sr_sim_type_set("myapp")
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
                pkunit.pkeq(None, proc.poll(), "server exited; see server.log")
                try:
                    requests.get(
                        c.http_prefix + "/auth-state", timeout=1
                    ).raise_for_status()
                    break
                except requests.exceptions.ConnectionError:
                    time.sleep(0.1)
            else:
                pkunit.pkfail("server did not become responsive; see server.log")
            yield c
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
    pkunit.pkok(
        "Traceback" not in pkio.read_text(pkunit.work_dir().join("server.log")),
        "unexpected server exception; see server.log",
    )


@pytest.fixture
def proxy_client(client):
    client.cookie_jar.clear()
    return client


def test_login_and_simulations(proxy_client):
    from pykern import pkunit

    c = proxy_client
    a = _state(c, "Owner@Example.com")
    pkunit.pkeq(True, a.isLoggedIn)
    pkunit.pkeq(False, a.guestIsOnlyMethod)
    pkunit.pkeq(True, a.needCompleteRegistration)
    pkunit.pkeq(None, a.displayName)
    pkunit.pkeq("owner@example.com", a.userName)
    pkunit.pkeq("header", a.method)
    pkunit.pkeq(["header"], a.visibleMethods)
    c.cookie_jar.clear()
    pending = _state(c, "owner@example.com")
    pkunit.pkeq(a.uid, pending.uid)
    pkunit.pkeq(True, pending.needCompleteRegistration)
    pkunit.pkeq(True, _state(c, None, None).needCompleteRegistration)
    c.sr_post(
        "listSimulations",
        PKDict(simulationType="myapp"),
        raw_response=True,
        redirect=False,
    ).assert_http_redirect("complete-registration")
    c.sr_post(
        "authCompleteRegistration",
        PKDict(displayName="Simulation Owner"),
    )
    a = _state(c, "owner@example.com")
    pkunit.pkeq(False, a.needCompleteRegistration)
    pkunit.pkeq("Simulation Owner", a.displayName)
    d = c.sr_post(
        "newSimulation",
        PKDict(simulationType="myapp", name="Proxy login simulation", folder="/"),
    )
    sid = d.models.simulation.simulationId
    pkunit.pkeq(a.uid, _state(c, "other").uid)
    for user, owns in (("other", False), ("owner@example.com", True)):
        c.sr_get("authLogout", redirect=False)
        if _state(c, user).needCompleteRegistration:
            c.sr_post(
                "authCompleteRegistration",
                PKDict(displayName="Other User"),
                headers=_headers(user),
            )
        simulations = c.sr_post(
            "listSimulations",
            PKDict(simulationType="myapp"),
            headers=_headers(user),
        )
        pkunit.pkeq(owns, sid in [s.simulationId for s in simulations])
    c.cookie_jar.clear()
    a2 = _state(c, "owner@example.com")
    pkunit.pkeq(a.uid, a2.uid)
    pkunit.pkeq("Simulation Owner", a2.displayName)
    pkunit.pkeq(False, a2.needCompleteRegistration)


def test_invalid_credentials(proxy_client):
    from pykern import pkunit

    c = proxy_client
    for user, token in (
        ("credentials", None),
        (None, "proxy-test-secret"),
        ("credentials", ""),
        ("credentials", "wrong"),
        ("credentials", "proxy-test-secret, proxy-test-secret"),
        ("", "proxy-test-secret"),
        ("bad name", "proxy-test-secret"),
        ("a, b", "proxy-test-secret"),
        ("x" * 256, "proxy-test-secret"),
    ):
        c.cookie_jar.clear()
        c.sr_get(
            "authHeaderLogin",
            PKDict(simulation_type="myapp"),
            headers=_headers(user, token),
            redirect=False,
        ).assert_http_status(403)
        a = _state(c, "credentials")
        pkunit.pkeq(a.uid, _state(c, user, token).uid)
        pkunit.pkeq(a.uid, _state(c, None, None).uid)


def test_anonymous_and_cookie_requirement(proxy_client):
    from pykern import pkunit

    c = proxy_client
    c.sr_get(
        "authHeaderLogin",
        PKDict(simulation_type="myapp"),
        redirect=False,
    ).assert_http_status(403)
    pkunit.pkeq(False, _state(c, None, None).isLoggedIn)
    pkunit.pkeq(
        False,
        _parse_state(
            c.sr_get("authState", headers=_headers("not-a-login")).data
        ).isLoggedIn,
    )
    r = c.sr_post(
        "listSimulations",
        PKDict(simulationType="myapp"),
        raw_response=True,
        redirect=False,
    )
    r.assert_http_redirect("login")
    c.cookie_jar.clear()
    r = c.sr_post(
        "authCompleteRegistration",
        PKDict(displayName="No Cookie"),
        headers=_headers("no-cookie"),
        raw_response=True,
        redirect=False,
    )
    r.assert_http_redirect("missing-cookies")


def test_logout(proxy_client):
    from pykern import pkunit

    c = proxy_client
    u = _state(c, "logout-user").uid
    c.sr_get("authLogout", redirect=False)
    pkunit.pkeq(False, _state(c, None, None).isLoggedIn)
    pkunit.pkeq(
        False,
        _parse_state(
            c.sr_get("authState", headers=_headers("logout-user")).data
        ).isLoggedIn,
    )
    pkunit.pkeq(u, _state(c, "logout-user").uid)


def test_websocket(proxy_client):
    from pykern import pkunit
    from websockets.sync.client import connect
    import requests

    c = proxy_client
    a = _state(c, "websocket-user")
    for credentials in (
        {},
        _headers("websocket-user"),
        _headers("different-user"),
        _headers("websocket-user", None),
        _headers(None),
        _headers("websocket-user", "wrong"),
    ):
        h = dict(credentials)
        h.update(
            requests.Request("GET", c.http_prefix, cookies=c.cookie_jar)
            .prepare()
            .headers
        )
        with connect(
            c.http_prefix.replace("http:", "ws:") + "/ws", additional_headers=h
        ) as ws:
            for seq in (1, 2):
                response_header, content = _websocket_request(ws, seq)
                pending = _parse_state(content)
                pkunit.pkeq(a.uid, pending.uid)
                pkunit.pkeq(True, pending.needCompleteRegistration)
    c.cookie_jar.clear()
    pkunit.pkeq(False, _state(c, None, None).isLoggedIn)
    for user, token in (
        ("websocket-user", "proxy-test-secret"),
        ("websocket-user", None),
        (None, "proxy-test-secret"),
        ("websocket-user", "wrong"),
    ):
        h = _headers(user, token)
        h.update(
            requests.Request("GET", c.http_prefix, cookies=c.cookie_jar)
            .prepare()
            .headers
        )
        with connect(
            c.http_prefix.replace("http:", "ws:") + "/ws", additional_headers=h
        ) as ws:
            response_header, content = _websocket_request(ws, 1)
            pkunit.pkeq(False, _parse_state(content).isLoggedIn)


def _headers(user, token="proxy-test-secret"):
    return {
        k: v
        for k, v in (("X-Proxy-User", user), ("X-Proxy-Token", token))
        if v is not None
    }


def _state(client, user, token="proxy-test-secret"):
    if user is not None or token is not None:
        r = client.sr_get(
            "authHeaderLogin",
            PKDict(simulation_type="myapp"),
            headers=_headers(user, token),
            redirect=False,
        )
        r.assert_http_redirect("/myapp")
    r = client.sr_get("authState")
    r.assert_http_status(200)
    return _parse_state(r.data)


def _parse_state(data):
    from pykern import pkcompat, pkjson
    import re

    return pkjson.load_any(re.search(r"(\{.*\})", pkcompat.from_bytes(data)).group(1))


def _websocket_request(ws, seq):
    from pykern import pkunit
    from sirepo import const, uri
    import msgpack

    ws.send(
        msgpack.packb(
            PKDict(
                kind=const.SCHEMA_COMMON.websocketMsg.kind.httpRequest,
                version=const.SCHEMA_COMMON.websocketMsg.version,
                reqSeq=seq,
                uri=uri.server_route("authState", None, None),
            )
        )
    )
    for _ in range(3):
        unpacker = msgpack.Unpacker(raw=False)
        unpacker.feed(ws.recv(timeout=5))
        h = unpacker.unpack()
        content = unpacker.unpack()
        if h["kind"] == const.SCHEMA_COMMON.websocketMsg.kind.asyncMsg:
            pkunit.pkeq(const.SCHEMA_COMMON.websocketMsg.method.setCookies, h["method"])
            continue
        pkunit.pkeq(seq, h["reqSeq"])
        return h, content
    pkunit.pkfail("too many asynchronous cookie updates before WebSocket reply")
