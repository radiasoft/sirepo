# -*- coding: utf-8 -*-
"""Wrapper to run elegant from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import elegant_common
from sirepo.template import template_common
from sirepo.template.elegant import save_report_data, parse_elegant_log, ELEGANT_LOG_FILE
import py.path


def run(cfg_dir):
    """Run elegant in ``cfg_dir``

    The files in ``cfg_dir`` must be configured properly.

    Args:
        cfg_dir (str): directory to run elegant in
    """
    with pkio.save_chdir(cfg_dir):
        _run_elegant(bunch_report=True)
        save_report_data(simulation_db.read_json(template_common.INPUT_BASE_NAME), py.path.local(cfg_dir))


def run_background(cfg_dir):
    """Run elegant as a background task

    Args:
        cfg_dir (str): directory to run elegant in
    """
    with pkio.save_chdir(cfg_dir):
        _run_elegant(with_mpi=True);
        simulation_db.write_result({})


def _run_elegant(bunch_report=False, with_mpi=False):
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    #TODO(pjm): in python3, lattice_file isn't present as a local variable after exec()
    pkio.write_text('elegant.lte', locals()['lattice_file'])
    ele = 'elegant.ele'
    pkio.write_text(ele, locals()['elegant_file'])
    kwargs = {
        'output': ELEGANT_LOG_FILE,
        'env': elegant_common.subprocess_env(),
    }
    try:
        #TODO(robnagler) Need to handle this specially, b/c different binary
        if locals()['execution_mode'] == 'parallel' and with_mpi and mpi.cfg.cores > 1:
            mpi.run_program(['Pelegant', ele], **kwargs)
        else:
            pksubprocess.check_call_with_signals(['elegant', ele], msg=pkdlog, **kwargs)
    except Exception as e:
        # ignore elegant failures - errors will be parsed from the log
        pass
