# -*- coding: utf-8 -*-
"""Wrapper to run tmap8 from the command line.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdp, pkdc, pkdlog
import sirepo.mpi
import sirepo.template.tmap8


def run_background(cfg_dir):
    cmd = [
        "tmap8",
        # setting uncertainty on a value may leave unused vars
        "--allow-unused",
        "-i",
        (
            sirepo.template.tmap8.MC_MAIN_FILE
            if pkio.py_path(sirepo.template.tmap8.MC_MAIN_FILE).exists()
            else sirepo.template.tmap8.TMAP8_INPUT_FILE
        ),
    ]
    if sirepo.mpi.cfg().cores > 1:
        sirepo.mpi.run_program(cmd)
    else:
        pksubprocess.check_call_with_signals(cmd, msg=pkdlog)
