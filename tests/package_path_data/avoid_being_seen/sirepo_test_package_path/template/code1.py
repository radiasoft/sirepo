# -*- coding: utf-8 -*-
u"""code1 execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdc, pkdp
from sirepo.template import template_common
import sirepo.sim_data


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    if 'report' in data and data.report != 'spiceReport':
        raise AssertionError(f'unknown report={data.report}')
    return template_common.render_jinja(
        SIM_TYPE,
        data.models,
        template_common.PARAMETERS_PYTHON_FILE,
    )
