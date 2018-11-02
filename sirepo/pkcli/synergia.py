# -*- coding: utf-8 -*-
"""Wrapper to run synergia from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import re
import sirepo.template.synergia as template

_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)


def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    report = data['report']
    if 'bunchReport' in report or report == 'twissReport' or report == 'twissReport2':
        try:
            with pkio.save_chdir(cfg_dir):
                exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
            template.save_report_data(data, py.path.local(cfg_dir))
        except Exception as e:
            res = template.parse_error_log(py.path.local(cfg_dir)) or {
                'error': str(e),
            }
            simulation_db.write_result(res)
    else:
        raise RuntimeError('unknown report: {}'.format(report))


def run_background(cfg_dir):
    res = {}
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    distribution = data['models']['bunch']['distribution']
    run_with_mpi = distribution == 'lattice' or distribution == 'file'
    try:
        with pkio.save_chdir(cfg_dir):
            if run_with_mpi:
                mpi.run_script(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE))
            else:
                #TODO(pjm): MPI doesn't work with rsbeams distributions yet
                exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    except Exception as e:
        res = {
            'error': str(e),
        }
    if run_with_mpi and 'error' in res:
        text = pkio.read_text('mpi_run.out')
        m = re.search(r'^Traceback .*?^\w*Error: (.*?)\n\n', text, re.MULTILINE|re.DOTALL)
        if m:
            res['error'] = m.group(1)
            # remove output file - write_result() will not overwrite an existing error output
            pkio.unchecked_remove(simulation_db.json_filename(template_common.OUTPUT_BASE_NAME))
    simulation_db.write_result(res)
