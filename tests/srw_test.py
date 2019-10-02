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
from sirepo import srunit

@srunit.wrap_in_request(sim_types='srw')
def test_model_defaults():
    from pykern import pkconfig
    from pykern.pkcollections import PKDict
    from sirepo.template import template_common
    from sirepo import simulation_db
    import sirepo.sim_data

    s = sirepo.sim_data.get_class('srw')
    res = s.model_defaults('trajectoryReport')
    assert res == PKDict(
        notes='',
        plotAxisY2='None',
        timeMomentEstimation='auto',
        magneticField='2',
        initialTimeMoment=0.0,
        numberOfPoints=10000,
        plotAxisY='X',
        plotAxisX='Z',
        finalTimeMoment=0.0,
    )
    model = PKDict(
        numberOfPoints=10,
        finalTimeMoment=1.0,
    )
    s.update_model_defaults(model, 'trajectoryReport')
    assert model['numberOfPoints'] == 10
    assert model['finalTimeMoment'] == 1.0
    assert model['plotAxisX'] == 'Z'


@srunit.wrap_in_request(sim_types='srw')
def test_prepare_aux_files():
    from sirepo.template import template_common
    from pykern.pkdebug import pkdp
    from pykern import pkcollections
    import sirepo.auth
    import sirepo.auth.guest

    sirepo.auth.login(sirepo.auth.guest)

    # Needed to initialize simulation_db
    data = pkcollections.json_load_any('''{
        "simulationType": "srw",
        "models": {
            "simulation": {
                "sourceType": "t"
            },
            "tabulatedUndulator": {
                "undulatorType": "u_t",
                "magneticFile": "magnetic_measurements.zip"
            },
            "beamline": { }
        },
        "report": "intensityReport"
    }''')
    template_common.copy_lib_files(data, None, pkunit.work_dir())
