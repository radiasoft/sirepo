# -*- coding: utf-8 -*-
u"""Myapp execution template.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import copy


SIM_TYPE = 'myapp'

INPUT_NAME = 'hundli.yml'

OUTPUT_NAME = 'hundli.csv'

_SCHEMA = simulation_db.get_schema(SIM_TYPE)


def fixup_old_data(data):
    for m in _SCHEMA.model:
        if m not in data.models:
            data.models[m] = pkcollections.Dict({})
        template_common.update_model_defaults(data.models[m], m, _SCHEMA)


def get_data_file(run_dir, model, frame, options=None):
    f = run_dir.join(OUTPUT_NAME)
    return f.basename, f.read(), 'text/csv'


def lib_files(data, source_lib):
    return []


def models_related_to_report(data):
    r = data['report']
    return [
        r,
        'dog',
    ]


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    if 'report' in data:
        assert data['report'] == 'heightWeightReport', \
            'unknown report: {}'.format(data['report'])
    v = copy.deepcopy(data['models'], pkcollections.Dict())
    v.input_name = INPUT_NAME
    v.output_name = OUTPUT_NAME
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )
