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


def run(cfg_dir):
    """Run Hellweg in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run hellweg in
    """
    template_common.exec_parameters()
    sim_in = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    r = sim_in.report
    template_common.write_sequential_result(
        template_common.sim_frame_dispatch(
            copy.deepcopy(sim_in.models[r]).pkupdate(
                # show very first frame for source reports
                frameIndex=0,
                frameReport=r.replace("Report", "Animation"),
                run_dir=pkio.py_path(cfg_dir),
                sim_in=sim_in,
                simulationType="hellweg",
            ),
        ),
    )


def run_background(cfg_dir):
    template_common.exec_parameters()
