# -*- coding: utf-8 -*-
"""Wrapper to run JSPEC from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdp, pkdc
from sirepo import simulation_db
from sirepo.template import sdds_util, template_common
import os.path
import re
import sirepo.template.jspec as template


def run(cfg_dir):
    text = _run_jspec(cfg_dir)
    res = {
        #TODO(pjm): x_range is needed for sirepo-plotting.js, need a better valid-data check
        'x_range': [],
        'rate': [],
    }
    for line in text.split("\n"):
        m = re.match(r'^(.*? rate.*?)\:\s+(\S+)\s+(\S+)\s+(\S+)', line)
        if m:
            row = [m.group(1), [m.group(2), m.group(3), m.group(4)]]
            row[0] = re.sub('\(', '[', row[0]);
            row[0] = re.sub('\)', ']', row[0]);
            res['rate'].append(row)
    simulation_db.write_result(res)


def run_background(cfg_dir):
    _run_jspec(cfg_dir)
    simulation_db.write_result({})


def _elegant_to_madx(ring):
    # if the lattice source is an elegant twiss file, convert it to MAD-X format
    if ring['latticeSource'] == 'madx':
        return
    if ring['latticeSource'] == 'elegant':
        elegant_twiss_file = template_common.lib_file_name('ring', 'elegantTwiss', ring['elegantTwiss'])
    else: # elegant-sirepo
        if 'elegantSirepo' not in ring or not ring['elegantSirepo']:
            raise RuntimeError('elegant simulation not selected')
        elegant_twiss_file = template.ELEGANT_TWISS_FILENAME
        if not os.path.exists(elegant_twiss_file):
            raise RuntimeError('elegant twiss output unavailable. Run elegant simulation.')
    sdds_util.twiss_to_madx(elegant_twiss_file, template.JSPEC_TWISS_FILENAME)


def _run_jspec(run_dir):
    with pkio.save_chdir(run_dir):
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        _elegant_to_madx(data['models']['ring'])
        exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
        jspec_filename = template.JSPEC_INPUT_FILENAME
        pkio.write_text(jspec_filename, jspec_file)
        pksubprocess.check_call_with_signals(['jspec', jspec_filename], msg=pkdp, output=template.JSPEC_LOG_FILE)
        return pkio.read_text(template.JSPEC_LOG_FILE)
