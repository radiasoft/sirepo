# -*- coding: utf-8 -*-
"""viz3d execution template.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from sirepo.template import template_common
import sirepo.sim_data


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    v.test_message = "hello world"
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )
