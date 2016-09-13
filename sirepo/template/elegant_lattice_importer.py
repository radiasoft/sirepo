# -*- coding: utf-8 -*-
u"""elegant lattice parser.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import json
import math
import ntpath
import os
import py.path
import re
import sirepo.template.elegant

from pykern import pkresource
from pykern.pkdebug import pkdc, pkdp
from sirepo.template import elegant_lattice_parser

_ANGLE_FIELDS = ['angle', 'kick', 'hkick']
_BEND_TYPES = ['BUMPER', 'CSBEND', 'CSRCSBEND', 'FMULT', 'HKICK', 'KICKER', 'KPOLY', 'KSBEND', 'KQUSE', 'MBUMPER', 'MULT', 'NIBEND', 'NISEPT', 'RBEN', 'SBEN', 'TUBEND']
_DRIFT_TYPES = ['CSRDRIFT', 'DRIF', 'EDRIFT', 'EMATRIX', 'LSCDRIFT']
_IGNORE_LENGTH_TYPES = ['ILMATRIX', 'STRAY', 'SCRIPT']
_LENGTH_FIELDS = ['l', 'xmax', 'length']
_STATIC_FOLDER = py.path.local(pkresource.filename('static'))

with open(str(_STATIC_FOLDER.join('json/elegant-default.json'))) as f:
    _DEFAULTS = json.load(f)

with open(str(_STATIC_FOLDER.join('json/elegant-schema.json'))) as f:
    _SCHEMA = json.load(f)

def _init_types():
    res = {}
    for name in _SCHEMA['model']:
        if name == name.upper():
            res[name] = True
    return res


_ELEGANT_TYPES = _init_types()


def import_file(text):
    models = elegant_lattice_parser.parse_file(text)
    name_to_id, default_beamline_id = _create_name_map(models)
    if 'default_beamline_name' in models and models['default_beamline_name'] in name_to_id:
        default_beamline_id = name_to_id[models['default_beamline_name']]
    element_names = {}
    rpn_cache = {}

    for el in models['elements']:
        el['type'] = _validate_type(el, element_names)
        element_names[el['name'].upper()] = el
        for field in el.copy():
            _validate_field(el, field, rpn_cache, models['rpnVariables'])
        for field in _SCHEMA['model'][el['type']]:
            if field not in el:
                el[field] = _SCHEMA['model'][el['type']][field][2]

    for bl in models['beamlines']:
        bl['items'] = _validate_beamline(bl, name_to_id, element_names)

    if len(models['elements']) == 0 or len(models['beamlines']) == 0:
        raise IOError('no beamline elements found in file')
    _calculate_beamline_metrics(models, rpn_cache)

    data = _DEFAULTS.copy()
    data['models']['elements'] = sorted(models['elements'], key=lambda el: el['type'])
    data['models']['elements'] = sorted(models['elements'], key=lambda el: (el['type'], el['name'].lower()))
    data['models']['beamlines'] = sorted(models['beamlines'], key=lambda b: b['name'].lower())
    data['models']['rpnVariables'] = models['rpnVariables']

    if default_beamline_id:
        data['models']['simulation']['activeBeamlineId'] = default_beamline_id
        data['models']['simulation']['visualizationBeamlineId'] = default_beamline_id

    return data


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


def _validate_field(el, field, rpn_cache, rpn_variables):
    if field in ['_id', 'type']:
        return
    field_type = None
    for f in _SCHEMA['model'][el['type']]:
        if f == field:
            field_type = _SCHEMA['model'][el['type']][f][1]
    if not field_type:
        pkdp('{}: unkown field type for {}', field, el['type'])
        del el[field]
    else:
        if field_type == 'OutputFile':
            el[field] = '{}.{}.sdds'.format(el['name'], field)
        elif field_type == 'InputFile':
            el[field] = ntpath.basename(el[field])
        elif field_type == "InputFileXY":
            # <filename>=<x>+<y>
            fullname= ntpath.basename(el[field])
            m = re.search('^(.*?)\=(.*?)\+(.*)$', fullname)
            if m:
                el[field] = m.group(1)
                el[field + 'X'] = m.group(2)
                el[field + 'Y'] = m.group(3)
            else:
                el[field] = fullname
        elif (field_type == 'RPNValue' or field_type == 'RPNBoolean') and sirepo.template.elegant.is_rpn_value(el[field]):
            value, error = sirepo.template.elegant.parse_rpn_value(el[field], rpn_variables)
            if error:
                raise IOError('invalid rpn: "{}"'.format(el[field]))
            rpn_cache[el[field]] = value
        elif field_type in _SCHEMA['enum']:
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
                raise IOError('unknown value: "{}"'.format(search))


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
