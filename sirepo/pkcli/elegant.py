# -*- coding: utf-8 -*-
"""Wrapper to run elegant from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import simulation_db
from sirepo.template import template_common
from sirepo.template.elegant import extract_report_data, ELEGANT_LOG_FILE
from subprocess import call

_ELEGANT_STDERR_FILE = 'elegant.stderr'


def run(cfg_dir):
    """Run elegant in ``cfg_dir``

    The files in ``cfg_dir`` must be configured properly.

    Args:
        cfg_dir (str): directory to run elegant in
    """
    with pkio.save_chdir(cfg_dir):
        _run_elegant()
        _extract_bunch_report()


def run_background(cfg_dir):
    """Run elegant as a background task

    Args:
        cfg_dir (str): directory to run elegant in
    """
    with pkio.save_chdir(cfg_dir):
        _run_elegant();


def _run_elegant():
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    pkio.write_text('elegant.lte', lattice_file)
    pkio.write_text('elegant.ele', elegant_file)
    with open(ELEGANT_LOG_FILE, 'w') as elegant_stdout:
        with open(_ELEGANT_STDERR_FILE, 'w') as elegant_stderr:
            call(['elegant', 'elegant.ele'], stdout=elegant_stdout, stderr=elegant_stderr)
    # combine stderr with stdout
    with open(ELEGANT_LOG_FILE, 'a') as log_file:
        with open(_ELEGANT_STDERR_FILE, 'r') as f:
            log_file.write(f.read())


def _extract_bunch_report():
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    info = extract_report_data('elegant.bun', data['models'][data['report']], data['models']['bunch']['p_central_mev'], 0)
    simulation_db.write_json(template_common.OUTPUT_BASE_NAME, info)
