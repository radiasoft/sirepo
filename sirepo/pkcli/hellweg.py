# -*- coding: utf-8 -*-
"""Wrapper to run Hellweg from the command line.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import simulation_db
from sirepo.template import template_common
import copy
import py.path
import rshellweg.solver
import sirepo.template


def run(cfg_dir):
    """Run Hellweg in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run hellweg in
    """
    _run_hellweg(cfg_dir)
    sim_in = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    r = sim_in.report
    template_common.write_sequential_result(
        template_common.sim_frame_dispatch(
            copy.deepcopy(sim_in.models[r]).pkupdate(
                # TODO(e-carlin): Is this right? What should frameIndex be?
                frameIndex=0,
                frameReport=r.replace("Report", "Animation"),
                run_dir=pkio.py_path(cfg_dir),
                sim_in=sim_in,
                simulationType="hellweg",
            ),
        ),
    )


def run_background(cfg_dir):
    _run_hellweg(cfg_dir)


def _run_hellweg(cfg_dir):
    t = sirepo.template.import_module("hellweg")
    r = template_common.exec_parameters()
    pkio.write_text(t.HELLWEG_INPUT_FILE, r.input_file)
    pkio.write_text(t.HELLWEG_INI_FILE, r.ini_file)
    s = rshellweg.solver.BeamSolver(t.HELLWEG_INI_FILE, t.HELLWEG_INPUT_FILE)
    s.solve()
    s.save_output(t.HELLWEG_SUMMARY_FILE)
    s.dump_bin(t.HELLWEG_DUMP_FILE)
