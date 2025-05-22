# -*- coding: utf-8 -*-
"""Simulation schema

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import util
import re
import sirepo.resource


# keep sirepo-components.js "safePath" in sync with these values
_NAME_ILLEGALS = r'\/|&:+?\'*"<>'
_NAME_ILLEGALS_RE = re.compile(r"[" + re.escape(_NAME_ILLEGALS) + "]")
_NAME_ILLEGAL_PERIOD = re.compile(r"^\.|\.$")


def get_enums(schema, name):
    enum_dict = PKDict()
    for info in schema.enum[name]:
        enum_name = info[0]
        enum_dict[enum_name] = enum_name
    return enum_dict


def parse_folder(folder):
    """Verifies syntax of folder is correct

    Args:
        folder (str): what to validate
    Returns:
        str: cleaned up folder name
    """
    if folder is None or len(folder) == 0:
        raise util.Error("blank folder", "blank folder={}", folder)
    res = []
    for f in folder.split("/"):
        if len(f):
            res.append(parse_name(f))
    return "/" + "/".join(res)


def parse_name(name):
    """Verifies syntax of simulation is correct

    Args:
        folder (str): what to validate
    Returns:
        str: cleaned up folder name
    """
    n = name
    if n is None:
        n = ""
    else:
        # ignore leading and trailing spaces
        n = name.strip()
    # don't raise an error on invalid name - the client is not looking for them
    # instead, remove illegal characters and throw an error if nothing is left
    n = re.sub(_NAME_ILLEGALS_RE, "", n)
    n = re.sub(_NAME_ILLEGAL_PERIOD, "", n)
    if len(n) == 0:
        raise util.Error("blank name", "blank name={}", name)
    return n


def validate_fields(data, schema):
    """Validate the values of the fields in model data

    Validations performed:
        enums (see _validate_enum)
        numeric values (see _validate_number)

    Args:
        data (PKDict): model data
        schema (PKDict): schema which data inmplements
    """
    sch_models = schema.model
    sch_enums = schema.enum
    for model_name in data.models:
        if model_name not in sch_models:
            continue
        sch_model = sch_models[model_name]
        model_data = data.models[model_name]
        for field_name in model_data:
            if field_name not in sch_model:
                continue
            val = model_data[field_name]
            if val == "":
                continue
            sch_field_info = sch_model[field_name]
            _validate_enum(val, sch_field_info, sch_enums)
            _validate_number(val, sch_field_info)


def validate_name(data, data_files, max_copies):
    """Validate and if necessary uniquify name

    Args:
        data (dict): what to validate
        data_files(list): simulation files already in the folder
    """
    s = data.models.simulation
    sim_id = s.simulationId
    n = s.name
    f = s.folder
    starts_with = PKDict()
    for d in data_files:
        n2 = d.models.simulation.name
        if n2.startswith(n) and d.models.simulation.simulationId != sim_id:
            starts_with[n2] = d.models.simulation.simulationId
    i = 2
    n2 = data.models.simulation.name
    while n2 in starts_with:
        n2 = "{} {}".format(data.models.simulation.name, i)
        i += 1
    assert i - 1 <= max_copies, util.err(
        n, "Too many copies: {} > {}", i - 1, max_copies
    )
    data.models.simulation.name = n2


def validate(schema):
    """Validate the schema

    Validations performed:
        Values of default data (if any)
        Existence of dynamic modules
        Enums keyed by string value
        Model names containing special characters
        Method name for API calls with them are valid python function names and not too long

    Args:
        schema (PKDict): app schema
    """
    sch_models = schema.model
    sch_enums = schema.enum
    for name in sch_enums:
        for values in sch_enums[name]:
            if not isinstance(values[0], pkconfig.STRING_TYPES):
                raise AssertionError(
                    util.err(
                        name,
                        "enum values must be keyed by a string value: {}",
                        type(values[0]),
                    )
                )
    for model_name in sch_models:
        _validate_model_name(model_name)
        sch_model = sch_models[model_name]
        for field_name in sch_model:
            _validate_job_run_mode(field_name, schema)
            sch_field_info = sch_model[field_name]
            if len(sch_field_info) <= 2:
                continue
            field_default = sch_field_info[2]
            if field_default == "" or field_default is None:
                continue
            _validate_enum(field_default, sch_field_info, sch_enums)
            _validate_number(field_default, sch_field_info)
    for t in schema.dynamicModules:
        for src in schema.dynamicModules[t]:
            sirepo.resource.file_path(src)
    _validate_strings(schema.strings)


def _validate_enum(val, sch_field_info, sch_enums):
    """Ensure the value of an enum field is one listed in the schema

    Args:
        val: enum value to validate
        sch_field_info ([str]): field info array from schema
        sch_enums (PKDict): enum section of the schema
    """
    type = sch_field_info[1]
    if not type in sch_enums:
        return
    if str(val) not in map(lambda enum: str(enum[0]), sch_enums[type]):
        raise AssertionError(
            util.err(sch_enums, "enum {} value {} not in schema", type, val)
        )


def _validate_job_run_mode(field_name, schema):
    if field_name != "jobRunMode":
        return
    from sirepo import pkcli

    t = schema.simulationType
    m = pkcli.import_module(t)
    if hasattr(m, "run_background"):
        raise AssertionError(
            f"simulation_type={t} cannot have"
            + " pkcli.run_background because it supports slurm. Slurm only"
            + " supports running a code through `python parameters.py` ",
        )


def _validate_model_name(model_name):
    """Ensure model name contain no special characters

    Args:
        model_name (str): name to validate
    """

    if not util.is_python_identifier(model_name):
        raise AssertionError(
            util.err(model_name, "model name must be a Python identifier")
        )


def _validate_number(val, sch_field_info):
    """Ensure the value of a numeric field falls within the supplied limits (if any)

    Args:
        val: numeric value to validate
        sch_field_info ([str]): field info array from schema
    """
    if len(sch_field_info) <= 4:
        return
    try:
        fv = float(val)
        fmin = float(sch_field_info[4])
    # Currently the values in enum arrays at the indices below are sometimes
    # used for other purposes, so we return rather than fail for non-numeric values.
    # Also ignore object-valued fields
    except (ValueError, TypeError):
        return
    if fv < fmin:
        raise AssertionError(
            util.err(sch_field_info, "numeric value {} out of range", val)
        )
    if len(sch_field_info) > 5:
        try:
            fmax = float(sch_field_info[5])
        except ValueError:
            return
        if fv > fmax:
            raise AssertionError(
                util.err(sch_field_info, "numeric value {} out of range", val)
            )


def _validate_strings(strings):
    c = 3
    d = strings.simulationDataType[:c]
    p = strings.simulationDataTypePlural[:c]
    assert d == p, (
        f"strings.simulationDataType={d} does not appear to be the same as"
        + f"strings.simulationDataTypePlural={p}"
    )
