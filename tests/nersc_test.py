# -*- coding: utf-8 -*-
"""NERSC-related tests.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import sirepo.util
from pykern.pkcollections import PKDict


def test_nersc_project(monkeypatch):
    from sirepo import nersc
    from pykern.pkunit import pkeq, pkok, pkre, pkfail, pkexcept

    _ERROR = "ERROR"
    _VALID_PROJECT = "VALID_TEST_PROJECT"
    _NO_SUCH_PROJECT = "NOT_" + _VALID_PROJECT

    mock_output = PKDict()
    mock_output[_VALID_PROJECT] = (
        f'[{{"fs": "user usage on HPSS charged to {_VALID_PROJECT}"}}]'
    )
    mock_output[_NO_SUCH_PROJECT] = "[]"
    mock_output[_ERROR] = "arbitrary hpssquota error"

    monkeypatch.setattr(nersc, "_hpssquota", lambda p: mock_output[p])

    with pkexcept(sirepo.util.UserAlert):
        nersc.sbatch_project_option(_ERROR)

    with pkexcept(sirepo.util.UserAlert):
        nersc.sbatch_project_option(_NO_SUCH_PROJECT)

    pkeq("", nersc.sbatch_project_option(""))
    pkre(_VALID_PROJECT, nersc.sbatch_project_option(_VALID_PROJECT))
