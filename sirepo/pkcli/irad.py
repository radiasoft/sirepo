# -*- coding: utf-8 -*-
"""Wrapper to run IRAD from the command line.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.template.irad as template


def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data.report == 'dvhReport':
        _run_dvh(data, cfg_dir)
    elif data.report == 'dicom3DReport':
        template_common.write_sequential_result({
            'simulationId': data.models.simulation.simulationId,
        })
    else:
        assert False, 'unknown report: {}'.format(data.report)


def _run_dvh(data, cfg_dir):
    sim_id = data.models.simulation.simulationId
    filename = template.sim_file(sim_id, 'dvh-data.json')
    template_common.write_sequential_result(simulation_db.read_json(filename))
