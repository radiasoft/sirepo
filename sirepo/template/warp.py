# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkjinja
from . import template_common

#: How long before killing WARP process
MAX_SECONDS = 60 * 60


def fixup_old_data(data):
    if 'laserPreviewReport' not in data['models']:
        data['models']['laserPreviewReport'] = {}


def generate_parameters_file(data, schema):
    _validate_data(data, schema)
    v = template_common.flatten_data(data['models'], {})
    if 'report' in data and data['report'] == 'laserPreviewReport':
        v['enablePlasma'] = 0
    else:
        v['enablePlasma'] = 1
    return pkjinja.render_resource('warp.py', v)


def prepare_aux_files(wd):
    pass


def run_all_text():
    return ''


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.parse_enums(schema['enum'])
    for k in data['models']:
        if k in schema['model']:
            template_common.validate_model(data['models'][k], schema['model'][k], enum_info)
