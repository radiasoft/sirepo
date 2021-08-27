# -*- coding: utf-8 -*-
u"""Raydata execution template.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkcollections import PKDict
from sirepo.template import template_common
import sirepo.sim_data


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

_OUTPUT_FILE = 'out.ipynb'


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(percentComplete=0, frameCount=0)
    return PKDict(percentComplete=100, frameCount=1)


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
