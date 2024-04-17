"""test srunit is working properly

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def setup_module(module):
    import os

    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES="jupyterhublogin",
    )


def test_assert_status_in_post_form(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkexcept

    with pkexcept("unexpected status"):
        fc.sr_post_form(
            "simulationSchema",
            data=PKDict(simulationType="xyzzy"),
        )


def test_assert_success_sr_exception(fc):
    from pykern.pkunit import pkexcept
    from sirepo import util

    fc.sr_logout()
    r = fc.sr_get("checkAuthJupyterHub", redirect=False)
    with pkexcept(util.SRException):
        r.assert_success()
