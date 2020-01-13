# -*- coding: utf-8 -*-
u"""IRAD execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from sirepo import simulation_db
from pykern.pkdebug import pkdp

SIM_TYPE = 'irad'

_ROI_FILE_NAME = 'rtstruct-data.json'

_SCHEMA = simulation_db.get_schema(SIM_TYPE)

def get_application_data(data, **kwargs):
    if data['method'] == 'roi_points':
        return _read_roi_file(data['simulationId'])
    assert False, 'no handler for method: {}'.format(data['method'])


def get_data_file(run_dir, model, frame, **kwargs):
    sim_id = kwargs['options'].simulationId
    if frame == 1:
        filename = _sim_file(sim_id, 'ct.zip')
    elif frame == 2:
        filename = _sim_file(sim_id, 'rtdose.zip')
    else:
        assert False, 'invalid frame: {}'.format(frame)
    with open(filename) as f:
        return 'index.json', f.read(), 'application/octet-stream'


def write_parameters(data, run_dir, is_parallel):
    pass


def _read_roi_file(sim_id):
    return simulation_db.read_json(_roi_file(sim_id))


def _roi_file(sim_id):
    return _sim_file(sim_id, _ROI_FILE_NAME)


def _sim_file(sim_id, filename):
    return str(simulation_db.simulation_dir(SIM_TYPE, sim_id).join(filename))
