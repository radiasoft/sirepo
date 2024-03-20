import pytest


def test_favicon(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq
    import sirepo.resource
    import sys

    for a, p in PKDict(favicon="favicon.ico", faviconPng="favicon.png").items():
        r = fc.sr_get(a)
        with open(sirepo.resource.static("img", p), "rb") as f:
            s = f.read()
            pkeq(len(s), len(r.data))


def test_find_by_name(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq

    r = fc.sr_get(
        "findByName",
        PKDict(
            simulation_type="srw",
            application_mode="default",
            simulation_name="Undulator Radiation",
        ),
        redirect=False,
    )
    r.assert_http_status(302)
    pkeq(r.header_get("Location"), "/srw#/findByName/default/Undulator%20Radiation")
