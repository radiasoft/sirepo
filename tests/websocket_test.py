"""test websockets

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import os
import pytest


def setup_module(module):
    os.environ.update(
        SIREPO_FEATURE_CONFIG_API_MODULES="srunit_api",
    )


pytestmark = pytest.mark.skipif(
    os.getenv("SIREPO_FEATURE_CONFIG_UI_WEBSOCKET", "1") != "1",
    reason="SIREPO_FEATURE_CONFIG_UI_WEBSOCKET is not enabled",
)


def test_serialization(fc):
    from pykern.pkcollections import PKDict
    from pykern import pkunit

    # Server: TypeError: can not serialize 'datetime.datetime' object
    fc.assert_post_will_redirect(
        "/error",
        "srUnitCase",
        PKDict(type=False, filename="serialization"),
        redirect=False,
    )
