# -*- coding: utf-8 -*-
u"""Simple API test for app.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
pytest.importorskip('srwl_bl')

from pykern import pkio
from pykern import pkunit
import json


def test_new(flask_client):
    from pykern.pkdebug import pkdp, pkdpretty
    sim_type = 'srw'
    data = flask_client.sr_post('listSimulations', {'simulationType': sim_type})
    for youngs in data:
        if youngs['name'] == "Young's Double Slit Experiment":
            break
    else:
        raise AssertionError("{}: Young's not found".format(pkdpretty(data)))
    data = flask_client.sr_get(
        'simulationData',
        {
            'simulation_type': sim_type,
            'pretty': '0',
            'simulation_id': youngs['simulationId'],
        },
    )
