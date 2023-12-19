# -*- coding: utf-8 -*-
"""test websockets

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def setup_module(module):
    import os

    os.environ.update(
        SIREPO_FEATURE_CONFIG_UI_WEBSOCKET="1",
        SIREPO_FEATURE_CONFIG_API_MODULES="srunit_api",
    )


def test_serialization(fc):
    from pykern.pkcollections import PKDict
    from pykern import pkunit

    with pkunit.pkexcept("routeName=error"):
        fc.sr_post("srUnitCase", PKDict(type=False, filename="serialization"))
