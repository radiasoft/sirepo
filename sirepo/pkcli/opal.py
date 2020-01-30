# -*- coding: utf-8 -*-
"""Wrapper to run OPAL from the command line.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import re
import sirepo.template.opal as template


def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        if _run_opal():
            data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
            if data['report'] == 'twissReport':
                template.save_report_data(data, py.path.local(cfg_dir))
        else:
            simulation_db.write_result({
                'error': _parse_opal_errors()
            })


def run_background(cfg_dir):
    res = {}
    with pkio.save_chdir(cfg_dir):
        if not _run_opal():
            res['error'] = _parse_opal_errors()
    simulation_db.write_result(res)


def _parse_opal_errors():
    res = ''
    with pkio.open_text(template.OPAL_OUTPUT_FILE) as f:
        prev_line = ''
        for line in f:
            if re.search(r'^Error>', line):
                line = re.sub(r'^Error>\s*\**\s*', '', line.rstrip())
                if re.search(r'1DPROFILE1-DEFAULT', line):
                    continue
                if line and line != prev_line:
                    res += line + '\n'
                prev_line = line
    if res:
        return res
    return 'An unknown error occurred'


def _run_opal():
    try:
        pksubprocess.check_call_with_signals(
            ['opal', template.OPAL_INPUT_FILE],
            output=template.OPAL_OUTPUT_FILE,
            msg=pkdlog,
        )
        return True
    except Exception as e:
        return False
