# -*- coding: utf-8 -*-
u"""elegant lattice parser

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import elegant_common
from sirepo.template import elegant_lattice_parser
import json
import math
import ntpath
import os
import py.path
import re
import subprocess


_IGNORE_FIELD = ['rootname', 'search_path', 'semaphore_file']

_ANGLE_FIELDS = ['angle', 'kick', 'hkick']
_BEND_TYPES = ['BUMPER', 'CSBEND', 'CSRCSBEND', 'FMULT', 'HKICK', 'KICKER', 'KPOLY', 'KSBEND', 'KQUSE', 'MBUMPER', 'MULT', 'NIBEND', 'NISEPT', 'RBEN', 'SBEN', 'TUBEND']
_DRIFT_TYPES = ['CSRDRIFT', 'DRIF', 'EDRIFT', 'EMATRIX', 'LSCDRIFT']
_IGNORE_LENGTH_TYPES = ['ILMATRIX', 'STRAY', 'SCRIPT']
_LENGTH_FIELDS = ['l', 'xmax', 'length']

_SCHEMA = simulation_db.get_schema('elegant')


def _init_types():
    res = {}
    for name in _SCHEMA['model']:
        if name == name.upper():
            res[name] = True
    return res


_ELEGANT_TYPES = _init_types()


def build_variable_dependency(value, variables, depends):
    for v in str(value).split(' '):
        if v in variables:
            if v not in depends:
                build_variable_dependency(variables[v], variables, depends)
                depends.append(v)
    return depends


def import_file(text, data=None):
    models = elegant_lattice_parser.parse_file(text, max_id(data) if data else 0)
    name_to_id, default_beamline_id = _create_name_map(models)
    if 'default_beamline_name' in models and models['default_beamline_name'] in name_to_id:
        default_beamline_id = name_to_id[models['default_beamline_name']]
    element_names = {}
    rpn_cache = {}

    for el in models['elements']:
        el['type'] = _validate_type(el, element_names)
        element_names[el['name'].upper()] = el
        validate_fields(el, rpn_cache, models['rpnVariables'])

    for bl in models['beamlines']:
        bl['items'] = _validate_beamline(bl, name_to_id, element_names)

    if len(models['elements']) == 0 or len(models['beamlines']) == 0:
        raise IOError('no beamline elements found in file')
    _calculate_beamline_metrics(models, rpn_cache)

    if not data:
        data = simulation_db.default_data(elegant_common.SIM_TYPE)
    data['models']['elements'] = sorted(models['elements'], key=lambda el: el['type'])
    data['models']['elements'] = sorted(models['elements'], key=lambda el: (el['type'], el['name'].lower()))
    data['models']['beamlines'] = sorted(models['beamlines'], key=lambda b: b['name'].lower())
    data['models']['rpnVariables'] = models['rpnVariables']

    if default_beamline_id:
        data['models']['simulation']['activeBeamlineId'] = default_beamline_id
        data['models']['simulation']['visualizationBeamlineId'] = default_beamline_id

    return data


def is_rpn_value(value):
    if (value):
        if re.search(r'^\s*(\-|\+)?(\d+|(\d*(\.\d*)))([eE][+-]?\d+)?\s*$', str(value)):
            return False
        return True
    return False


def max_id(data):
    max_id = 1
    for model_type in ['elements', 'beamlines', 'commands']:
        if model_type not in data['models']:
            continue
        for m in data['models'][model_type]:
            id = m['_id'] if '_id' in m else m['id']
            if id > max_id:
                max_id = id
    return max_id


def parse_rpn_value(value, variable_list):
    variables = {x['name']: x['value'] for x in variable_list}
    depends = build_variable_dependency(value, variables, [])
    #TODO(robnagler) scan variable values for strings. Need to be parsable
    var_list = ' '.join(map(lambda x: '{} sto {}'.format(variables[x], x), depends))
    #TODO(pjm): security - need to scrub field value
    #     execn  send top of string stack to UNIX and put result on numerical stack
    #     execs     send top of string stack to UNIX and put output on string stack
    # csh                       start and enter C shell subprocess
    # cshs                       send top of string stack to C shell
    # gets                       get string from input file
    # seems like this would be bad, because you could construct a string that could be executed
    # mudf    make user defined function from string stack (name commands mudf)
    # open                       open input/output file
    # puts                       put string to file
    # sleep                       sleep for number of seconds
    # @                       push command input file
    pkdc('rpn variables={} expr="{}"', var_list, value)
    out = elegant_common.subprocess_output(['rpnl', '{} {}'.format(var_list, value)])
    if out is None:
        return None, 'invalid'
    if len(out):
        return float(out.strip()), None
    return None, 'empty'


def validate_fields(el, rpn_cache, rpn_variables):
    for field in el.copy():
        _validate_field(el, field, rpn_cache, rpn_variables)
    model_name = _model_name_for_data(el)
    for field in _SCHEMA['model'][model_name]:
        if field not in el:
            el[field] = _SCHEMA['model'][model_name][field][2]


def _model_name_for_data(model):
    return 'command_{}'.format(model['_type']) if '_type' in model else model['type']


def _calculate_beamline_metrics(models, rpn_cache):
    metrics = {}
    for el in models['elements']:
        metrics[el['_id']] = {
            'length': _element_length(el, rpn_cache),
            'angle': _element_angle(el, rpn_cache),
            'count': _element_count(el),
        }
    for bl in models['beamlines']:
        bl['length'] = 0
        bl['angle'] = 0
        bl['distance'] = 0
        bl['count'] = 0
        bl['end_x'] = 0
        bl['end_y'] = 0
        #TODO(pjm): convert key not found to IOError
        for id in bl['items']:
            if id < 0:
                id = -id
            el_metrics = metrics[id]

            if 'distance' in el_metrics:
                angle = bl['angle'] + el_metrics['end_angle']
                bl['end_x'] += math.cos(angle) * el_metrics['distance']
                bl['end_y'] += math.sin(angle) * el_metrics['distance']
            elif el_metrics['angle']:
                radius = el_metrics['length'] / 2
                bl['end_x'] += math.cos(bl['angle']) * radius
                bl['end_y'] += math.sin(bl['angle']) * radius

            bl['length'] += el_metrics['length']
            bl['angle'] += el_metrics['angle']
            bl['count'] += el_metrics['count']

            if 'distance' in el_metrics:
                pass
            elif el_metrics['angle']:
                radius = el_metrics['length'] / 2
                bl['end_x'] += math.cos(bl['angle']) * radius
                bl['end_y'] += math.sin(bl['angle']) * radius
            else:
                bl['end_x'] += math.cos(bl['angle']) * el_metrics['length']
                bl['end_y'] += math.sin(bl['angle']) * el_metrics['length']
        bl['distance'] = math.sqrt(bl['end_x'] ** 2 + bl['end_y'] ** 2)
        bl['end_angle'] = math.atan2(bl['end_y'], bl['end_x'])
        metrics[bl['id']] = bl

    for bl in models['beamlines']:
        for f in ['end_x', 'end_y', 'end_angle']:
            del bl[f]


def _create_name_map(models):
    name_to_id = {}
    last_beamline_id = None

    for bl in models['beamlines']:
        name_to_id[bl['name'].upper()] = bl['id']
        last_beamline_id = bl['id']

    for el in models['elements']:
        name_to_id[el['name'].upper()] = el['_id']

    return name_to_id, last_beamline_id


def _element_angle(el, rpn_cache):
    if el['type'] in _BEND_TYPES:
        for f in _ANGLE_FIELDS:
            if f in el:
                return _rpn_value(el[f], rpn_cache)
    return 0


def _element_count(el):
    if el['type'] in _DRIFT_TYPES:
        return 0
    return 1


def _element_length(el, rpn_cache):
    if el['type'] in _IGNORE_LENGTH_TYPES:
        return 0
    for f in _LENGTH_FIELDS:
        if f in el:
            return _rpn_value(el[f], rpn_cache)
    return 0


def _field_type_for_field(el, field):
    if re.search(r'\[\d+\]$', field):
        field = re.sub(r'\[\d+\]$', '', field)
    field_type = None
    model_name = _model_name_for_data(el)
    for f in _SCHEMA['model'][model_name]:
        if f == field:
            field_type = _SCHEMA['model'][model_name][f][1]
            break
    if not field_type:
        if not field in _IGNORE_FIELD:
            pkdlog('{}: unknown field type for {}', field, model_name)
        del el[field]
    return field_type


def _rpn_value(v, rpn_cache):
    if v in rpn_cache:
        return float(rpn_cache[v])
    return float(v)


def _validate_beamline(bl, name_to_id, element_names):
    items = []
    for name in bl['items']:
        is_reversed = False
        if re.search(r'^-', name):
            is_reversed = True
            name = re.sub(r'^-', '', name)
        if name.upper() not in name_to_id:
            raise IOError('{}: unknown beamline item name'.format(name))
        id = name_to_id[name.upper()]
        if name.upper() in element_names:
            items.append(id)
        else:
            items.append(-id if is_reversed else id)
    return items


def _validate_enum(el, field, field_type):
    search = el[field].lower()
    exact_match = ''
    close_match = ''
    for v in _SCHEMA['enum'][field_type]:
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


def _validate_field(el, field, rpn_cache, rpn_variables):
    if field in ['_id', '_type']:
        return
    if '_type' not in el and field == 'type':
        return
    field_type = _field_type_for_field(el, field)
    if field_type == 'OutputFile':
        el[field] = '1'
    elif field_type == 'InputFile':
        el[field] = ntpath.basename(el[field])
    elif field_type == "InputFileXY":
        _validate_input_file(el, field)
    elif (field_type == 'RPNValue' or field_type == 'RPNBoolean') and is_rpn_value(el[field]):
        _validate_rpn_field(el, field, rpn_cache, rpn_variables)
    elif field_type == 'StringArray':
        _validate_string_array_field(el, field)
    elif field_type in _SCHEMA['enum']:
        #TODO(pjm): special case for DistributionType - not really an enum
        # but a collection of enum values
        if field_type != 'DistributionType':
            _validate_enum(el, field, field_type)


def _validate_input_file(el, field):
    # <filename>=<x>+<y>
    fullname= ntpath.basename(el[field])
    m = re.search('^(.*?)\=(.*?)\+(.*)$', fullname)
    if m:
        el[field] = m.group(1)
        el[field + 'X'] = m.group(2)
        el[field + 'Y'] = m.group(3)
    else:
        el[field] = fullname


def _validate_rpn_field(el, field, rpn_cache, rpn_variables):
    if '_type' in el:
        return
    if '_type' in el:
        m = re.search('\((.*?)\)$', el[field])
        if m:
            el[field] = m.group(1)
        m = re.search('\{\s*rpnl\s+(.*)\}$', el[field])
        if m:
            el[field] = m.group(1)
    value, error = parse_rpn_value(el[field], rpn_variables)
    if error:
        raise IOError('invalid rpn: "{}"'.format(el[field]))
    rpn_cache[el[field]] = value


def _validate_string_array_field(el, field):
    m = re.search('(.*?)\[(\d+)\]$', field)
    if not m:
        return
    value = el[field]
    del el[field]
    field = m.group(1)
    index = int(m.group(2))
    if not field in el:
        model_name = _model_name_for_data(el)
        el[field] = _SCHEMA['model'][model_name][field][2]
    value_array = re.split('\s*,\s*', el[field])
    m = re.search('^(\d+)\*(.*)$', value)
    if m:
        count = int(m.group(1))
        val = m.group(2)
        for i in range(count):
            value_array[index + i] = val
    else:
        values = re.split('\s*,\s*', value)
        for v in values:
            value_array[index] = v
            index += 1
    el[field] = ', '.join(value_array)


def _validate_type(el, element_names):
    type = el['type'].upper()
    match = None
    for el_type in _ELEGANT_TYPES:
        if type.startswith(el_type) or el_type.startswith(type):
            if match:
                raise IOError('{}: type name matches multiple element types'.format(type))
            match = el_type
        if not el_type:
            raise IOError('{}: unknown element type'.format(type))
    if not match:
        # type may refer to another element
        if el['type'] in element_names:
            el_copy = element_names[el['type'].upper()]
            for field in el_copy.copy():
                if field not in el:
                    el[field] = el_copy[field]
            match = el_copy['type']
        else:
            raise IOError('{}: element not found'.format(type))
    return match
