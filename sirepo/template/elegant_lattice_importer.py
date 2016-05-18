# -*- coding: utf-8 -*-
u"""elegant lattice parser.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import json
import py.path
import re
import subprocess

from pykern import pkresource
from pykern.pkdebug import pkdc, pkdp
from sirepo.template import elegant_lattice_parser

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

    for el in models['elements']:
        el['type'] = _validate_type(el)
        for field in el:
            _validate_field(el, field)
        for field in _SCHEMA['model'][el['type']]:
            if field not in el:
                el[field] = _SCHEMA['model'][el['type']][field][2]

    for bl in models['beamlines']:
        bl['items'] = _validate_beamline(bl, name_to_id)

    data = _DEFAULTS.copy()
    data['models']['elements'] = sorted(models['elements'], key=lambda el: el['type'])
    data['models']['beamlines'] = models['beamlines']

    if default_beamline_id:
        data['models']['simulation']['activeBeamlineId'] = default_beamline_id
        data['models']['simulation']['visualizationBeamlineId'] = default_beamline_id

    return data


def _create_name_map(models):
    name_to_id = {}
    last_beamline_id = None

    for bl in models['beamlines']:
        name_to_id[bl['name'].upper()] = bl['id']
        last_beamline_id = bl['id']

    for el in models['elements']:
        name_to_id[el['name'].upper()] = el['_id']

    return name_to_id, last_beamline_id


def _validate_beamline(bl, name_to_id):
    items = []
    for name in bl['items']:
        #TODO(pjm): handle reversed elements
        if re.search(r'^-', name):
            name = re.sub(r'^-', '', name)
        if name.upper() not in name_to_id:
            raise IOError('{}: unknown beamline item name'.format(name))
        items.append(name_to_id[name.upper()])
    return items


def _validate_field(el, field):
    if field in ['_id', 'type']:
        return
    field_type = None
    for f in _SCHEMA['model'][el['type']]:
        if f == field:
            field_type = _SCHEMA['model'][el['type']][f][1]
    if not field_type:
        pkdp('{}: unkown field type for {}', field, el['type'])
    else:
        if field_type == 'OutputFile':
            el[field] = '{}.{}.sdds'.format(el['name'], field)
        elif field_type == 'Float':
            if re.search(r'\S\s+\S', el[field]):
                out = subprocess.check_output('rpnl "{}"'.format(el[field]), shell=True)
                if len(out):
                    el[field] = out.strip()
                else:
                    raise IOError('invalid rpn: {}'.format(el[field]))


def _validate_type(el):
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
        raise IOError('{}: element not found'.format(type))
    return match
