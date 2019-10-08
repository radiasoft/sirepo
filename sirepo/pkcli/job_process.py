# -*- coding: utf-8 -*-
u"""Operations run inside the report directory to extract data.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjson
from pykern.pkdebug import pkdp
from sirepo import job
from sirepo import simulation_db
from sirepo.template import template_common
import functools
import sirepo
import sys


def default_command(in_file):
    f = pkio.py_path(in_file)
    a = pkjson.load_any(f)
    f.remove()
    sys.stdout.write(
        pkjson.dump_pretty(
            globals()['_do_' + a.cmd](*_args(a)),
            pretty=False,
        ),
    )


def _do_background_percent_complete(is_running, data, template, run_dir):
    return template.background_percent_complete(data.report, run_dir, is_running)


def _do_get_simulation_frame(msg):
    d = pkio.py_path()
    return template.get_simulation_frame(
        d,
        # parsed frame_id
        msg.data,
        simulation_db.read_json(d.join(template_common.INPUT_BASE_NAME)),
    )


def _do_compute(args):
#TODO(robnagler) make remove_last_frame "inherited"
    write_json()
    d = simulation_db.tmp_dir()
#TODO(robnagler) prepare_simulation runs only in the agent
        cmd, _ = simulation_db.prepare_simulation(data, tmp_dir=d)
        data['simulationStatus'] = {
            'startTime': int(time.time()),
            'state': 'pending',
        }
    if hasattr(t, 'remove_last_frame'):
        t.remove_last_frame(run_dir)

def _do_full_status():
    return report_info on simulation db


def _do_remove_last_frame(ignored, data, template, run_dir):
#TODO(robnagler) make remove_last_frame "inherited"
    if hasattr(template, 'remove_last_frame'):
        template.remove_last_frame(run_dir)


def _do_result(ignored, data, template, run_dir):
#TODO(robnagler) make a single call that does this
    if hasattr(template, 'prepare_output_file'):
        template.prepare_output_file(run_dir, data)
    r, e = simulation_db.read_result(run_dir)
    if e and hasattr(template, 'parse_error_log'):
        r = template.parse_error_log(run_dir)
        if r:
            return (r, None)
    return r, e


def _do_status(args):
    read status file
    return ''

def _args(args):
    r = pkio.py_path()
    d =
    return d, sirepo.template.import_module(d), r
