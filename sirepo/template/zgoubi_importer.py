# -*- coding: utf-8 -*-
u"""zgoubi datafile parser

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import elegant_common, zgoubi_parser
from sirepo.template import template_common
import math
import re

_SIM_TYPE = 'zgoubi'
_SCHEMA = simulation_db.get_schema(_SIM_TYPE)
_IGNORE_FIELDS = ['bunch.coordinates', 'BEND.IL', 'BEND.NCE', 'BEND.NCS', 'MULTIPOL.IL', 'MULTIPOL.NCE', 'MULTIPOL.NCS', 'QUADRUPO.IL', 'QUADRUPO.NCE', 'QUADRUPO.NCS', 'SEXTUPOL.IL', 'SEXTUPOL.NCE', 'SEXTUPOL.NCS']
_DEGREE_TO_RADIAN_FIELDS = ['CHANGREF.ALE']
_MRAD_FIELDS = ['AUTOREF.ALE']
#TODO(pjm): consolidate this with template.zgoubi _MODEL_UNITS, use one definition
_CM_FIELDS = ['l', 'X_E', 'LAM_E', 'X_S', 'LAM_S', 'XCE', 'YCE', 'R_0', 'dY', 'dZ', 'dS', 'YR', 'ZR', 'SR']


def import_file(text):
    data = simulation_db.default_data(_SIM_TYPE)
    #TODO(pjm): need a common way to clean-up/uniquify a simulation name from imported text
    title, elements, unhandled_elements = zgoubi_parser.parse_file(text, 1)
    title = re.sub(r'\s+', ' ', title)
    title = re.sub(r'^\s+|\s+$', '', title)
    data['models']['simulation']['name'] = title if title else 'zgoubi'
    if len(unhandled_elements):
        data['models']['simulation']['warnings'] = 'Unsupported Zgoubi elements: {}'.format(', '.join(unhandled_elements))
    info = _validate_and_dedup_elements(data, elements)
    _validate_element_names(data, info)
    elegant_common.sort_elements_and_beamlines(data)
    return data


def _validate_and_dedup_elements(data, elements):
    beamline = []
    current_id = 1
    data['models']['beamlines'] = [
        {
            'name': 'BL1',
            'id': current_id,
            'items': beamline,
        },
    ]
    data['models']['simulation']['activeBeamlineId'] = current_id
    data['models']['simulation']['visualizationBeamlineId'] = current_id
    info = {
        'ids': [],
        'names': [],
        'elements': [],
    }
    for el in elements:
        _validate_model(el)
        if 'name' in el:
            name = el['name']
            #TODO(pjm): don't de-duplicate certain types
            if el['type'] != 'MARKER':
                del el['name']
            if el not in info['elements']:
                current_id += 1
                info['ids'].append(current_id)
                info['names'].append(name)
                info['elements'].append(el)
            beamline.append(info['ids'][info['elements'].index(el)])
        else:
            if el['type'] in data['models']:
                pkdlog('replacing existing {} model', el['type'])
            template_common.update_model_defaults(el, el['type'], _SCHEMA)
            data['models'][el['type']] = el
    return info


def _validate_element_names(data, info):
    names = {}
    for idx in range(len(info['ids'])):
        el = info['elements'][idx]
        template_common.update_model_defaults(el, el['type'], _SCHEMA)
        el['_id'] = info['ids'][idx]
        name = info['names'][idx]
        name = re.sub(r'\\', '_', name)
        name = re.sub(r'\d+$', '', name)
        name = re.sub(r'(\_|\#)$', '', name)
        if not name:
            name = el['type'][:2]
        if name in names:
            count = 2
            while True:
                name2 = '{}{}'.format(name, count)
                if name2 not in names:
                    name = name2
                    break
                count += 1
        el['name'] = name
        names[name] = True
        data['models']['elements'].append(el)


def _validate_field(model, field, model_info):
    if field in ('_id', 'type'):
        return
    assert field in model_info, \
        'unknown model field: {}.{}, value: {}'.format(model['type'], field, model[field])
    field_info = model_info[field]
    field_type = field_info[1]
    if field_type == 'Float':
        model[field] = float(model[field])
        mf = '{}.{}'.format(model['type'], field)
        if mf in _DEGREE_TO_RADIAN_FIELDS:
            model[field] *= math.pi / 180.0
        elif mf in _MRAD_FIELDS:
            model[field] /= 1000.0
        elif field in _CM_FIELDS and model['type'] != 'CAVITE':
            model[field] *= 0.01
    elif field == 'XPAS':
        #TODO(pjm): need special handling, may be in #00|00|00 format
        if not re.search(r'\#', model[field]):
            v = float(model[field])
            if v > 1e10:
                # old step size format
                m = re.search(r'^0*(\d+)\.0*(\d+)', model[field])
                assert m, 'XPAS failed to parse step size: {}'.format(model[field])
                model[field] = '#{}|{}|{}'.format(m.group(2), m.group(1), m.group(2))
            else:
                model[field] = str(v * 0.01)
    elif field_type in _SCHEMA['enum']:
        for v in _SCHEMA['enum'][field_type]:
            if v[0] == model[field]:
                return
        pkdlog('invalid enum value, {}.{} {}: {}', model['type'], field, field_type, model[field])
        model[field] = field_info[3]


def _validate_model(model):
    assert model['type'] in _SCHEMA['model'], \
        'element type missing from schema: {}'.format(model['type'])
    model_info = _SCHEMA['model'][model['type']]
    if 'name' in model_info and 'name' not in model:
        model['name'] = ''
    for f in model:
        if f == 'label2':
            continue
        if '{}.{}'.format(model['type'], f) in _IGNORE_FIELDS:
            continue
        _validate_field(model, f, model_info)
