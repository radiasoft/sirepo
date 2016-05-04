# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import glob
import json
import math
import numpy as np
import os
import py.path
import re
import shutil
import traceback
import zipfile

from pykern import pkio
from pykern.pkdebug import pkdc, pkdp
from pykern import pkjinja
from pykern import pkresource
from sirepo.template import template_common
import uti_plot_com

WANT_BROWSER_FRAME_CACHE = False

_MULTI_ELECTRON_FILENAME_FOR_MODEL = {
    'fluxAnimation': 'res_spec_me.dat',
    'multiElectronAnimation': 'res_int_pr_me.dat',
}

_PREDEFINED_MAGNETIC_ZIP_FILE = 'magnetic_measurements.zip'

#: Where server files and static files are found
_STATIC_FOLDER = py.path.local(pkresource.filename('static'))

with open(str(_STATIC_FOLDER.join('json/beams.json'))) as f:
    _PREDEFINED_BEAMS = json.load(f)

with open(str(_STATIC_FOLDER.join('json/mirrors.json'))) as f:
    _PREDEFINED_MIRRORS = json.load(f)

with open(str(_STATIC_FOLDER.join('json/srw-schema.json'))) as f:
    _SCHEMA = json.load(f)


def background_percent_complete(data, run_dir, is_running):
    filename = str(run_dir.join(_MULTI_ELECTRON_FILENAME_FOR_MODEL[data['report']]))
    if os.path.isfile(filename):
        return {
            'percent_complete': 100,
            'frame_count': 1,
            'total_frames': 1,
            'last_update_time': os.path.getmtime(filename),
        }
    return {
        'percent_complete': 0,
        'frame_count': 0,
        'total_frames': 0,
    }


def copy_animation_file(source_path, target_path):
    # source_file = str(py.path.local(source_path).join('animation', _MULTI_ELECTRON_FILENAME))
    # if os.path.isfile(source_file):
    #     pkio.mkdir_parent(str(py.path.local(target_path).join('animation')))
    #     target_file = str(py.path.local(target_path).join('animation', _MULTI_ELECTRON_FILENAME))
    #     shutil.copyfile(source_file, target_file)
    pass


def _intensity_units(is_gaussian, model_data):
    if is_gaussian:
        if 'report' in model_data:
            i = model_data['models'][model_data['report']]['fieldUnits']
        else:
            i = model_data['models']['initialIntensityReport']['fieldUnits']
        return _SCHEMA['enum']['FieldUnits'][int(i) - 1][1]
    return 'ph/s/.1%bw/mm^2'


