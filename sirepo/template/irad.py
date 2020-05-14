# -*- coding: utf-8 -*-
u"""IRAD execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

CT_FILE = 'ct.zip'
RTDOSE_FILE = 'rtdose.zip'
RTSTRUCT_FILE = 'rtstruct-data.json'

_FRAME_FILENAME = PKDict({
    _SCHEMA.constants.dicomFrame: CT_FILE,
    _SCHEMA.constants.doseFrame: RTDOSE_FILE,
    _SCHEMA.constants.roiFrame: RTSTRUCT_FILE,
})


def get_data_file(run_dir, model, frame, **kwargs):
    sim_id = simulation_db.read_json(run_dir.join(template_common.OUTPUT_BASE_NAME)).simulationId
    return PKDict(
        filename=pkio.py_path(sim_file(sim_id, _FRAME_FILENAME[frame])),
    )


def sim_file(sim_id, filename):
    return str(simulation_db.simulation_dir(SIM_TYPE, sim_id).join(filename))


def write_parameters(data, run_dir, is_parallel):
    pass
