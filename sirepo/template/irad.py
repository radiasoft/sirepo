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

_FRAME_FILENAME = PKDict({
    _SCHEMA.constants.dicomFrameId: _SIM_DATA.CT_FILE,
    _SCHEMA.constants.doseFrameId: _SIM_DATA.RTDOSE_FILE,
    _SCHEMA.constants.roiFrameId: _SIM_DATA.RTSTRUCT_FILE,
    _SCHEMA.constants.dose2FrameId: _SIM_DATA.RTDOSE2_FILE,
})


def get_data_file(run_dir, model, frame, **kwargs):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    path = pkio.py_path(_SIM_DATA.lib_file_for_sim(data, _FRAME_FILENAME[frame]))
    return PKDict(filename=path);


def write_parameters(data, run_dir, is_parallel):
    pass
