# -*- coding: utf-8 -*-
u"""Simulation schema

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import util
import re


def get_enums(schema, name):
    enum_dict = pkcollections.Dict()
    for info in schema.enum[name]:
        enum_name = info[0]
        enum_dict[enum_name] = enum_name
    return enum_dict


def validate_fields(data, schema):
    """Validate the values of the fields in model data

    Validations performed:
        enums (see _validate_enum)
        numeric values (see _validate_number)
        notifications
        cookie definitions (see _validate_cookie_def)

    Args:
        data (pkcollections.Dict): model data
        schema (pkcollections.Dict): schema which data inmplements
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
            if val == '':
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
    starts_with = pkcollections.Dict()
    for d in data_files:
        n2 = d.models.simulation.name
        if n2.startswith(n) and d.models.simulation.simulationId != sim_id:
            starts_with[n2] = d.models.simulation.simulationId
    i = 2
    n2 = data.models.simulation.name
    while n2 in starts_with:
        n2 = '{} {}'.format(data.models.simulation.name, i)
        i += 1
    assert i - 1 <= max_copies, util.err(n, 'Too many copies: {} > {}', i - 1, max_copies)
    data.models.simulation.name = n2


def validate(schema):
    """Validate the schema

    Validations performed:
        Values of default data (if any)
        Existence of dynamic modules
        Enums keyed by string value

    Args:
        schema (pkcollections.Dict): app schema
    """
    sch_models = schema.model
    sch_enums = schema.enum
    sch_ntfy = schema.notifications
    sch_cookies = schema.cookies
    for name in sch_enums:
        for values in sch_enums[name]:
            if not isinstance(values[0], pkconfig.STRING_TYPES):
                raise AssertionError(util.err(name, 'enum values must be keyed by a string value: {}', type(values[0])))
    for model_name in sch_models:
        sch_model = sch_models[model_name]
        for field_name in sch_model:
            sch_field_info = sch_model[field_name]
            if len(sch_field_info) <= 2:
                continue
            field_default = sch_field_info[2]
            if field_default == '' or field_default is None:
                continue
            _validate_enum(field_default, sch_field_info, sch_enums)
            _validate_number(field_default, sch_field_info)
    for n in sch_ntfy:
        if 'cookie' not in sch_ntfy[n] or sch_ntfy[n].cookie not in sch_cookies:
            raise AssertionError(util.err(sch_ntfy[n], 'notification must reference a cookie in the schema'))
    for sc in sch_cookies:
        _validate_cookie_def(sch_cookies[sc])
    for type in schema.dynamicModules:
        for src in schema.dynamicModules[type]:
            pkresource.filename(src[1:])


def _validate_cookie_def(c_def):
    """Validate the cookie definitions in the schema

    Validations performed:
        cannot contain delimiters we use on the client side
        values must match the valType if provided
        timeout must be numeric if provided

    Args:
        data (pkcollections.Dict): cookie definition object from the schema
    """
    c_delims = '|:;='
    c_delim_re = re.compile('[{}]'.format(c_delims))
    if c_delim_re.search(str(c_def.name) + str(c_def.value)):
        raise AssertionError(util.err(c_def, 'cookie name/value cannot include delimiters {}', c_delims))
    if 'valType' in c_def:
        if c_def.valType == 'b':
            pkconfig.parse_bool(c_def.value)
        if c_def.valType == 'n':
            float(c_def.value)
    if 'timeout' in c_def:
        float(c_def.timeout)


def _validate_enum(val, sch_field_info, sch_enums):
    """Ensure the value of an enum field is one listed in the schema

    Args:
        val: enum value to validate
        sch_field_info ([str]): field info array from schema
        sch_enums (pkcollections.Dict): enum section of the schema
    """
    type = sch_field_info[1]
    if not type in sch_enums:
        return
    if str(val) not in map(lambda enum: str(enum[0]), sch_enums[type]):
        raise AssertionError(util.err(sch_enums, 'enum {} value {} not in schema', type, val))


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
    # used for other purposes, so we return rather than fail for non-numeric values
    except ValueError:
        return
    if fv < fmin:
        raise AssertionError(util.err(sch_field_info, 'numeric value {} out of range', val))
    if len(sch_field_info) > 5:
        try:
            fmax = float(sch_field_info[5])
        except ValueError:
            return
        if fv > fmax:
            raise AssertionError(util.err(sch_field_info, 'numeric value {} out of range', val))
