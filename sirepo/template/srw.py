# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import glob
import json
import os
import py
import py.path
import re
import shutil

from pykern import pkio
from pykern import pkjinja
from pykern import pkresource

from sirepo.template import template_common

#: How long before killing SRW process
MAX_SECONDS = 60

_EXAMPLE_SIMULATIONS = [
    'Bending Magnet Radiation',
    'Circular Aperture',
    'Ellipsoidal Undulator Example',
    'Idealized Free Electron Laser Pulse',
    'Focusing Bending Magnet Radiation',
    'Gaussian X-ray beam through a Beamline containing Imperfect Mirrors',
    'Gaussian X-ray Beam Through Perfect CRL',
    'NSLS-II CHX beamline',
    'Polarization of Bending Magnet Radiation',
    'Young\'s Double Slit Experiment',
    'Undulator Radiation',
    'Soft X-Ray Undulator Radiation Containing VLS Grating',
]

#: Where server files and static files are found
_STATIC_FOLDER = py.path.local(pkresource.filename('static'))

with open(str(_STATIC_FOLDER.join('json/beams.json'))) as f:
    _PREDEFINED_BEAMS = json.load(f)

with open(str(_STATIC_FOLDER.join('json/mirrors.json'))) as f:
    _PREDEFINED_MIRRORS = json.load(f)


def fixup_old_data(data):
    """Fixup data to match the most recent schema."""
    if 'post_propagation' in data['models']:
        data['models']['postPropagation'] = data['models']['post_propagation']
        del data['models']['post_propagation']
    if 'beamName' in data['models']['electronBeam']:
        _fixup_beam(data, data['models']['electronBeam'])
        del data['models']['electronBeam']['beamName']
    for k in ('watchpointReport', 'twissParameters'):
        if k in data['models']:
            del data['models'][k]
    for item in data['models']['beamline']:
        if item['type'] == 'aperture' or item['type'] == 'obstacle':
            if not item.get('shape'):
                item['shape'] = 'r'
            if not item.get('horizontalOffset'):
                item['horizontalOffset'] = 0
            if not item.get('verticalOffset'):
                item['verticalOffset'] = 0
        elif item['type'] == 'mirror':
            if not item.get('heightProfileFile'):
                item['heightProfileFile'] = 'mirror_1d.dat'
        elif item['type'] == 'lens':
            if not item.get('horizontalOffset'):
                item['horizontalOffset'] = 0
            if not item.get('verticalOffset'):
                item['verticalOffset'] = 0
        elif item['type'] == 'ellipsoidMirror':
            if 'distanceToCenter' in item:
                del item['distanceToCenter']
                item['focalLength'] = item['distanceFromCenter']
                del item['distanceFromCenter']
            if 'orientation' not in item:
                item['orientation'] = 'y'
                item['heightProfileFile'] = None
                item['heightAmplification'] = 1

    if 'magneticField' in data['models']['simulation']:
        data['models']['simulation']['sourceType'] = data['models']['simulation']['magneticField']
        del data['models']['simulation']['magneticField']
    if 'sourceType' not in data['models']['simulation']:
        data['models']['simulation']['sourceType'] = 'u'
    if 'facility' not in data['models']['simulation']:
        facility = ''
        if data['models']['simulation']['name'] == 'NSLS-II CHX beamline':
            facility = 'NSLS-II'
        data['models']['simulation']['facility'] = facility
    if 'isExample' not in data['models']['simulation']:
        data['models']['simulation']['isExample'] = ''
        if data['models']['simulation']['name'] in _EXAMPLE_SIMULATIONS:
            data['models']['simulation']['isExample'] = '1'
    if 'mirrorFiles' in data['models']['simulation']:
        del data['models']['simulation']['mirrorFiles']
    if 'multipole' not in data['models']:
        data['models']['multipole'] = {
            'field': 0.4,
            'order': 1,
            'distribution': 'n',
            'length': 3,
        }
    if 'electronBeams' not in data['models']:
        data['models']['electronBeams'] = []
    if 'solenoid' in data['models']:
        del data['models']['solenoid']

    for k in data['models']:
        model = data['models'][k]
        if isinstance(model, dict):
            for old_field in ['_visible', '_loading', '_error']:
                if old_field in model:
                    del model[old_field]
            if k == 'intensityReport' or k == 'initialIntensityReport' or 'watchpointReport' in k:
                if 'method' in model:
                    del model['method']

    if 'gaussianBeam' not in data['models']:
        data['models']['gaussianBeam'] = {
            'waistX': 0,
            'waistY': 0,
            'waistZ': 0,
            'waistAngleX': 0,
            'waistAngleY': 0,
            'energyPerPulse': '0.001',
            'polarization': 1,
            'rmsSizeX': '9.78723',
            'rmsSizeY': '9.78723',
            'rmsPulseDuration': 0.1,
        }
    if 'sourceIntensityReport' not in data['models']:
        if 'gaussianBeamIntensityReport' in data['models']:
            data['models']['sourceIntensityReport'] = data['models']['gaussianBeamIntensityReport']
            del data['models']['gaussianBeamIntensityReport']
        else:
            data['models']['sourceIntensityReport'] = {
                'distanceFromSource': 20,
                'verticalRange': 0.5,
                'verticalPosition': 0,
                'horizontalRange': 0.5,
                'characteristic': 0,
                'sampleFactor': 0,
                'polarization': 6,
                'horizontalPosition': 0,
        }
    # move gaussianBeam.sampleFactor into reports
    if 'sampleFactor' in data['models']['gaussianBeam']:
        sampleFactor = data['models']['gaussianBeam'].pop('sampleFactor')
        for k in data['models']:
            if k == 'sourceIntensityReport' or k == 'initialIntensityReport' or 'watchpointReport' in k:
                data['models'][k]['sampleFactor'] = sampleFactor
    if 'distanceFromSource' not in data['models']['intensityReport']:
        position = _get_first_element_position(data)
        for name in ('intensityReport', 'powerDensityReport', 'fluxReport'):
            data['models'][name]['distanceFromSource'] = position
    if 'photonEnergy' in data['models']['initialIntensityReport']:
        photonEnergy = data['models']['initialIntensityReport']['photonEnergy']
        for k in data['models']:
            model = data['models'][k]
            if isinstance(model, dict):
                if 'photonEnergy' in data['models'][k]:
                    del data['models'][k]['photonEnergy']
        data['models']['simulation']['photonEnergy'] = photonEnergy

