# -*- coding: utf-8 -*-
"""Wrapper to run JSPEC from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdp, pkdc
from sirepo import simulation_db
from sirepo.template import template_common
import re
import sirepo.template.jspec as template


def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        _run_jspec()
        res = {
            'rate': [],
        }
        text = pkio.read_text(template.JSPEC_LOG_FILE)
        for line in text.split("\n"):
            m = re.match(r'^(.*? rate.*?)\:\s+(\S+)\s+(\S+)\s+(\S+)', line)
            if m:
                res['rate'].append([m.group(1), [m.group(2), m.group(3), m.group(4)]])
    simulation_db.write_result(res)


def run_background(cfg_dir):
    run(cfg_dir)
    simulation_db.write_result({})


def _run_jspec():
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    jspec_filename = 'jspec.in'
    pkio.write_text(jspec_filename, jspec_file)
    kwargs = {
        'output': template.JSPEC_LOG_FILE,
    }
    pksubprocess.check_call_with_signals(['jspec', jspec_filename], msg=pkdp, **kwargs)
