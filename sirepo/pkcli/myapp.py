# -*- coding: utf-8 -*-
"""Wrapper to run myapp from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.template.myapp as template

_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)

def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    dog = data.models.dog
    report = data['models'][data['report']]
    res = {
        'title': 'Dog Height/Weight',
        'x_range': [0, 1],
        'y_label': 'y label',
        'x_label': 'x label',
        'x_points': [0, 1],
        'points': [
            [dog.height, dog.height],
            [dog.weight, dog.weight],
        ],
        'y_range': [0, max(dog.height, dog.weight)],
        'y1_title': _SCHEMA['model']['dog']['height'][0],
        'y2_title': _SCHEMA['model']['dog']['weight'][0],
    }
    simulation_db.write_result(res)