def generate_parameters_file(data, schema, run_dir=None):
    if 'report' in data and re.search('watchpointReport', data['report']):
        # render the watchpoint report settings in the initialIntensityReport template slot
        data['models']['initialIntensityReport'] = data['models'][data['report']].copy()
    _validate_data(data, schema)
    last_id = None
    if 'report' in data:
        m = re.search('watchpointReport(\d+)', data['report'])
        if m:
            last_id = int(m.group(1))
    v = template_common.flatten_data(data['models'], {})
    v['beamlineOptics'] = _generate_beamline_optics(data['models'], last_id)

    if 'report' in data and 'distanceFromSource' in data['models'][data['report']]:
        position = data['models'][data['report']]['distanceFromSource']
    else:
        position = _get_first_element_position(data)
    v['beamlineFirstElementPosition'] = position
    # initial drift = 1/2 undulator length + 2 periods
    source_type = data['models']['simulation']['sourceType']
    drift = 0
    if source_type == 'u':
        drift = -0.5 * data['models']['undulator']['length'] - 2 * data['models']['undulator']['period']
    else:
        #TODO(pjm): allow this to be set in UI?
        drift = 0
    v['electronBeamInitialDrift'] = drift
    # 1: auto-undulator 2: auto-wiggler
    v['energyCalculationMethod'] = 1 if source_type == 'u' else 2
    v['userDefinedElectronBeam'] = 1
    if 'isReadOnly' in data['models']['electronBeam'] and data['models']['electronBeam']['isReadOnly']:
        v['userDefinedElectronBeam'] = 0
    return pkjinja.render_resource('srw.py', v)


