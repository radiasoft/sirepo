# -*- coding: utf-8 -*-
"""Wrapper to run elegant from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import elegant_common
from sirepo.template import template_common
from sirepo.template.elegant import save_sequential_report_data, ELEGANT_LOG_FILE


def run(cfg_dir):
    """Run elegant in ``cfg_dir``

    The files in ``cfg_dir`` must be configured properly.

    Args:
        cfg_dir (str): directory to run elegant in
    """
    run_elegant()
    save_sequential_report_data(
        simulation_db.read_json(
            template_common.INPUT_BASE_NAME,
        ),
        pkio.py_path(cfg_dir),
    )


def run_background(cfg_dir):
    """Run elegant as a background task

    Args:
        cfg_dir (str): directory to run elegant in
    """
    run_elegant(with_mpi=True)


def run_elegant(with_mpi=False):
    r = template_common.exec_parameters()
    pkio.write_text("elegant.lte", r.lattice_file)
    ele = "elegant.ele"
    pkio.write_text(ele, r.elegant_file)
    kwargs = {
        "output": ELEGANT_LOG_FILE,
        "env": elegant_common.subprocess_env(),
    }
    # TODO(robnagler) Need to handle this specially, b/c different binary
    if r.execution_mode == "parallel" and with_mpi and mpi.cfg().cores > 1:
        mpi.run_program(["Pelegant", ele], **kwargs)
    else:
        pksubprocess.check_call_with_signals(["elegant", ele], msg=pkdlog, **kwargs)
