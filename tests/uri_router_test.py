"""Test sirepo.uri_router

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest

pytest.importorskip("srwpy.srwl_bl")


def test_error_user_agents(fc):
    from pykern import pkcompat, pkjson, pkdebug
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq, pkexcept, pkok, pkre
    from sirepo import http_request

    fc.sr_login_as_guest()
    uri = "/stateless-compute"
    d = PKDict(simulationType="srw", method="will-fail-in-job_api", models=PKDict())
    # Default user agent and protocol
    r = fc.sr_post(uri, data=d, raw_response=True)
    # WebSocket and HTTP respond differently, but sirepo.js handles the same
    r.assert_http_status(500)
    for a in (
        "python-requests/1.3",
        "python-requests/2.0",
    ):
        r = fc.sr_post(
            uri,
            headers=PKDict({"User-Agent": a}),
            data=d,
            raw_response=True,
            want_http=True,
        )
        r.assert_http_status(500)
        pkre("doctype.*server.error", r.data)
    for a in (
        None,
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.128 Safari/537.36 OPR/75.0.3969.250",
    ):
        fc.sr_post(
            uri,
            headers=PKDict({"User-Agent": a}),
            data=d,
            raw_response=True,
            want_http=True,
        )
        r.assert_http_status(500)
        pkre("doctype.*server.error", r.data)


def test_not_found(fc):
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq

    for uri in ("/some random uri", "/srw/wrong-param", "/export-archive/"):
        fc.sr_get(uri).assert_http_status(404)


def test_uri_for_api():
    from sirepo import srunit

    with srunit.quest_start() as qcall:
        from pykern.pkdebug import pkdp
        from pykern.pkunit import pkeq, pkexcept, pkre, pkeq
        from sirepo import uri_router

        uri = uri_router.uri_for_api("homePage", params={"path_info": None})
        pkeq("/en", uri)
        uri = uri_router.uri_for_api("homePage", params={"path_info": "terms.html"})
        pkeq("/en/terms.html", uri)
        with pkexcept(KeyError):
            uri_router.uri_for_api("notAnApi")
        with pkexcept("missing parameter"):
            uri_router.uri_for_api("exportArchive", {"simulation_type": "srw"})
        pkeq("/", uri_router.uri_for_api("root", params={}))
