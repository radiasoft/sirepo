# -*- coding: utf-8 -*-
"""CLI for genesis

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkdebug import pkdp, pkdlog
from pykern import pksubprocess
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.template.genesis


def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data.report == "maginPlotReport":
        template_common.write_sequential_result(
            sirepo.template.genesis.plot_magin(data.models.io.maginfile)
        )


def run_background(cfg_dir):
    # TODO(e-carlin): use the mpi version of genesis?
    run_genesis(cfg_dir)


def run_genesis(cfg_dir):
    pksubprocess.check_call_with_signals(
        ["genesis", sirepo.template.genesis.GENESIS_INPUT_FILE],
        output=sirepo.template.genesis.GENESIS_OUTPUT_FILE,
        msg=pkdlog,
    )
    # GENESIS does not return a bad exit code, so need to look for a failure
    if not sirepo.template.genesis.genesis_success_exit(pkio.py_path(cfg_dir)):
        raise RuntimeError("GENESIS execution failed")
