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

SIM_TYPE = 'irad'

CT_FILE = 'ct.zip'
RTDOSE_FILE = 'rtdose.zip'
RTSTRUCT_FILE = 'rtstruct-data.json'

_SCHEMA = simulation_db.get_schema(SIM_TYPE)
_VTI_FILE = 'index.json'

def get_application_data(data, **kwargs):
    if data['method'] == 'roi_points':
        return _read_roi_file(data['simulationId'])
    assert False, 'no handler for method: {}'.format(data['method'])


def get_data_file(run_dir, model, frame, **kwargs):
    sim_id = simulation_db.read_json(run_dir.join(template_common.OUTPUT_BASE_NAME)).simulationId
    if frame == 1:
        filename = sim_file(sim_id, CT_FILE)
    elif frame == 2:
        filename = sim_file(sim_id, RTDOSE_FILE)
    else:
        assert False, 'invalid frame: {}'.format(frame)
    return PKDict(
        uri=_VTI_FILE,
        filename=pkio.py_path(filename),
    )


def sim_file(sim_id, filename):
    return str(simulation_db.simulation_dir(SIM_TYPE, sim_id).join(filename))


def write_parameters(data, run_dir, is_parallel):
    pass


def _read_roi_file(sim_id):
    return simulation_db.read_json(_roi_file(sim_id))


def _roi_file(sim_id):
    return sim_file(sim_id, RTSTRUCT_FILE)
