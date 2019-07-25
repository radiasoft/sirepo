# -*- coding: utf-8 -*-
u"""zgoubi datafile parser

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import elegant_common, zgoubi_parser
from sirepo.template import template_common
from sirepo.template.template_common import ModelUnits
import glob
import os.path
import re
import zipfile

MODEL_UNITS = None

_SIM_TYPE = 'zgoubi'
_SCHEMA = simulation_db.get_schema(_SIM_TYPE)
_UNIT_TEST_MODE = False


def import_file(text, unit_test_mode=False):
    if unit_test_mode:
        global _UNIT_TEST_MODE
        _UNIT_TEST_MODE = unit_test_mode
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
    if 'missingFiles' in info and len(info['missingFiles']):
        data['error'] = 'Missing data files'
        data['missingFiles'] = info['missingFiles']
    return data


def is_zip_file(path):
    return re.search(r'\.zip$', str(path), re.IGNORECASE)


def tosca_info(tosca):
    # determine the list of available files (from zip if necessary)
    # compute the tosca length from datafile
    #TODO(pjm): keep a cache on the tosca model?
    datafile = simulation_db.simulation_lib_dir(_SIM_TYPE).join(template_common.lib_file_name('TOSCA', 'magnetFile', tosca['magnetFile']))
    if not datafile.exists():
        return {
            'error': 'missing or invalid file: {}'.format(tosca['magnetFile']),
        }
    error = None
    length = None
    if is_zip_file(datafile):
        with zipfile.ZipFile(str(datafile), 'r') as z:
            filenames = []
            if 'fileNames' not in tosca or not tosca['fileNames']:
                tosca['fileNames'] = []
            for info in z.infolist():
                filenames.append(info.filename)
                if not length and info.filename in tosca['fileNames']:
                    length, error = _tosca_length(tosca, z.read(info).splitlines())
                    if length:
                        error = None
    else:
        filenames = [tosca['magnetFile']]
        with pkio.open_text(str(datafile)) as f:
            length, error = _tosca_length(tosca, f)
    if error:
        return {
            'error': error
        }
    return {
        'toscaInfo': {
            'toscaLength': length,
            'fileList': sorted(filenames) if filenames else None,
            'magnetFile': tosca['magnetFile'],
        },
    }


def _init_model_units():
    # Convert element units (m, rad) to the required zgoubi units (cm, mrad, degrees)

    def _changref2(transforms, is_native):
        # list of cm or deg values
        for t in transforms:
            if t.transformType == 'none':
                continue
            if t.transformType in ('XS', 'YS', 'ZS'):
                t.transformValue = ModelUnits.scale_value(t.transformValue, 'cm_to_m', is_native)
            elif t.transformType in ('XR', 'YR', 'ZR'):
                t.transformValue = ModelUnits.scale_value(t.transformValue, 'deg_to_rad', is_native)
            else:
                assert False, 'invalid transformType: {}'.format(t.transformType)
        return transforms

    def _il(v, is_native):
        if v == '0':
            return v
        if is_native:
            return '1' if v == '2' else '0'
        return '2' if v == '1' else '0'


    def _marker_plot(v, is_native):
        if is_native:
            return v
        else:
            return '"{}"'.format('.plt' if int(v) else '')

    def _xpas(v, is_native):
        if is_native:
            if re.search(r'\#', v):
                return v
            v2 = zgoubi_parser.parse_float(v)
            if v2 > 1e10:
                # old step size format
                m = re.search(r'^0*(\d+)\.0*(\d+)', v)
                assert m, 'XPAS failed to parse step size: {}'.format(v)
                return '#{}|{}|{}'.format(m.group(2), m.group(1), m.group(2))
        else:
            if re.search(r'\#', str(v)):
                v = re.sub(r'^#', '', v)
                return '[{}]'.format(','.join(v.split('|')))
        return ModelUnits.scale_value(v, 'cm_to_m', is_native)

    return ModelUnits({
        'AUTOREF': {
            'XCE': 'cm_to_m',
            'YCE': 'cm_to_m',
            'ALE': 'mrad_to_rad',
        },
        'BEND': {
            'l': 'cm_to_m',
            'IL': _il,
            'X_E': 'cm_to_m',
            'LAM_E': 'cm_to_m',
            'X_S': 'cm_to_m',
            'LAM_S': 'cm_to_m',
            'XPAS': _xpas,
            'XCE': 'cm_to_m',
            'YCE': 'cm_to_m',
        },
        'CAVITE': {
        },
        'CHANGREF': {
            'ALE': 'deg_to_rad',
            'XCE': 'cm_to_m',
            'YCE': 'cm_to_m',
        },
        'CHANGREF2': {
            'subElements': _changref2,
        },
        'DRIFT': {
            'l': 'cm_to_m',
        },
        'ffaDipole': {
            'ACN': 'deg_to_rad',
            'DELTA_RM': 'cm_to_m',
            'G0_E': 'cm_to_m',
            'SHIFT_E': 'cm_to_m',
            'OMEGA_E': 'deg_to_rad',
            'THETA_E': 'deg_to_rad',
            'R1_E': 'cm_to_m',
            'U1_E': 'cm_to_m',
            'U2_E': 'cm_to_m',
            'R2_E': 'cm_to_m',
            'G0_S': 'cm_to_m',
            'SHIFT_S': 'cm_to_m',
            'OMEGA_S': 'deg_to_rad',
            'THETA_S': 'deg_to_rad',
            'R1_S': 'cm_to_m',
            'U1_S': 'cm_to_m',
            'U2_S': 'cm_to_m',
            'R2_S': 'cm_to_m',
            'G0_L': 'cm_to_m',
            'SHIFT_L': 'cm_to_m',
            'OMEGA_L': 'deg_to_rad',
            'THETA_L': 'deg_to_rad',
            'R1_L': 'cm_to_m',
            'U1_L': 'cm_to_m',
            'U2_L': 'cm_to_m',
            'R2_L': 'cm_to_m',
        },
        'ffaSpiDipole': {
            'ACN': 'deg_to_rad',
            'DELTA_RM': 'cm_to_m',
            'G0_E': 'cm_to_m',
            'SHIFT_E': 'cm_to_m',
            'OMEGA_E': 'deg_to_rad',
            'XI_E': 'deg_to_rad',
            'G0_S': 'cm_to_m',
            'SHIFT_S': 'cm_to_m',
            'OMEGA_S': 'deg_to_rad',
            'XI_S': 'deg_to_rad',
            'G0_L': 'cm_to_m',
            'SHIFT_L': 'cm_to_m',
            'OMEGA_L': 'deg_to_rad',
            'XI_L': 'deg_to_rad',
        },
        'FFA': {
            'IL': _il,
            'AT': 'deg_to_rad',
            'RM': 'cm_to_m',
            'XPAS': 'cm_to_m',
            'RE': 'cm_to_m',
            'RS': 'cm_to_m',
        },
        'FFA_SPI': {
            'IL': _il,
            'AT': 'deg_to_rad',
            'RM': 'cm_to_m',
            'XPAS': 'cm_to_m',
            'RE': 'cm_to_m',
            'RS': 'cm_to_m',
        },
        'MARKER': {
            'plt': _marker_plot,
        },
        'MULTIPOL': {
            'l': 'cm_to_m',
            'IL': _il,
            'R_0': 'cm_to_m',
            'X_E': 'cm_to_m',
            'LAM_E': 'cm_to_m',
            'X_S': 'cm_to_m',
            'LAM_S': 'cm_to_m',
            'XPAS': _xpas,
            'XCE': 'cm_to_m',
            'YCE': 'cm_to_m',
        },
        'particleCoordinate': {
            'Y': 'cm_to_m',
            'Z': 'cm_to_m',
            'S': 'cm_to_m',
            'T': 'mrad_to_rad',
            'P': 'mrad_to_rad',
        },
        'QUADRUPO': {
            'l': 'cm_to_m',
            'IL': _il,
            'R_0': 'cm_to_m',
            'X_E': 'cm_to_m',
            'LAM_E': 'cm_to_m',
            'X_S': 'cm_to_m',
            'XPAS': _xpas,
            'LAM_S': 'cm_to_m',
            'XCE': 'cm_to_m',
            'YCE': 'cm_to_m',
        },
        'SEXTUPOL': {
            'l': 'cm_to_m',
            'IL': _il,
            'R_0': 'cm_to_m',
            'X_E': 'cm_to_m',
            'LAM_E': 'cm_to_m',
            'X_S': 'cm_to_m',
            'XPAS': _xpas,
            'LAM_S': 'cm_to_m',
            'XCE': 'cm_to_m',
            'YCE': 'cm_to_m',
        },
        'SOLENOID': {
            'l': 'cm_to_m',
            'IL': _il,
            'R_0': 'cm_to_m',
            'X_E': 'cm_to_m',
            'X_S': 'cm_to_m',
            'XPAS': _xpas,
            'XCE': 'cm_to_m',
            'YCE': 'cm_to_m',
        },
        'TOSCA': {
            'IL': _il,
            'A': 'cm_to_m',
            'B': 'cm_to_m',
            'C': 'cm_to_m',
            'XPAS': _xpas,
            'XCE': 'cm_to_m',
            'YCE': 'cm_to_m',
            'RE': 'cm_to_m',
            'RS': 'cm_to_m',
        },
    })


def _tosca_length(tosca, lines):
    col2 = []
    count = 0
    for line in lines:
        count += 1
        if count <= tosca['headerLineCount']:
            continue
        # some columns may not have spaces between values, ex:
        #  -1.2000E+02 0.0000E+00-3.5000E+01 3.1805E-03-1.0470E+01 2.0089E-03-2.4481E-15
        line = re.sub(r'(E[+\-]\d+)(\-)', r'\1 \2', line, flags=re.IGNORECASE)
        values = line.split()
        if len(values) > 2:
            try:
                col2.append(zgoubi_parser.parse_float(values[2]))
            except ValueError:
                pass
    if not len(col2):
        return None, 'missing column 2 data in file: {}'.format(tosca['magnetFile'])
    # scaled by unit conversion XN
    return (max(col2) - min(col2)) / 100.0 * tosca['XN'], None


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
        'missingFiles': [],
    }
    for el in elements:
        _validate_model(el['type'], el, info['missingFiles'])
        if 'name' in el:
            name = el['name']
            #TODO(pjm): don't de-duplicate certain types
            if el['type'] != 'MARKER' and not re.search(r'^DUMMY ', name):
                del el['name']
            if el not in info['elements']:
                current_id += 1
                info['ids'].append(current_id)
                info['names'].append(name)
                info['elements'].append(el)
            beamline.append(info['ids'][info['elements'].index(el)])
        else:
            if el['type'] in data['models']:
                pkdlog('updating existing {} model', el['type'])
                data['models'][el['type']].update(el)
            else:
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
        model[field] = zgoubi_parser.parse_float(model[field])
    elif field_type == 'Integer':
        model[field] = int(model[field])
    elif field_type == 'FileNameArray':
        return _validate_file_names(model, model[field])
    elif field_type in _SCHEMA['enum']:
        for v in _SCHEMA['enum'][field_type]:
            if v[0] == model[field]:
                return
        pkdlog('invalid enum value, {}.{} {}: {}', model['type'], field, field_type, model[field])
        model[field] = field_info[2]


def _validate_file_names(model, file_names):
    if _UNIT_TEST_MODE:
        return
    #TODO(pjm): currently specific to TOSCA element, but could be generalizaed on model['type']
    # flatten filenames, search indiviual and zip files which contains all files, set magnetFile if found
    for idx in range(len(file_names)):
        file_names[idx] = os.path.basename(file_names[idx])
    file_type = '{}-{}'.format(model['type'], 'magnetFile')
    magnet_file = None
    if len(file_names) == 1:
        name = file_names[0]
        target = template_common.lib_file_name(model['type'], 'magnetFile', name)
        if os.path.exists(str(simulation_db.simulation_lib_dir(_SIM_TYPE).join(target))):
            magnet_file = name
    for f in glob.glob(str(simulation_db.simulation_lib_dir(_SIM_TYPE).join('*.zip'))):
        zip_has_files = True
        zip_names = []
        with zipfile.ZipFile(f, 'r') as z:
            for info in z.infolist():
                zip_names.append(info.filename)
        for name in file_names:
            if name not in zip_names:
                zip_has_files = False
                break
        if zip_has_files:
            magnet_file = os.path.basename(f)[len(file_type) + 1:]
            break
    if magnet_file:
        model['magnetFile'] = magnet_file
        info = tosca_info(model)
        if 'toscaInfo' in info:
            model['l'] = info['toscaInfo']['toscaLength']
        return
    return {
        model['type']: sorted(file_names),
    }


def _validate_model(model_type, model, missing_files):
    assert model_type in _SCHEMA['model'], \
        'element type missing from schema: {}'.format(model_type)
    model_info = _SCHEMA['model'][model_type]
    if 'name' in model_info and 'name' not in model:
        model['name'] = ''
    MODEL_UNITS.scale_from_native(model_type, model)
    for f in model.keys():
        if isinstance(model[f], list) and len(model[f]) and 'type' in model[f][0]:
            for sub_model in model[f]:
                _validate_model(sub_model['type'], sub_model, missing_files)
            continue
        err = _validate_field(model, f, model_info)
        if err:
            missing_files.append(err)


MODEL_UNITS = _init_model_units()
