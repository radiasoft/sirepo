# -*- coding: utf-8 -*-
"""elegant lattice parser

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import elegant_common
from sirepo.template import elegant_lattice_parser
from sirepo.template import lattice
import math
import ntpath
import operator
import re
import sirepo.sim_data
import subprocess


_IGNORE_FIELD = [
    "mpi_io_write_buffer_size",
    "rootname",
    "search_path",
    "semaphore_file",
]

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals("elegant")

_ELEGANT_TYPE_RE = re.compile(r"^[A-Z]+$")

_ELEGANT_TYPES = set(n for n in SCHEMA.model if _ELEGANT_TYPE_RE.search(n))


def elegant_code_var(variables):
    _PI = 4 * math.atan(1)

    class _P(code_variable.PurePythonEval):
        _OPS = PKDict(
            {
                "<": operator.lt,
                ">": operator.gt,
                "beta.p": lambda a: a / (math.sqrt((1 + (a * a)))),
                "dacos": lambda a: math.acos(a) * 180 / _PI,
                "dasin": lambda a: math.asin(a) * 180 / _PI,
                "datan": lambda a: math.atan(a) * 180 / _PI,
                "dcos": lambda a: math.cos(a * _PI / 180),
                "dsin": lambda a: math.sin(a * _PI / 180),
                "dtan": lambda a: math.tan(a * _PI / 180),
                "gamma.beta": lambda a: 1 / math.sqrt(1 - (a * a)),
                "gamma.p": lambda a: math.sqrt(1 + (a * a)),
                # TODO(e-carlin): Should not need lambda.
                # https://bugs.python.org/issue29299
                "ln": lambda a: math.log(a),
                "mod": operator.mod,
                "mult": operator.mul,
                "p.beta": lambda a: a / math.sqrt(1 - (a * a)),
                "p.gamma": lambda a: math.sqrt((a * a) - 1),
                "sqr": lambda a: a * a,
                **code_variable.PurePythonEval._OPS,
            }
        )

        def eval_var(self, expr, depends, variables):
            if re.match(r"^\{.+\}$", expr):
                # It is a shell command
                return expr, None
            return super().eval_var(expr, depends, variables)

    return code_variable.CodeVar(
        variables,
        _P(
            constants=PKDict(
                c_gs=2.99792458e10,
                c_mks=2.99792458e8,
                e_cgs=4.80325e-10,
                e_mks=1.60217733e-19,
                hbar_MeVs=6.582173e-22,
                hbar_mks=1.0545887e-34,
                kb_cgs=1.380658e-16,
                kb_mks=1.380658e-23,
                me_cgs=9.1093897e-28,
                me_mks=9.1093897e-31,
                mev=0.51099906,
                mp_mks=1.6726485e-27,
                pi=_PI,
                re_cgs=2.81794092e-13,
                re_mks=2.81794092e-15,
            ),
        ),
    )


def import_file(text, data=None, update_filenames=True):
    if not data:
        data = simulation_db.default_data(elegant_common.SIM_TYPE)
    models = elegant_lattice_parser.parse_file(
        text,
        data.models.rpnVariables,
        lattice.LatticeUtil.max_id(data),
    )
    name_to_id, default_beamline_id = _create_name_map(models)
    if (
        "default_beamline_name" in models
        and models["default_beamline_name"] in name_to_id
    ):
        default_beamline_id = name_to_id[models["default_beamline_name"]]
    element_names = PKDict()
    rpn_cache = PKDict()
    code_var = elegant_code_var(models.rpnVariables)

    for el in models["elements"]:
        el["type"] = _validate_type(el, element_names)
        element_names[el["name"].upper()] = el
        validate_fields(el, rpn_cache, code_var, update_filenames)

    for bl in models["beamlines"]:
        bl["items"] = _validate_beamline(bl, name_to_id, element_names)

    if len(models["elements"]) == 0 or len(models["beamlines"]) == 0:
        raise IOError("no beamline elements found in file")

    data["models"]["elements"] = models["elements"]
    data["models"]["beamlines"] = models["beamlines"]
    data["models"]["rpnVariables"] = models["rpnVariables"]
    lattice.LatticeUtil(data, SCHEMA).sort_elements_and_beamlines()

    if default_beamline_id:
        data["models"]["simulation"]["activeBeamlineId"] = default_beamline_id
        data["models"]["simulation"]["visualizationBeamlineId"] = default_beamline_id
    return data


def validate_fields(el, rpn_cache, code_var=None, update_filenames=True):
    if code_var is None:
        code_var = elegant_code_var([])
    for field in el.copy():
        _validate_field(el, field, rpn_cache, code_var, update_filenames)
    model_name = lattice.LatticeUtil.model_name_for_data(el)
    for field in SCHEMA["model"][model_name]:
        if field not in el:
            el[field] = SCHEMA["model"][model_name][field][2]


def _create_name_map(models):
    name_to_id = PKDict()
    last_beamline_id = None

    for bl in models["beamlines"]:
        name_to_id[bl["name"].upper()] = bl["id"]
        last_beamline_id = bl["id"]

    for el in models["elements"]:
        name_to_id[el["name"].upper()] = el["_id"]

    return name_to_id, last_beamline_id


def _field_type_for_field(el, field):
    if re.search(r"\[\d+\]$", field):
        field = re.sub(r"\[\d+\]$", "", field)
    field_type = None
    model_name = lattice.LatticeUtil.model_name_for_data(el)
    for f in SCHEMA["model"][model_name]:
        if f == field:
            field_type = SCHEMA["model"][model_name][f][1]
            break
    if not field_type:
        if not field in _IGNORE_FIELD:
            pkdlog("{}: unknown field type for {}", field, model_name)
        del el[field]
    return field_type


def _strip_file_prefix(value, model, field):
    return re.sub(r"^{}-{}\.".format(model, field), "", value)


def _validate_beamline(bl, name_to_id, element_names):
    items = []
    for name in bl["items"]:
        is_reversed = False
        if re.search(r"^-", name):
            is_reversed = True
            name = re.sub(r"^-", "", name)
        if name.upper() not in name_to_id:
            raise IOError("{}: unknown beamline item name".format(name))
        id = name_to_id[name.upper()]
        if name.upper() in element_names:
            items.append(id)
        else:
            items.append(-id if is_reversed else id)
    return items


def _validate_enum(el, field, field_type):
    search = el[field].lower()
    exact_match = ""
    close_match = ""
    for v in SCHEMA["enum"][field_type]:
        if v[0] == search:
            exact_match = v[0]
            break
        if search.startswith(v[0]) or v[0].startswith(search):
            close_match = v[0]
    if exact_match:
        el[field] = exact_match
    elif close_match:
        el[field] = close_match
    else:
        raise IOError('{} unknown value: "{}"'.format(field, search))


def _validate_field(el, field, rpn_cache, code_var, update_filenames):
    if field in ["_id", "_type"]:
        return
    if "_type" not in el and field == "type":
        return
    field_type = _field_type_for_field(el, field)
    if not field_type:
        return
    if update_filenames:
        if field_type == "OutputFile":
            el[field] = "1"
        elif field_type == "InputFile":
            el[field] = ntpath.basename(el[field])
    if field_type == "InputFileXY":
        _validate_input_file(el, field)
    elif (
        field_type == "RPNValue" or field_type == "RPNBoolean"
    ) and code_var.is_var_value(el[field]):
        _validate_rpn_field(el, field, rpn_cache, code_var)
    elif field_type.endswith("StringArray"):
        _validate_string_array_field(el, field)
    elif field_type in SCHEMA["enum"]:
        _validate_enum(el, field, field_type)
    elif "type" in el and el["type"] == "SCRIPT" and field == "command":
        _validate_script(el)
    if not update_filenames:
        return
    # Input files may have been from a sirepo export. Strip the sirepo file prefix if present.
    if field_type.startswith("InputFile"):
        el[field] = _strip_file_prefix(
            el[field], lattice.LatticeUtil.model_name_for_data(el), field
        )
    elif field_type == "BeamInputFile":
        el[field] = ntpath.basename(el[field])
        el[field] = _strip_file_prefix(el[field], "bunchFile", "sourceFile")


def _validate_input_file(el, field):
    # <filename>=<x>+<y>
    fullname = ntpath.basename(el[field])
    m = re.search(r"^(.*?)\=(.*?)\+(.*)$", fullname)
    if m:
        el[field] = m.group(1)
        el[field + "X"] = m.group(2)
        el[field + "Y"] = m.group(3)
    else:
        el[field] = fullname


def _validate_rpn_field(el, field, rpn_cache, code_var):
    if "_type" in el:
        # command model
        m = re.search(r"\((.*?)\)$", el[field])
        if m:
            el[field] = m.group(1)
        m = re.search(r"\{\s*rpnl\s+(.*)\}$", el[field])
        if m:
            el[field] = m.group(1)
        return
    el[field] = re.sub(r"\s+", " ", el[field]).strip()
    value, error = code_var.eval_var(el[field])
    if error:
        raise IOError(f'invalid rpn="{el[field]}" error="{error}"')
    rpn_cache[el[field]] = value


def _validate_script(el):
    # ex, command: 'sddscombine %i beam1.sdds -merge %o'
    v = el["command"]
    if v:
        m = re.search(r"(\w+)\b", v, re.IGNORECASE)
        if m:
            executable = m.group(1)
            try:
                import distutils.spawn

                if not distutils.spawn.find_executable(executable):
                    el["commandFile"] = executable
            except Exception as e:
                pass
        m = re.search(r"\b(\w+\.sdds)\b", v, re.IGNORECASE)
        if m:
            el["commandInputFile"] = m.group(1)


def _validate_string_array_field(el, field):
    m = re.search(r"(.*?)\[(\d+)\]$", field)
    if not m:
        return
    value = el[field]
    del el[field]
    field = m.group(1)
    index = int(m.group(2))
    if not field in el:
        model_name = lattice.LatticeUtil.model_name_for_data(el)
        el[field] = SCHEMA["model"][model_name][field][2]
    value_array = re.split(r"\s*,\s*", el[field])
    m = re.search(r"^(\d+)\*(.*)$", value)
    if m:
        count = int(m.group(1))
        val = m.group(2)
        for i in range(count):
            value_array[index + i] = val
    else:
        values = re.split(r"\s*,\s*", value)
        for v in values:
            value_array[index] = v
            index += 1
    el[field] = ", ".join(value_array)


def _validate_type(el, element_names):
    type = el["type"].upper()
    match = None
    for el_type in _ELEGANT_TYPES:
        if type.startswith(el_type) or el_type.startswith(type):
            if match:
                raise IOError(
                    "{}: type name matches multiple element types".format(type)
                )
            match = el_type
        if not el_type:
            raise IOError("{}: unknown element type".format(type))
    if not match:
        # type may refer to another element
        if el["type"] in element_names:
            el_copy = element_names[el["type"].upper()]
            for field in el_copy.copy():
                if field not in el:
                    el[field] = el_copy[field]
            match = el_copy["type"]
        else:
            raise IOError("{}: element not found".format(type))
    return match
