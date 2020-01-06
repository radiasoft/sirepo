# -*- coding: utf-8 -*-
u"""SRW template fixups

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import math
import sirepo.sim_data
from sirepo.template import srw_common

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals('srw')

def do(template, data):
    _do_beamline(template, data)
    dm = data.models
    data = _do_electron_beam(template, data)
    for c in 'horizontal', 'vertical':
        n = '{}DeflectingParameter'.format(c)
        if n not in dm.undulator:
            u = dm.undulator
            u[n] = template.process_undulator_definition(
                pkcollections.Dict(
                    undulator_definition='B',
                    undulator_parameter=None,
                    amplitude=float(u['{}Amplitude'.format(c)]),
                    undulator_period=float(u.period) / 1000.0
                ),
            ).undulator_parameter
    if 'length' in dm.tabulatedUndulator:
        tabulated_undulator = dm.tabulatedUndulator
        und_length = template.compute_undulator_length(tabulated_undulator)
        if _SIM_DATA.srw_uses_tabulated_zipfile(data) and 'length' in und_length:
            dm.undulator.length = und_length.length
        del dm.tabulatedUndulator['length']
    return data


def _do_beamline(template, data):
    dm = data.models
    for i in dm.beamline:
        t = i.type
        if t == 'crl' and i.get('focalDistance', 0) == 0:
            template.compute_crl_focus(i)
        if t == 'crystal' and i.get('diffractionAngle', 0) == 0:
            allowed_angles = [x[0] for x in _SCHEMA.enum.DiffractionPlaneAngle]
            i.diffractionAngle = _SIM_DATA.srw_find_closest_angle(i.grazingAngle or 0, allowed_angles)
            if i.tvx == '':
                i.tvx = i.tvy = 0
                _SIM_DATA.srw_compute_crystal_grazing_angle(i)
        _SIM_DATA.update_model_defaults(i, t)


def _do_electron_beam(template, data):
    dm = data.models
    if 'beamDefinition' not in dm['electronBeam']:
        srw_common.process_beam_parameters(dm['electronBeam'])
        dm['electronBeamPosition']['drift'] = template.calculate_beam_drift(
            dm['electronBeamPosition'],
            dm['simulation']['sourceType'],
            dm['tabulatedUndulator']['undulatorType'],
            float(dm['undulator']['length']),
            float(dm['undulator']['period']) / 1000.0,
        )
    return data
