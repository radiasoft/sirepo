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