def extract_report_data(filename, model_data):
    flux_type = 1
    if 'report' in model_data and model_data['report'] == 'fluxAnimation':
        flux_type = int(model_data['animationArgs'])
    elif 'models' in model_data:
        flux_type = model_data['models']['fluxReport']['fluxType']
    sValShort = 'Flux'; sValType = 'Flux through Finite Aperture'; sValUnit = 'ph/s/.1%bw'
    if flux_type == 2:
        sValShort = 'Intensity'
        sValUnit = 'ph/s/.1%bw/mm^2'
    is_gaussian = False
    if 'models' in model_data and model_data['models']['simulation']['sourceType'] == 'g':
        is_gaussian = True
    files_3d = ['res_pow.dat', 'res_int_se.dat', 'res_int_pr_se.dat', 'res_mirror.dat', 'res_int_pr_me.dat']
    file_info = {
        'res_spec_se.dat': [['Photon Energy', 'Intensity', 'On-Axis Spectrum from Filament Electron Beam'], ['eV', _intensity_units(is_gaussian, model_data)]],
        'res_spec_me.dat': [['Photon Energy', sValShort, sValType], ['eV', sValUnit]],
        'res_pow.dat': [['Horizontal Position', 'Vertical Position', 'Power Density', 'Power Density'], ['m', 'm', 'W/mm^2']],
        'res_int_se.dat': [['Horizontal Position', 'Vertical Position', '{photonEnergy} eV Before Propagation', 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        #TODO(pjm): improve multi-electron label
        'res_int_pr_me.dat': [['Horizontal Position', 'Vertical Position', 'After Propagation', 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        'res_int_pr_se.dat': [['Horizontal Position', 'Vertical Position', '{photonEnergy} eV After Propagation', 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        'res_mirror.dat': [['Horizontal Position', 'Vertical Position', 'Optical Path Difference', 'Optical Path Difference'], ['m', 'm', 'm']],
    }

    data, mode, allrange, arLabels, arUnits = uti_plot_com.file_load(filename)
    filename = os.path.basename(filename)

    title = file_info[filename][0][2]
    if '{photonEnergy}' in title:
        title = title.format(photonEnergy=model_data['models']['simulation']['photonEnergy'])
    info = {
        'title': title,
        'x_range': [allrange[0], allrange[1]],
        'y_label': _superscript(file_info[filename][0][1] + ' [' + file_info[filename][1][1] + ']'),
        'x_label': file_info[filename][0][0] + ' [' + file_info[filename][1][0] + ']',
        'x_units': file_info[filename][1][0],
        'y_units': file_info[filename][1][1],
        'points': data,
    }
    if filename in files_3d:
        info = _remap_3d(info, allrange, file_info[filename][0][3], file_info[filename][1][2])
    return info


def fixup_old_data(data):
    """Fixup data to match the most recent schema."""
    if 'name' in data['models']['simulation'] and data['models']['simulation']['name'] == 'Undulator Radiation':
        data['models']['sourceIntensityReport']['distanceFromSource'] = 20
    # add point count to reports and move sampleFactor to simulation model
    if data['models']['fluxReport'] and 'photonEnergyPointCount' not in data['models']['fluxReport']:
        data['models']['fluxReport']['photonEnergyPointCount'] = 10000
        data['models']['powerDensityReport']['horizontalPointCount'] = 100
        data['models']['powerDensityReport']['verticalPointCount'] = 100
        data['models']['intensityReport']['photonEnergyPointCount'] = 10000
        # move sampleFactor to simulation model
        if 'sampleFactor' in data['models']['initialIntensityReport']:
            data['models']['simulation']['sampleFactor'] = data['models']['initialIntensityReport']['sampleFactor']
            data['models']['simulation']['horizontalPointCount'] = 100
            data['models']['simulation']['verticalPointCount'] = 100
            for k in data['models']:
                if k == 'sourceIntensityReport' or k == 'initialIntensityReport' or 'watchpointReport' in k:
                    del data['models'][k]['sampleFactor']
    if data['models']['fluxReport'] and 'magneticField' not in data['models']['fluxReport']:
        data['models']['fluxReport']['magneticField'] = 1
        data['models']['fluxReport']['method'] = -1
        data['models']['fluxReport']['precision'] = 0.01
        data['models']['fluxReport']['initialHarmonic'] = 1
        data['models']['fluxReport']['finalHarmonic'] = 15
    if 'fluxAnimation' in data['models']:
        if 'magneticField' not in data['models']['fluxAnimation']:
            data['models']['fluxAnimation']['magneticField'] = 2
            data['models']['fluxAnimation']['method'] = 1
            data['models']['fluxAnimation']['precision'] = 0.01
            data['models']['fluxAnimation']['initialHarmonic'] = 1
            data['models']['fluxAnimation']['finalHarmonic'] = 15
    if data['models']['intensityReport']:
        if 'method' not in data['models']['intensityReport']:
            if data['models']['simulation']['sourceType'] in ['u', 't']:
                data['models']['intensityReport']['method'] = 1
            elif data['models']['simulation']['sourceType'] in ['m']:
                data['models']['intensityReport']['method'] = 2
            else:
                data['models']['intensityReport']['method'] = 0
            data['models']['intensityReport']['precision'] = 0.01
            data['models']['intensityReport']['magneticField'] = 1
            data['models']['intensityReport']['fieldUnits'] = 1
    if 'simulationStatus' not in data['models'] or 'state' in data['models']['simulationStatus']:
        data['models']['simulationStatus'] = {}
    if 'outOfSessionSimulationId' not in data['models']['simulation']:
        data['models']['simulation']['outOfSessionSimulationId'] = ''
    if 'multiElectronAnimation' not in data['models']:
        m = data['models']['initialIntensityReport']
        data['models']['multiElectronAnimation'] = {
            'horizontalPosition': m['horizontalPosition'],
            'horizontalRange': m['horizontalRange'],
            'verticalPosition': m['verticalPosition'],
            'verticalRange': m['verticalRange'],
            'stokesParameter': '0',
        }
    for item in data['models']['beamline']:
        if item['type'] == 'ellipsoidMirror':
            if 'firstFocusLength' not in item:
                item['firstFocusLength'] = item['position']
        elif item['type'] == 'grating':
            if 'grazingAngle' not in item:
                angle = 0
                if item['normalVectorX']:
                    angle = math.acos(abs(float(item['normalVectorX']))) * 1000
                elif item['normalVectorY']:
                    angle = math.acos(abs(float(item['normalVectorY']))) * 1000
                item['grazingAngle'] = angle
    for k in data['models']:
        if k == 'sourceIntensityReport' or k == 'initialIntensityReport' or 'watchpointReport' in k:
            if 'fieldUnits' not in data['models'][k]:
                data['models'][k]['fieldUnits'] = 1
    if 'samplingMethod' not in data['models']['simulation']:
        simulation = data['models']['simulation']
        simulation['samplingMethod'] = 1 if simulation['sampleFactor'] > 0 else 2
        for k in ['horizontalPosition', 'horizontalRange', 'verticalPosition', 'verticalRange']:
            simulation[k] = data['models']['initialIntensityReport'][k]
    if 'horizontalPosition' in data['models']['initialIntensityReport']:
        for k in data['models']:
            if k == 'sourceIntensityReport' or k == 'initialIntensityReport' or 'watchpointReport' in k:
                for f in ['horizontalPosition', 'horizontalRange', 'verticalPosition', 'verticalRange']:
                    del data['models'][k][f]
    if 'documentationUrl' not in data['models']['simulation']:
        data['models']['simulation']['documentationUrl'] = ''
    if 'tabulatedUndulator' not in data['models']:
        data['models']['tabulatedUndulator'] = {
            'gap': 6.72,
            'phase': 0,
            'magneticFile': _PREDEFINED_MAGNETIC_ZIP_FILE,
            'longitudinalPosition': 1.305,
            'indexFile': '',
        }
    if 'drift' not in data['models']['electronBeam']:
        data['models']['electronBeam']['drift'] = 0.0
    if 'fluxAnimation' not in data['models']:
        data['models']['fluxAnimation'] = data['models']['fluxReport'].copy()
        data['models']['fluxAnimation']['photonEnergyPointCount'] = 1000
        data['models']['fluxAnimation']['initialEnergy'] = 10000.0
        data['models']['fluxAnimation']['finalEnergy'] = 20000.0
        data['models']['fluxAnimation']['magneticField'] = 2
        data['models']['fluxAnimation']['method'] = 1
        data['models']['fluxAnimation']['precision'] = 0.01
        data['models']['fluxAnimation']['initialHarmonic'] = 1
        data['models']['fluxAnimation']['finalHarmonic'] = 15

def generate_parameters_file(data, schema, run_dir=None, run_async=False):
    if 'report' in data:
        if data['report'] == 'fluxAnimation':
            data['models']['fluxReport'] = data['models'][data['report']].copy()
        elif re.search('watchpointReport', data['report']) or data['report'] == 'sourceIntensityReport':
            # render the watchpoint report settings in the initialIntensityReport template slot
            data['models']['initialIntensityReport'] = data['models'][data['report']].copy()
    _validate_data(data, schema)
    last_id = None
    if 'report' in data:
        m = re.search('watchpointReport(\d+)', data['report'])
        if m:
            last_id = int(m.group(1))
    if int(data['models']['simulation']['samplingMethod']) == 2:
        data['models']['simulation']['sampleFactor'] = 0
    v = template_common.flatten_data(data['models'], {})
    v['beamlineOptics'] = _generate_beamline_optics(data['models'], last_id)
    # und_g and und_ph API units are mm rather than m
    v['tabulatedUndulator_gap'] *= 1000
    v['tabulatedUndulator_phase'] *= 1000

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
        # undulator longitudinal center only set with tabulatedUndulator
        v['tabulatedUndulator_longitudinalPosition'] = 0
    else:
        drift = data['models']['electronBeam']['drift']
    v['electronBeamInitialDrift'] = drift
    # 1: auto-undulator 2: auto-wiggler
    v['energyCalculationMethod'] = 2
    if source_type == 'u' or source_type == 't':
        v['energyCalculationMethod'] = 1
    v['userDefinedElectronBeam'] = 1
    if 'isReadOnly' in data['models']['electronBeam'] and data['models']['electronBeam']['isReadOnly']:
        v['userDefinedElectronBeam'] = 0
    v['fluxNumberOfMacroElectrons'] = 1
    if 'report' in data:
        v[data['report']] = 1
        if data['report'] == 'fluxAnimation':
            v['fluxNumberOfMacroElectrons'] = 1000000
    return pkjinja.render_resource('srw.py', v)


def get_animation_name(data):
    return data['modelName']


def get_application_data(data):
    if data['method'] == 'compute_grazing_angle':
        return _compute_grazing_angle(data['optical_element'])
    elif data['method'] == 'compute_crystal_init':
        return _compute_crystal_init(data['optical_element'])
    elif data['method'] == 'compute_crystal_orientation':
        return _compute_crystal_orientation(data['optical_element'])
    raise RuntimeError('unknown application data method: {}'.format(data['method']))


def get_data_file(run_dir, frame_index):
    for path in glob.glob(str(run_dir.join('res_*.dat'))):
        path = str(py.path.local(path))
        with open(path) as f:
            return os.path.basename(path), f.read(), 'text/plain'
    raise RuntimeError('no datafile found in run_dir: {}'.format(run_dir))


def get_simulation_frame(run_dir, data, model_data):
    return extract_report_data(str(run_dir.join(_MULTI_ELECTRON_FILENAME_FOR_MODEL[data['report']])), data)


def is_cache_valid(data, old_data):
    related_models = [data['report'], 'electronBeam', 'gaussianBeam', 'multipole', 'simulation', 'tabulatedUndulator', 'undulator']

    if data['report'] == 'mirrorReport' or 'watchpointReport' in data['report']:
        related_models.append('beamline')
        if 'watchpointReport' in data['report']:
            related_models.append('postPropagation')
            related_models.append('propagation')

    if 'watchpointReport' in data['report'] or data['report'] in ['fluxReport', 'initialIntensityReport', 'intensityReport', 'mirrorReport', 'powerDensityReport', 'sourceIntensityReport']:
        for name in related_models:
            if data['models'][name] != old_data['models'][name]:
                return False
        return True
    return False


def new_simulation(data, new_simulation_data):
    source = new_simulation_data['sourceType']
    data['models']['simulation']['sourceType'] = source
    if source == 'g':
        intensityReport = data['models']['initialIntensityReport']
        intensityReport['sampleFactor'] = 0


def prepare_aux_files(run_dir, data):
    if not data['models']['simulation']['sourceType'] == 't':
        return
    filename = data['models']['tabulatedUndulator']['magneticFile']
    filepath = run_dir.join(filename)
    if filename == _PREDEFINED_MAGNETIC_ZIP_FILE and not filepath.check():
        _STATIC_FOLDER.join('dat', _PREDEFINED_MAGNETIC_ZIP_FILE).copy(run_dir)
    zip_file = zipfile.ZipFile(str(filepath))
    zip_file.extractall(str(run_dir))
    for f in zip_file.namelist():
        if re.search('\.txt', f):
            data['models']['tabulatedUndulator']['indexFile'] = f
            break


def remove_last_frame(run_dir):
    pass


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
    res = [_STATIC_FOLDER.join('dat', m['fileName']) for m in _PREDEFINED_MIRRORS]
    res.append(_STATIC_FOLDER.join('dat', _PREDEFINED_MAGNETIC_ZIP_FILE))
    return res


def write_parameters(data, schema, run_dir, run_async):
    """Write the parameters file

    Args:
        data (dict): input
        schema (dict): to validate data
        run_dir (py.path): where to write
        run_async (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        generate_parameters_file(
            data,
            schema,
            run_dir,
            run_async,
        ),
    )


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


def _compute_crystal_init(model):
    parms_list = ['dSpacing', 'psi0r', 'psi0i', 'psiHr', 'psiHi', 'psiHBr', 'psiHBi']
    try:
        material_raw = model['material']  # name contains either "(SRW)" or "(X0h)"
        material = material_raw.split()[0]  # short name for SRW (e.g., Si), long name for X0h (e.g., Silicon)
        h = int(model['h'])
        k = int(model['k'])
        l = int(model['l'])
        millerIndices = [h, k, l]
        energy = model['energy']

        if re.search('(X0h)', material_raw):
            from sirepo.srw_crystal_x0h import srw_crystal_x0h
            dc, xr0, xi0, xrh, xih = srw_crystal_x0h(material, energy, h, k, l)
        elif re.search('(SRW)', material_raw):
            from srwl_uti_cryst import srwl_uti_cryst_pl_sp, srwl_uti_cryst_pol_f
            dc = srwl_uti_cryst_pl_sp(millerIndices, material)
            xr0, xi0, xrh, xih = srwl_uti_cryst_pol_f(energy, millerIndices, material)
        else:
            dc = xr0 = xi0 = xrh = xih = None
        model['dSpacing'] = dc
        model['psi0r'] = xr0
        model['psi0i'] = xi0
        model['psiHr'] = xrh
        model['psiHi'] = xih
        model['psiHBr'] = xrh
        model['psiHBi'] = xih
    except Exception:
        pkdp('\n{}', traceback.format_exc())
        for key in parms_list:
            model[key] = None

    return model


def _compute_crystal_orientation(model):
    parms_list = ['nvx', 'nvy', 'nvz', 'tvx', 'tvy']
    try:
        import srwlib
        opCr = srwlib.SRWLOptCryst(
            _d_sp=model['dSpacing'],
            _psi0r=model['psi0r'],
            _psi0i=model['psi0i'],
            _psi_hr=model['psiHr'],
            _psi_hi=model['psiHi'],
            _psi_hbr=model['psiHBr'],
            _psi_hbi=model['psiHBi'],
            _tc=model['crystalThickness'],
            _ang_as=model['asymmetryAngle'],
        )
        orientDataCr = opCr.find_orient(_en=model['energy'], _ang_dif_pl=model['grazingAngle'])[0]
        tCr = orientDataCr[0]  # Tangential Vector to Crystal surface
        nCr = orientDataCr[2]  # Normal Vector to Crystal surface

        if model['rotationAngle'] != 0:
            import uti_math
            rot = uti_math.trf_rotation([0, 1, 0], model['rotationAngle'], [0, 0, 0])[0]
            nCr = uti_math.matr_prod(rot, nCr)
            tCr = uti_math.matr_prod(rot, tCr)

        model['nvx'] = nCr[0]
        model['nvy'] = nCr[1]
        model['nvz'] = nCr[2]
        model['tvx'] = tCr[0]
        model['tvy'] = tCr[1]
    except Exception:
        pkdp('\n{}', traceback.format_exc())
        for key in parms_list:
            model[key] = None

    return model


def _compute_grazing_angle(model):

    def preserve_sign(item, field, new_value):
        old_value = item[field] if field in item else 0
        was_negative = float(old_value) < 0
        item[field] = float(new_value)
        if (was_negative and item[field] > 0) or item[field] < 0:
            item[field] = - item[field]

    grazing_angle = float(model['grazingAngle']) / 1000.0
    preserve_sign(model, 'normalVectorZ', math.sin(grazing_angle))

    if 'normalVectorY' in model and float(model['normalVectorY']) == 0:
        preserve_sign(model, 'normalVectorX', math.cos(grazing_angle))
        preserve_sign(model, 'tangentialVectorX', math.sin(grazing_angle))
        model['tangentialVectorY'] = 0
    if 'normalVectorX' in model and float(model['normalVectorX']) == 0:
        preserve_sign(model, 'normalVectorY', math.cos(grazing_angle))
        model['tangentialVectorX'] = 0
        preserve_sign(model, 'tangentialVectorY', math.sin(grazing_angle))

    return model


def _crystal_element(template, item, fields, propagation):
    """The function prepares the code for processing of the crystal element.

    Args:
        template: template for SRWLOptCryst().
        item: dictionary with parameters of the crystal.
        fields: fields of the crystal.
        propagation: propagation list for the crystal.

    Returns:
        res: the resulted block of text.
    """

    res = '''
    opCr = {}
    # Set crystal orientation:
    opCr.set_orient({}, {}, {}, {}, {})
    el.append(opCr)
    {}\n'''.format(
        template.format(*map(lambda x: item[x], fields)),
        item['nvx'], item['nvy'], item['nvz'], item['tvx'], item['tvy'],
        _propagation_params(propagation[str(item['id'])][0]).strip()
    )
    return res


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
        elif item['type'] == 'crystal':
            res += _crystal_element(
                'srwlib.SRWLOptCryst(_d_sp={}, _psi0r={}, _psi0i={}, _psi_hr={}, _psi_hi={}, _psi_hbr={}, _psi_hbi={}, _tc={}, _ang_as={})',
                item,
                ['dSpacing', 'psi0r', 'psi0i', 'psiHr', 'psiHi', 'psiHBr', 'psiHBi', 'crystalThickness', 'asymmetryAngle'],
                propagation)
            res += _height_profile_element(item, propagation, overwrite_propagation=True)
        elif item['type'] == 'ellipsoidMirror':
            res += _beamline_element(
                'srwlib.SRWLOptMirEl(_p={}, _q={}, _ang_graz={}, _size_tang={}, _size_sag={}, _nvx={}, _nvy={}, _nvz={}, _tvx={}, _tvy={})',
                item,
                ['firstFocusLength', 'focalLength', 'grazingAngle', 'tangentialSize', 'sagittalSize', 'normalVectorX', 'normalVectorY', 'normalVectorZ', 'tangentialVectorX', 'tangentialVectorY'],
                propagation)
            res += _height_profile_element(item, propagation, overwrite_propagation=True)
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
            res += _height_profile_element(item, propagation)
        elif item['type'] == 'obstacle':
            res += _beamline_element(
                'srwlib.SRWLOptA("{}", "o", {}, {}, {}, {})',
                item,
                ['shape', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
                propagation)
        elif item['type'] == 'sphericalMirror':
            res += _beamline_element(
                'srwlib.SRWLOptMirSph(_r={}, _size_tang={}, _size_sag={}, _nvx={}, _nvy={}, _nvz={}, _tvx={}, _tvy={})',
                item,
                ['radius', 'tangentialSize', 'sagittalSize', 'normalVectorX', 'normalVectorY', 'normalVectorZ','tangentialVectorX', 'tangentialVectorY'],
                propagation)
            res += _height_profile_element(item, propagation, overwrite_propagation=True)
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

def _height_profile_element(item, propagation, overwrite_propagation=False):
    if overwrite_propagation:
        if item['heightProfileFile'] and item['heightProfileFile'] != 'None':
            propagation[str(item['id'])][0] = [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0]
        else:
            return ''
    res = '    ifnHDM = "{}"\n'.format(item['heightProfileFile'])
    res += '    hProfDataHDM = srwlib.srwl_uti_read_data_cols(ifnHDM, "\\t", 0, 1)\n'
    fields = ['orientation', 'grazingAngle', 'heightAmplification']
    if 'horizontalTransverseSize' in item:
        template = 'srwlib.srwl_opt_setup_surf_height_1d(hProfDataHDM, _dim="{}", _ang={}, _amp_coef={}, _size_x={}, _size_y={})'
        fields.extend(('horizontalTransverseSize', 'verticalTransverseSize'))
    else:
        template = 'srwlib.srwl_opt_setup_surf_height_1d(hProfDataHDM, _dim="{}", _ang={}, _amp_coef={})'
    res += _beamline_element(template, item, fields, propagation)
    return res

def _propagation_params(prop):
    res = '    pp.append(['
    for i in range(len(prop)):
        res += str(prop[i])
        if (i != len(prop) - 1):
            res += ', '
    res += '])\n'
    return res

def _remap_3d(info, allrange, z_label, z_units):
    x_range = [allrange[3], allrange[4], allrange[5]]
    y_range = [allrange[6], allrange[7], allrange[8]]
    ar2d = info['points']

    totLen = int(x_range[2]*y_range[2])
    lenAr2d = len(ar2d)
    if lenAr2d > totLen: ar2d = np.array(ar2d[0:totLen])
    elif lenAr2d < totLen:
        auxAr = np.array('d', [0]*lenAr2d)
        for i in range(lenAr2d): auxAr[i] = ar2d[i]
        ar2d = np.array(auxAr)
    if isinstance(ar2d,(list,np.array)): ar2d = np.array(ar2d)
    ar2d = ar2d.reshape(y_range[2],x_range[2])
    return {
        'x_range': x_range,
        'y_range': y_range,
        'x_label': info['x_label'],
        'y_label': info['y_label'],
        'z_label': _superscript(z_label + ' [' + z_units + ']'),
        'title': info['title'],
        'z_matrix': ar2d.tolist(),
    }

def _superscript(val):
    return re.sub(r'\^2', u'\u00B2', val)

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
