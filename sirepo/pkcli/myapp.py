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
import numpy as np
import random
import sirepo.template.myapp as template

_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)

_MAX_AGE_BY_WEIGHT = [
    [0, 16],
    [20, 13],
    [50, 11],
    [90, 10],
]

def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data['report'] == 'dogReport':
        dog = data.models.dog
        max_age = _max_age(dog.weight)
        x = np.linspace(0, max_age, int(max_age) + 1).tolist()
        plots = [
            _plot(dog, 'height', x),
            _plot(dog, 'weight', x),
        ]
        res = {
            'title': 'Dog Height and Weight Over Time',
            'x_range': [0, max_age],
            'y_label': '',
            'x_label': 'Age (years)',
            'x_points': x,
            'plots': plots,
            'y_range': template_common.compute_plot_color_and_range(plots),
        }
    else:
        raise RuntimeError('unknown report: {}'.format(data['report']))
    simulation_db.write_result(res)


def _max_age(weight):
    prev = None
    for bracket in _MAX_AGE_BY_WEIGHT:
        if weight <= bracket[0]:
            break;
        prev = bracket[1]
    return prev


def _plot(dog, field, x):
    return {
        'name': field,
        'label': _SCHEMA.model.dog[field][0],
        'points': _points(dog[field], x),
    }


def _points(max_value, x):
    return map(lambda v: (random.random() * 0.5) * max_value / 20.0 + max_value * 19.0 / 20.0 * (1.0 - 1.0 / (1.0 + v ** 2)), x)
