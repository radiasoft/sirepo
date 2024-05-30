# -*- coding: utf-8 -*-
"""Impact-T execution template.
:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from sirepo.template import code_variable
from sirepo.template import template_common
import sirepo.sim_data


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def code_var(variables):
    return code_variable.CodeVar(variables, code_variable.PurePythonEval())


def prepare_for_client(data, qcall, **kwargs):
    code_var(data.models.rpnVariables).compute_cache(data, SCHEMA)
    return data


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    return res + template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )
