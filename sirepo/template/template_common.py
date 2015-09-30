# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import re


def flatten_data(d, res, prefix=''):
    """Takes a nested dictionary and converts it to a single level dictionary with flattened keys."""
    for k in d:
        v = d[k]
        if isinstance(v, dict):
            flatten_data(v, res, prefix + k + '_')
        elif isinstance(v, list):
            pass
        else:
            res[prefix + k] = v
    return res


def parse_enums(enum_schema):
    """Returns a list of enum values, keyed by enum name."""
    res = {}
    for k in enum_schema:
        res[k] = {}
        for v in enum_schema[k]:
            res[k][v[0]] = True
    return res


def validate_model(model_data, model_schema, enum_info):
    """Ensure the value is valid for the field type. Scales values as needed."""
    for k in model_schema:
        label = model_schema[k][0]
        field_type = model_schema[k][1]
        value = model_data[k]
        if field_type in enum_info:
            if not enum_info[field_type][str(value)]:
                raise Exception('invalid enum value: {}'.format(value))
        elif field_type == 'Float':
            if not value:
                value = 0
            v = float(value)
            if re.search('\[m(m|rad)\]', label):
                v /= 1000
            elif re.search('\[nm\]', label):
                v /= 1e09
            elif re.search('\[ps]', label):
                v /= 1e12
            #TODO(pjm): need to handle unicode in label better (mu)
            elif re.search('\[\xb5m\]', label):
                v /= 1e6
            model_data[k] = v
        elif field_type == 'Integer':
            if not value:
                value = 0
            model_data[k] = int(value)
        elif field_type == 'BeamList' or field_type == 'File' or field_type == 'String':
            model_data[k] = _escape(value)
        else:
            raise Exception('unknown field type: {}'.format(field_type))

def _escape(v):
    return re.sub("['()\.]", '', str(v))
