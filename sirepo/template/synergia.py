# -*- coding: utf-8 -*-
u"""JSPEC execution template.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdc, pkdp
from sirepo.template import template_common

SIM_TYPE = 'synergia'

def fixup_old_data(data):
    pass


def lib_files(data, source_lib):
    return []


def models_related_to_report(data):
    r = data['report']
    return [
        'bunch',
        r,
    ]


def python_source_for_model(data, model):
    return ''


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        '# python code goes here\n'
    )
