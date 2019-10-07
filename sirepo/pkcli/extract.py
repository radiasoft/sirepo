# -*- coding: utf-8 -*-
u"""Operations run inside the report directory to extract data.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjson
from pykern.pkdebug import pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import functools
import sirepo
import sys


#TODO(robnagler) single entry point that takes operation as arg,
# and then passes to functions. Not sure if should be in template
# or here. default_command?
def _cmd(func):
    @functools.wraps(func)
    def w(extract_arg_file):
        f = pkio.py_path(extract_arg_file)
        a = pkjson.load_any(f)
        f.remove()
        sys.stdout.write(
            pkjson.dump_pretty(
                func(a, *_common_args()),
                pretty=False,
            ),
        )
    return w


@_cmd
def background_percent_complete(is_running, data, template, run_dir):
    return template.background_percent_complete(data.report, run_dir, is_running)


@_cmd
def get_simulation_frame(frame_data, data, template, run_dir):
    return template.get_simulation_frame(run_dir, frame_data, data)


@_cmd
def remove_last_frame(ignored, data, template, run_dir):
#TODO(robnagler) make remove_last_frame "inherited"
    if hasattr(template, 'remove_last_frame'):
        template.remove_last_frame(run_dir)


@_cmd
def result(ignored, data, template, run_dir):
#TODO(robnagler) make a single call that does this
    if hasattr(template, 'prepare_output_file'):
        template.prepare_output_file(run_dir, data)
    r, e = simulation_db.read_result(run_dir)
    if e and hasattr(template, 'parse_error_log'):
        r = template.parse_error_log(run_dir)
        if r:
            return (r, None)
    return r, e


def _common_args():
    r = pkio.py_path()
    d = simulation_db.read_json(
        r.join(template_common.INPUT_BASE_NAME)
    )
    return d, sirepo.template.import_module(d), r
