# -*- coding: utf-8 -*-
u"""Raydata execution template.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from sirepo.template import template_common
import databroker
import sirepo.sim_data


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

_ANALYSIS_METADATA = (
    'analysis',
    'auto_pipeline',
    'detectors',
    'number of images',
)

# TODO(e-carlin): from user
_BROKER_NAME = 'chx'

# TODO(e-carlin): from user
_SCAN_UID = 'bdcce1f3-7317-4775-bc26-ece8f0612758'

_OUTPUT_FILE = 'out.ipynb'

_GENERAL_METADATA = (
    'beamline_id',
    'cycle',
    'data path',
    'owner',
    'time',
    'uid',
)

_PLAN_METADATA = (
    'plan_args',
    'plan_name',
    'plan_type',
    'scan_id',
    'sequence id',
)


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(percentComplete=0, frameCount=0)
    return PKDict(percentComplete=100, frameCount=1)


def stateless_compute_analysis_metadata(data):
    return PKDict(data=_metadata(_ANALYSIS_METADATA))


def stateless_compute_general_metadata(data):
    return PKDict(data=_metadata(_GENERAL_METADATA))


def stateless_compute_plan_metadata(data):
    return PKDict(data=_metadata(_PLAN_METADATA))


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    return template_common.render_jinja(
        SIM_TYPE,
        PKDict(
            input_name=data.models.analysisAnimation.notebook,
            output_name=_OUTPUT_FILE,
        ),
    )


def _metadata(type):
    res = PKDict()
    for k in type:
        res[
            ' '.join(k.split('_'))
        ] = databroker.catalog[_BROKER_NAME][_SCAN_UID].metadata['start'][k]
    return res