def get_data_file(run_dir, frame_index):
    for path in glob.glob(str(run_dir.join('res_*.dat'))):
        path = str(py.path.local(path))
        with open(path) as f:
            return os.path.basename(path), f.read(), 'text/plain'
    raise RuntimeError('no datafile found in run_dir: {}'.format(run_dir))


def new_simulation(data, new_simulation_data):
    source = new_simulation_data['sourceType']
    data['models']['simulation']['sourceType'] = source
    if source == 'g':
        intensityReport = data['models']['initialIntensityReport']
        intensityReport['sampleFactor'] = 0


def run_all_text():
    return '''
def run_all_reports():
    v = srwl_bl.srwl_uti_parse_options(get_srw_params())
    source_type, mag = setup_source(v)
    if source_type != 'g':
        v.ss = True
        v.ss_pl = 'e'
        v.pw = True
        v.pw_pl = 'xy'
    if source_type == 'u':
        v.sm = True
        v.sm_pl = 'e'
    v.si = True
    v.ws = True
    v.ws_pl = 'xy'
    op = get_beamline_optics()
    srwl_bl.SRWLBeamline(_name=v.name, _mag_approx=mag).calc_all(v, op)

run_all_reports()
'''

def static_lib_files():
    """Library shared between simulations of this type

    Returns:
        list: py.path.local objects
    """
    return [_STATIC_FOLDER.join('dat', m['fileName']) for m in _PREDEFINED_MIRRORS]


def _beamline_element(template, item, fields, propagation):
    return '    el.append({})\n{}'.format(
        template.format(*map(lambda x: item[x], fields)),
        _propagation_params(propagation[str(item['id'])][0]),
    )


def _fixup_beam(data, beam):
    # fix old beam structure to match new schema
    beam['name'] = beam['beamName']['name']
    beam['beamSelector'] = beam['name']
    for b in _PREDEFINED_BEAMS:
        if b['name'] == beam['name']:
            beam.update(b)
            return
    if 'twissParameters' in data['models']:
        if 'name' in data['models']['twissParameters']:
            del data['models']['twissParameters']['name']
        beam.update(data['models']['twissParameters'])
        beam['id'] = 1
        data['models']['electronBeams'] = [beam]
        return

    # otherwise default to the first predefined beam
    beam.update(_PREDEFINED_BEAMS[0])
    beam['beamSelector'] = beam['name']


