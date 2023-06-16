# -*- coding: utf-8 -*-
"""CLI for genesis

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkdebug import pkdp, pkdlog
from sirepo.template import template_common
import sirepo.template.genesis


def run_background(cfg_dir):
    # TODO(e-carlin): use the mpi version of genesis?
    run_genesis(cfg_dir)


def run_genesis(cfg_dir):
    template_common.exec_parameters()
    # GENESIS does not return a bad exit code, so need to look for a failure
    if not sirepo.template.genesis.genesis_success_exit(pkio.py_path(cfg_dir)):
        raise RuntimeError("GENESIS execution failed")
