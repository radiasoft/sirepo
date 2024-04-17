"""test srunit is working properly

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_assert_status_in_post_form(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkexcept

    with pkexcept("unexpected status"):
        fc.sr_post_form(
            "simulationSchema",
            data=PKDict(simulationType="xyzzy"),
        )
