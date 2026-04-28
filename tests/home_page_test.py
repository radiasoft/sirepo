"""Test home page subdir configuration

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def setup_module(module):
    import os

    os.environ["SIREPO_FEATURE_CONFIG_HOME_PAGE_SUBDIR"] = "wp_en"


def test_wp_en(fc):
    from pykern.pkunit import pkre

    pkre("Sirepo by RadiaSoft", fc.sr_get("/en/").data)
