# -*- coding: utf-8 -*-
"""Impact-T execution template.
:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo.template import code_variable
from sirepo.template import template_common
import sirepo.template.lattice
import sirepo.sim_data


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_S_ELEMENTS = set(
    [
        "OFFSET_BEAM",
        "WRITE_BEAM",
        "WRITE_BEAM_FOR_RESTART",
        "CHANGE_TIMESTEP",
        "ROTATIONALLY_SYMMETRIC_TO_3D",
        "WAKEFIELD",
        "STOP",
        "SPACECHARGE",
        "WRITE_SLICE_INFO",
    ]
)


def code_var(variables):
    return code_variable.CodeVar(variables, code_variable.PurePythonEval())


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            frameCount=0,
            percentComplete=0,
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
    )


def prepare_for_client(data, qcall, **kwargs):
    code_var(data.models.rpnVariables).compute_cache(data, SCHEMA)
    return data


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )
    if is_parallel:
        return template_common.get_exec_parameters_cmd(False)
    return None


def _format_field(field, field_type, value):
    if field == "_super":
        return ""
    if field == "l":
        field = "L"
    return f'{field}="{value}",\n'


def _generate_lattice(util, beamline_id, result):
    beamline = util.id_map[abs(beamline_id)]
    for idx, item_id in enumerate(beamline["items"]):
        item = util.id_map[abs(item_id)]
        if "type" in item:
            el = f'type="{item.type.lower()}",\n'
            if item.type in _S_ELEMENTS:
                el += f"s={beamline.positions[idx].elemedge},\n"
            else:
                el += f"zedge={beamline.positions[idx].elemedge},\n"
            for f, d in SCHEMA.model[item.type].items():
                el += _format_field(f, d[1], item[f])
            result.append(el)
        else:
            _generate_lattice(util, item.id, result)
    return result


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    util = sirepo.template.lattice.LatticeUtil(data, SCHEMA)
    v.lattice = _generate_lattice(util, util.select_beamline().id, [])
    return res + template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )
