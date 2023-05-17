# -*- coding: utf-8 -*-
"""Test(s) for static files

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest
import os

pytestmark = pytest.mark.skipif(
    bool(os.environ.get("SIREPO_PKCLI_SERVICE_TORNADO")),
    reason="using tornado",
)

_TEST_ID = "__NO_SUCH_STRING_IN_PAGE__"


def setup_module(module):
    os.environ.update(
        SIREPO_SERVER_GOOGLE_TAG_MANAGER_ID=_TEST_ID,
    )


def test_injection(fc):
    from pykern import pkcompat, pkunit
    from pykern.pkdebug import pkdc, pkdp, pkdlog
    from pykern.pkunit import pkeq, pkok, pkre
    import re

    # test non-static page
    r = fc.get("/myapp")
    pkok(
        not re.search(r"googletag", pkcompat.from_bytes(r.data)),
        "Unexpected injection of googletag data={}",
        r.data,
    )

    # test successful injection
    r = fc.get("/en/landing.html")
    pkre(_TEST_ID, pkcompat.from_bytes(r.data))