def _generate_beamline_optics(models, last_id):
    beamline = models['beamline']
    propagation = models['propagation']
    res = '''
    el = []
    pp = []
'''
    prev = None
    has_item = False
    last_element = False
    want_final_propagation = True

    for item in beamline:
        if last_element:
            want_final_propagation = False
            break
        if prev:
            has_item = True
            size = item['position'] - prev['position']
            if size != 0:
                res += '    el.append(srwlib.SRWLOptD({}))\n'.format(size)
                res += _propagation_params(propagation[str(prev['id'])][1])
        if item['type'] == 'aperture':
            res += _beamline_element(
                'srwlib.SRWLOptA("{}", "a", {}, {}, {}, {})',
                item,
                ['shape', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
                propagation)
        elif item['type'] == 'crl':
            res += _beamline_element(
                'srwlib.srwl_opt_setup_CRL({}, {}, {}, {}, {}, {}, {}, {}, {}, 0, 0)',
                item,
                ['focalPlane', 'refractiveIndex', 'attenuationLength', 'shape', 'horizontalApertureSize', 'verticalApertureSize', 'radius', 'numberOfLenses', 'wallThickness'],
                propagation)
        elif item['type'] == 'ellipsoidMirror':
            res += _beamline_element(
                'srwlib.SRWLOptMirEl(_p={}, _q={}, _ang_graz={}, _size_tang={}, _size_sag={}, _nvx={}, _nvy={}, _nvz={}, _tvx={}, _tvy={})',
                item,
                ['position', 'focalLength', 'grazingAngle', 'tangentialSize', 'sagittalSize', 'normalVectorX', 'normalVectorY', 'normalVectorZ', 'tangentialVectorX', 'tangentialVectorY'],
                propagation)
            if item['heightProfileFile'] and item['heightProfileFile'] != 'None':
                res += '    ifnHDM = "{}"\n'.format(item['heightProfileFile'])
                res += '    hProfDataHDM = srwlib.srwl_uti_read_data_cols(ifnHDM, "\\t", 0, 1)\n'
                # overwrite propagation
                propagation[str(item['id'])][0] = [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0]
                res += _beamline_element(
                    'srwlib.srwl_opt_setup_surf_height_1d(hProfDataHDM, _dim="{}", _ang={}, _amp_coef={})',
                    item,
                    ['orientation', 'grazingAngle', 'heightAmplification'],
                    propagation)
        elif item['type'] == 'grating':
            res += _beamline_element(
                'srwlib.SRWLOptG(_mirSub=srwlib.SRWLOptMirPl(_size_tang={}, _size_sag={}, _nvx={}, _nvy={}, _nvz={}, _tvx={}, _tvy={}), _m={}, _grDen={}, _grDen1={}, _grDen2={}, _grDen3={}, _grDen4={})',
                item,
                ['tangentialSize', 'sagittalSize', 'normalVectorX', 'normalVectorY', 'normalVectorZ', 'tangentialVectorX', 'tangentialVectorY', 'diffractionOrder', 'grooveDensity0', 'grooveDensity1', 'grooveDensity2', 'grooveDensity3', 'grooveDensity4'],
                propagation)
        elif item['type'] == 'lens':
            res += _beamline_element(
                'srwlib.SRWLOptL({}, {}, {}, {})',
                item,
                ['horizontalFocalLength', 'verticalFocalLength', 'horizontalOffset', 'verticalOffset'],
                propagation)
        elif item['type'] == 'mirror':
            res += '    ifnHDM = "{}"\n'.format(item['heightProfileFile'])
            res += '    hProfDataHDM = srwlib.srwl_uti_read_data_cols(ifnHDM, "\\t", 0, 1)\n'
            res += _beamline_element(
                # 'srwlib.srwl_opt_setup_surf_height_1d(hProfDataHDM, "{}", _ang={}, _amp_coef={}, _nx=1000, _ny=200, _size_x={}, _size_y={})',
                'srwlib.srwl_opt_setup_surf_height_1d(hProfDataHDM, _dim="{}", _ang={}, _amp_coef={}, _size_x={}, _size_y={})',
                item,
                ['orientation', 'grazingAngle', 'heightAmplification', 'horizontalTransverseSize', 'verticalTransverseSize'],
                propagation)
        elif item['type'] == 'obstacle':
            res += _beamline_element(
                'srwlib.SRWLOptA("{}", "o", {}, {}, {}, {})',
                item,
                ['shape', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
                propagation)
        elif item['type'] == 'watch':
            if not has_item:
                res += '    el.append(srwlib.SRWLOptD({}))\n'.format(1.0e-16)
                res += _propagation_params(propagation[str(item['id'])][0])
            if last_id and last_id == int(item['id']):
                last_element = True
        prev = item
        res += '\n'

    # final propagation parameters
    if want_final_propagation:
        res += _propagation_params(models['postPropagation'])
    res += '    return srwlib.SRWLOptC(el, pp)\n'
    return res

def _get_first_element_position(data):
    beamline = data['models']['beamline']
    if len(beamline):
        return beamline[0]['position']
    return 20

def _propagation_params(prop):
    res = '    pp.append(['
    for i in range(len(prop)):
        res += str(prop[i])
        if (i != len(prop) - 1):
            res += ', '
    res += '])\n'
    return res

def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.parse_enums(schema['enum'])
    for k in data['models']:
        if k in schema['model']:
            template_common.validate_model(data['models'][k], schema['model'][k], enum_info)
    for m in data['models']['beamline']:
        template_common.validate_model(m, schema['model'][m['type']], enum_info)
    for item_id in data['models']['propagation']:
        _validate_propagation(data['models']['propagation'][item_id][0])
        _validate_propagation(data['models']['propagation'][item_id][1])
    _validate_propagation(data['models']['postPropagation'])

def _validate_propagation(prop):
    for i in range(len(prop)):
        prop[i] = int(prop[i]) if i in (0, 1, 3, 4) else float(prop[i])
