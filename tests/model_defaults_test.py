# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.srw.py`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from sirepo import srunit

@srunit.wrap_in_request()
def test_srw_model_defaults():
    from pykern import pkresource
    from pykern import pkunit
    from pykern import pkconfig
    from pykern.pkcollections import PKDict
    from sirepo.template import template_common
    from sirepo import simulation_db
    import sirepo.sim_data

    sirepo.sim_data.get_class('srw').resource_dir().join('predefined.json')
    s = sirepo.sim_data.get_class('srw')
    res = s.model_defaults('trajectoryReport')
    assert res == PKDict(
        notes='',
        plotAxisY2='None',
        timeMomentEstimation='auto',
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
