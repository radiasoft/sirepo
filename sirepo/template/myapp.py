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
from sirepo.template import template_common

SIM_TYPE = 'myapp'

def copy_related_files(data, source_path, target_path):
    pass


def fixup_old_data(data):
    pass


def lib_files(data, source_lib):
    return []


def models_related_to_report(data):
    r = data['report']
    return [
        r,
        'dog',
    ]


def new_simulation(data, new_simulation_data):
    pass


def prepare_aux_files(run_dir, data):
    pass


def prepare_for_client(data):
    return data


def prepare_for_save(data):
    return data


def python_source_for_model(data, model):
    return ''


def resource_files():
    return []


def write_parameters(data, schema, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        '# python code goes here\n'
    )
