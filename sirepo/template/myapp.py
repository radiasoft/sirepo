# -*- coding: utf-8 -*-
u"""Myapp execution template.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common

SIM_TYPE = 'myapp'


def fixup_old_data(data):
    pass


def get_data_file(run_dir, model, frame, options=None):
    f = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
    return f.basename, f.read(), 'application/json'


def lib_files(data, source_lib):
    return []


def models_related_to_report(data):
    r = data['report']
    return [
        r,
        'dog',
    ]


def python_source_for_model(data, model):
    return ''


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        '# python code goes here\n'
    )
