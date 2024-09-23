# -*- coding: utf-8 -*-
"""Wrapper to run MAD-X from the command line.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
import glob
import os
import re
import sirepo.template.madx as template


def run(cfg_dir):
    _run_simulation(cfg_dir)
    template.save_sequential_report_data(
        simulation_db.read_json(template_common.INPUT_BASE_NAME),
        pkio.py_path(cfg_dir),
    )


def run_background(cfg_dir):
    _run_simulation(cfg_dir)


def create_particle_file(cfg_dir, data):
    twiss = PKDict()
    b = data.models.bunch
    if b.matchTwissParameters == "1" and b.beamDefinition != "file":
        report = data.report
        # run twiss report and copy results into beam
        data.models.simulation.activeBeamlineId = (
            data.models.simulation.visualizationBeamlineId
        )
        data.report = "twissReport"
        template.write_parameters(data, cfg_dir, False, "matched-twiss.madx")
        _run_madx("matched-twiss.madx")
        twiss = template.extract_parameter_report(data, cfg_dir).initialTwissParameters
        b.update(twiss)
        # restore the original report and generate new source with the updated beam values
        data.report = report
        if data.report == "animation":
            template.write_parameters(data, pkio.py_path(cfg_dir), False)
    template.generate_ptc_particles_file(cfg_dir, data, twiss)


def _need_particle_file(data):
    if "bunchReport" in data.report or (
        data.report == "animation"
        and LatticeUtil.find_first_command(data, template.PTC_LAYOUT_COMMAND)
    ):
        return True
    return False


def _run_madx(filename=template.MADX_INPUT_FILE):
    pksubprocess.check_call_with_signals(
        ["madx", filename],
        msg=pkdlog,
        output=template.MADX_LOG_FILE,
    )
    # fixup madx munged file names
    for f in glob.glob("*.tfsone"):
        n = re.sub(r"tfsone$", "tfs", f)
        os.rename(f, n)


def _run_simulation(cfg_dir):
    cfg_dir = pkio.py_path(cfg_dir)
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if _need_particle_file(data):
        create_particle_file(cfg_dir, data)
    if cfg_dir.join(template.MADX_INPUT_FILE).exists():
        _run_madx()
