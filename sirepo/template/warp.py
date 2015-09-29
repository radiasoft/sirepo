# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkjinja
from . import template_common

#: How long before killing WARP process
MAX_SECONDS = 60 * 60 * 24

def fixup_old_data(data):
    pass

def generate_parameters_file(data, schema):
    v = template_common.flatten_data(data['models'], {})
    v['enablePlasma'] = 1
    return pkjinja.render_resource('warp.py', v)

def prepare_aux_files(wd):
    pass

def run_all_text():
    return ''
