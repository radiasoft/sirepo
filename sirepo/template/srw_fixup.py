# -*- coding: utf-8 -*-
"""SRW template fixups

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals("srw")


def do(template, data, qcall):
    _do_beamline(template, data)
    return data


def _do_beamline(template, data):
    dm = data.models
    for i in dm.beamline:
        t = i.type
        _SIM_DATA.update_model_defaults(i, t)
        if t == "crystal":
            template._compute_crystal_orientation(i)
        if t == "grating":
            template._compute_PGM_value(i)
