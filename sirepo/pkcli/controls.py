# -*- coding: utf-8 -*-
"""Wrapper to run controls code from the command line.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.pkcli.madx
import sirepo.template.controls as template


def madx_device_server(sim_id):
    import sirepo.pkcli.madx_device_server

    sirepo.pkcli.madx_device_server.run(sim_id)


def run(cfg_dir):
    cfg_dir = pkio.py_path(cfg_dir)
    _create_particle_file_for_external_lattice(cfg_dir)
    template_common.exec_parameters()
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    res = template.extract_beam_position_report(data, pkio.py_path(cfg_dir))
    if not template.is_viewing_log_file(data):
        res.summaryData = PKDict(
            elementValues=template.read_summary_line(
                cfg_dir,
                simulation_db.get_schema(template.SIM_TYPE).constants.maxBPMPoints,
            )[0],
        )
    template_common.write_sequential_result(res, run_dir=cfg_dir)


def run_background(cfg_dir):
    _create_particle_file_for_external_lattice(pkio.py_path(cfg_dir))
    template_common.exec_parameters()


def _create_particle_file_for_external_lattice(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data.models.controlSettings.operationMode == "madx":
        madx = data.models.externalLattice
        madx.models.command_beam = data.models.command_beam
        madx.models.bunch = data.models.bunch
        madx.models.bunch.matchTwissParameters = "0"
        sirepo.pkcli.madx.create_particle_file(cfg_dir, madx)
