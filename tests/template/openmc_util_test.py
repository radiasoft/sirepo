"""test openmc_util methods

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


def test_openmc_util():
    from pykern.pkcollections import PKDict
    from sirepo.template.openmc_util import wo_to_ao
    from pykern import pkunit

    pkunit.pkeq(
        PKDict(
            Fe=74.07632354240252,
            C=25.92367645759749,
        ),
        wo_to_ao(
            PKDict(
                Fe=93.0,
                C=7.0,
            )
        ),
    )
    pkunit.pkeq(
        PKDict(
            Fe56=74.02766312403061,
            C12=25.972336875969383,
        ),
        wo_to_ao(
            PKDict(
                Fe56=93.0,
                C12=7.0,
            )
        ),
    )
