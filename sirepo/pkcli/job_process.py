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
    """Reads `in_file` passes to `msg.job_process_cmd`

    Must be called in run_dir

    Writes its output on stdout.

    Args:
        in_file (str): json parsed to msg
    Returns:
        str: json output of command, e.g. status msg
    """
    f = pkio.py_path(in_file)
    msg = pkjson.load_any(f)
    f.remove()
    return pkjson.dump_pretty(
        globals()['_do_' + msg.job_process_cmd](
            msg,
            sirepo.template.import_module(msg.sim_type),
        ),
        pretty=False,
    )


def _do_background_percent_complete(msg, template):
    return template.background_percent_complete(
        msg.data.report,
        msg.run_dir,
        msg.is_running,
    )


def _do_get_simulation_frame(msg, template):
    return template.get_simulation_frame(
        msg.run_dir,
        # parsed frame_id
        msg.data,
        simulation_db.read_json(msg.run_dir.join(template_common.INPUT_BASE_NAME)),
    )


def _do_compute(msg):
    with pkio.save_chdir('/'):
        pkio.unchecked_remove(msg.run_dir)
    cmd, _ = simulation_db.prepare_simulation(msg.data, run_dir=msg.run_dir)
    msg.data['simulationStatus'] = {
        'startTime': int(time.time()),
        'state': 'pending',
    }
    str(run_dir.join(template_common.RUN_LOG)),
    if hasattr(t, 'remove_last_frame'):
        t.remove_last_frame(run_dir)


def _do_compute_status(msg, template):
    return PKDict(
        compute_hash=template_common.report_parameters_hash(
            simulation_db.json_filename(
                template_common.INPUT_BASE_NAME,
                msg.run_dir,
            ),
        status=simulation_db.read_status(msg.run_dir),a
    )


def _do_result(msg, template):
    if hasattr(template, 'prepare_output_file'):
        template.prepare_output_file(msg.run_dir, msg.data)
    r, e = simulation_db.read_result(msg.run_dir)
    if not e:
        return PKDict(result=r)
    l = None
    if hasattr(template, 'parse_error_log'):
        l = template.parse_error_log(msg.run_dir)
    return PKDict(error=e, error_log=l)


def _args(args):
    r = pkio.py_path()
    d =
    return d,
