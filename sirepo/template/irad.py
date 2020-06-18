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
    _SCHEMA.constants.dicomFrameId: CT_FILE,
    _SCHEMA.constants.doseFrameId: RTDOSE_FILE,
    _SCHEMA.constants.roiFrameId: RTSTRUCT_FILE,
    _SCHEMA.constants.dose2FrameId: 'rtdose2.zip',
})

def get_data_file(run_dir, model, frame, **kwargs):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    path = lib_file_for_sim(data, _FRAME_FILENAME[frame])
    if not path.exists() and frame == _SCHEMA.constants.dose2FrameId:
        # no alternate dose exists, use main dose instead
        path = lib_file_for_sim(data, RTDOSE_FILE)
    return PKDict(filename=path);


def lib_file_for_sim(data, filename):
    return pkio.py_path('{}-{}'.format(
        data.models.simulation.libFilePrefix,
        filename,
    ))


def write_parameters(data, run_dir, is_parallel):
    pass
