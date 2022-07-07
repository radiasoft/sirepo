# -*- coding: utf-8 -*-
u"""test sim_types

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
import os
import pytest


def setup_module(module):
    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES='xyz1',
        SIREPO_FEATURE_CONFIG_MODERATED_SIM_TYPES='xyz1',
    )


def test_1():
    from pykern import pkunit
    import sirepo.feature_config

    sirepo.feature_config.cfg()
