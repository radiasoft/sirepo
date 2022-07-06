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
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.template


def run(cfg_dir):
    """Run code in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run code in
    """
    template = sirepo.template.import_module(pkinspect.module_basename(run))
    _run_code()
    a = PKDict(
        # see template.warppba.open_data_file (opens last frame)
        frameIndex=None,
        run_dir=pkio.py_path(cfg_dir),
        sim_in=simulation_db.read_json(template_common.INPUT_BASE_NAME),
    )
    a.frameReport = a.sim_in.report
    a.update(a.sim_in.models[a.frameReport])
    if a.frameReport == "laserPreviewReport":
        res = template.sim_frame_fieldAnimation(a)
    elif a.frameReport == "beamPreviewReport":
        res = template.sim_frame_beamAnimation(a)
    else:
        raise AssertionError("invalid report: {}".format(a.frameReport))
    template_common.write_sequential_result(res)


def _run_code():
    """Run code program with isolated locals()"""
    r = template_common.exec_parameters()
    # advance the window until zmin is >= 0 (avoids mirroring in output)
    i = r.inc_steps
    if r.USE_BEAM:
        for x in range(0, r.diag_period, i):
            r.step(i)
    else:
        while r.w3d.zmmin + r.top.zgrid < 0:
            r.step(i)
