# -*- coding: utf-8 -*-
u"""Test statelessCompute API

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import pytest


def test_elegant_get_beam_input_type(fc):
    from pykern import pkunit
    f = None
    r = _do_stateful_compute(fc, 'get_beam_input_type', PKDict(input_file=f))
    pkunit.pkeq(None, f)


def test_invalid_method(fc):
    from pykern import pkunit
    m = '-x23'
    r = _do_stateless_compute(fc, m)
    pkunit.pkre(f'method={m} not a valid python function name or too long', r.error)


def test_madx_calculate_bunch_parameters(fc):
    from pykern import pkunit
    r = _do_stateless_compute(fc, 'calculate_bunch_parameters')
    pkunit.pkok(r.command_beam, 'unexpected response={}', r)


def _do(fc, api, method, data):
    data.method = method
    return fc.sr_post(api, data)


def _do_stateful_compute(fc, method, data):
    t = 'elegant'
    d = fc.sr_sim_data(sim_name='Backtracking', sim_type=t)
    return _do(
        fc,
        'statefulCompute',
        method,
        PKDict(
            simulationId=d.models.simulation.simulationId,
            simulationType=t,
            **data
        ),
    )


def _do_stateless_compute(fc, method, data=None):
    data = data or PKDict()
    t = 'madx'
    d = fc.sr_sim_data(sim_name='FODO PTC', sim_type=t)
    return _do(
        fc,
        'statelessCompute',
        method,
        PKDict(
            bunch=d.models.bunch,
            command_beam=d.models.command_beam,
            simulationId=d.models.simulation.simulationId,
            simulationType=t,
            variables=d.models.rpnVariables,
            **data
        ),
    )
