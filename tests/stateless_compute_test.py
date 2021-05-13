# -*- coding: utf-8 -*-
u"""Test statelessCompute API

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import pytest

def test_madx_calculate_bunch_parameters(fc):
    from pykern import pkunit
    r = _do(fc, 'calculate_bunch_parameters')
    pkunit.pkok(r.command_beam, 'unexpected response={}', r)


def test_uknown_method(fc):
    from pykern import pkunit
    m = 'uknown'
    r = _do(fc, m)
    pkunit.pkre(f'method={m} not defined in schema', r.error)


def _do(fc, method):
    t = 'madx'
    d = fc.sr_sim_data(sim_name='FODO PTC', sim_type=t)
    return fc.sr_post(
        'statelessCompute',
        PKDict(
            bunch=d.models.bunch,
            command_beam=d.models.command_beam,
            method=method,
            simulationId=d.models.simulation.simulationId,
            simulationType=t,
            variables=d.models.rpnVariables,
        ),
    )
