# -*- coding: utf-8 -*-
"""Wrapper to run the code from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkinspect
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.template


def run(cfg_dir):
    """Run code in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run code in
    """
    template = sirepo.template.import_module(pkinspect.module_basename(run))
    with pkio.save_chdir(cfg_dir):
        _run_code()
        a = PKDict(
            # see template.warppba.open_data_file (opens last frame)
            frameIndex=None,
            run_dir=pkio.py_path(cfg_dir),
            sim_in=simulation_db.read_json(template_common.INPUT_BASE_NAME),
        )
        a.frameReport = a.sim_in.report
        a.update(a.sim_in.models[a.frameReport])
        if a.frameReport == 'laserPreviewReport':
            res = template.sim_frame_fieldAnimation(a)
        elif a.frameReport == 'beamPreviewReport':
            res = template.sim_frame_beamAnimation(a)
        simulation_db.write_result(res)


def run_background(cfg_dir):
    """Run code in ``cfg_dir`` with mpi

    Args:
        cfg_dir (str): directory to run code in
    """
    with pkio.save_chdir(cfg_dir):
        mpi.run_script(_script())
        simulation_db.write_result({})


def _run_code():
    """Run code program with isolated locals()
    """
    exec(_script(), locals(), locals())
    # advance the window until zmin is >= 0 (avoids mirroring in output)
    doit = True
    total_steps = 0
    while doit:
        step(inc_steps)
        total_steps += inc_steps
        if USE_BEAM:
            doit = total_steps < diag_period
        else:
            doit = w3d.zmmin + top.zgrid < 0

def _script():
    return pkio.read_text(template_common.PARAMETERS_PYTHON_FILE)
