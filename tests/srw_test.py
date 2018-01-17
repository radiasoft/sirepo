# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.srw.py`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

pytest.importorskip('srwl_bl')

from pykern import pkresource
from pykern import pkunit


def DOES_NOT_WORK_test_find_height_profile_dimension():
    from sirepo.template import srw
    for dimension in (1, 2):
        dat_file = pkresource.filename('static/dat/mirror_{}d.dat'.format(dimension), srw)
        found_dimension = srw.find_height_profile_dimension(dat_file)
        assert found_dimension == dimension


def DOES_NOT_WORK_test_find_tab_undulator_length():
    from sirepo.template import srw
    magnet = pkresource.filename('static/dat/magnetic_measurements.zip', srw)
    for case in (
            (6.82, 'ivu21_srx_g6_8c.dat', 6.8),
            ('3', 'ivu21_srx_g6_2c.dat', 6.2),
            (45, 'ivu21_srx_g40_0c.dat', 40),
    ):
        res = srw.find_tab_undulator_length(zip_file=magnet, gap=case[0])
        assert res['dat_file'] == case[1]
        assert res['closest_gap'] == case[2]
        assert abs(res['found_length'] - 2.5) < 1e-3


def test_model_defaults():
    from sirepo.template import template_common
    from sirepo import simulation_db
    res = template_common.model_defaults('trajectoryReport', simulation_db.get_schema('srw'))
    assert res == {
        'plotAxisY2': 'None',
        'timeMomentEstimation': 'auto',
        'magneticField': '2',
        'initialTimeMoment': 0.0,
        'numberOfPoints': 10000,
        'plotAxisY': 'X',
        'plotAxisX': 'Z',
        'finalTimeMoment': 0.0,
    }
    model = {
        'numberOfPoints': 10,
        'finalTimeMoment': 1.0,
    }
    template_common.update_model_defaults(model, 'trajectoryReport', simulation_db.get_schema('srw'))
    assert model['numberOfPoints'] == 10
    assert model['finalTimeMoment'] == 1.0
    assert model['plotAxisX'] == 'Z'


def test_prepare_aux_files():

    def t():
        from sirepo.template import template_common
        from pykern import pkcollections

        # Needed to initialize simulation_db
        data = pkcollections.json_load_any('''{
            "simulationType": "srw",
            "models": {
                "simulation": {
                    "sourceType": "t"
                },
                "tabulatedUndulator": {
                    "magneticFile": "magnetic_measurements.zip"
                },
                "beamline": { }
            },
            "report": "intensityReport"
        }''')
        d = pkunit.empty_work_dir()
        template_common.copy_lib_files(data, None, d)

    from sirepo import sr_unit
    sr_unit.test_in_request(t)
