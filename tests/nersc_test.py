# -*- coding: utf-8 -*-
"""NERSC-related tests.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_nersc_project(fc):
    from sirepo import nersc
    from pykern.pkunit import pkeq, pkok, pkre, pkfail, pkexcept

    _NO_SUCH_PROJECT = "NOT_" + nersc.VALID_TEST_ACCOUNT

    with pkexcept(nersc.invalid_project_msg(_NO_SUCH_PROJECT)):
        nersc.assert_project(_NO_SUCH_PROJECT)

    pkeq(
        nersc.sbatch_account(nersc.VALID_TEST_ACCOUNT),
        nersc.assert_project(nersc.VALID_TEST_ACCOUNT),
    )
