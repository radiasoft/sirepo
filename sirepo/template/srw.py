# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkio
from pykern import pkjinja
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdexc, pkdp
from sirepo import crystal
from sirepo import simulation_db
from sirepo.template import template_common
from srwl_uti_cryst import srwl_uti_cryst_pl_sp, srwl_uti_cryst_pol_f
import bnlcrl.pkcli.simulate
import glob
import json
import math
import numpy as np
import os
import py.path
import random
import re
import shutil
import sirepo.importer
import traceback
import uti_plot_com
import zipfile

WANT_BROWSER_FRAME_CACHE = False

_DATA_FILE_FOR_MODEL = {
    'fluxAnimation': 'res_spec_me.dat',
    'fluxReport': 'res_spec_me.dat',
    'initialIntensityReport': 'res_int_se.dat',
    'intensityReport': 'res_spec_se.dat',
    'multiElectronAnimation': 'res_int_pr_me.dat',
    'powerDensityReport': 'res_pow.dat',
    'sourceIntensityReport': 'res_int_se.dat',
    'trajectoryReport': 'res_trj.dat',
}

_EXAMPLE_FOLDERS = {
    'Bending Magnet Radiation': '/SR Calculator',
    'Diffraction by an Aperture': '/Wavefront Propagation',
    'Ellipsoidal Undulator Example': '/Examples',
    'Focusing Bending Magnet Radiation': '/Examples',
    'Gaussian X-ray Beam Through Perfect CRL': '/Examples',
    'Gaussian X-ray beam through a Beamline containing Imperfect Mirrors': '/Examples',
    'Idealized Free Electron Laser Pulse': '/SR Calculator',
    'LCLS SXR beamline - Simplified': '/Light Source Facilities/LCLS',
    'LCLS SXR beamline': '/Light Source Facilities/LCLS',
    'NSLS-II CHX beamline': '/Light Source Facilities/NSLS-II/NSLS-II CHX beamline',
    'Polarization of Bending Magnet Radiation': '/Examples',
    'Soft X-Ray Undulator Radiation Containing VLS Grating': '/Examples',
    'Tabulated Undulator Example': '/Examples',
    'Undulator Radiation': '/SR Calculator',
    'Young\'s Double Slit Experiment (green laser)': '/Wavefront Propagation',
    'Young\'s Double Slit Experiment (green laser, no lens)': '/Wavefront Propagation',
    'Young\'s Double Slit Experiment': '/Wavefront Propagation',
}

#: Where server files and static files are found
_STATIC_FOLDER = py.path.local(pkresource.filename('static'))

with open(str(_STATIC_FOLDER.join('json/beams.json'))) as f:
    _PREDEFINED_BEAMS = json.load(f)

with open(str(_STATIC_FOLDER.join('json/mirrors.json'))) as f:
    _PREDEFINED_MIRRORS = json.load(f)

with open(str(_STATIC_FOLDER.join('json/magnetic_measurements.json'))) as f:
    _PREDEFINED_MAGNETIC_ZIP_FILES = json.load(f)

with open(str(_STATIC_FOLDER.join('json/srw-schema.json'))) as f:
    _SCHEMA = json.load(f)


def background_percent_complete(report, run_dir, is_running, schema):
    filename = str(run_dir.join(_DATA_FILE_FOR_MODEL[report]))
    if os.path.isfile(filename):
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        return {
            'percent_complete': 100,
            'frame_count': 1,
            'total_frames': 1,
            'last_update_time': os.path.getmtime(filename),
            'start_time': data['models']['simulationStatus'][report]['startTime'] if report in data['models']['simulationStatus'] else None,
        }
    return {
        'percent_complete': 0,
        'frame_count': 0,
        'total_frames': 0,
    }


def copy_related_files(data, source_path, target_path):
    pass


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
    if model_data['report'] == 'initialIntensityReport':
        before_propagation_name = 'Before Propagation (E={photonEnergy} eV)'
    else:
        before_propagation_name = 'E={photonEnergy} eV'
    file_info = {
        'res_trj.dat': [['Longitudinal Position', 'Position', 'Electron Trajectory'], ['m', 'm']],
        'res_spec_se.dat': [['Photon Energy', 'Intensity', 'On-Axis Spectrum from Filament Electron Beam'], ['eV', _intensity_units(is_gaussian, model_data)]],
        'res_spec_me.dat': [['Photon Energy', sValShort, sValType], ['eV', sValUnit]],
        'res_pow.dat': [['Horizontal Position', 'Vertical Position', 'Power Density', 'Power Density'], ['m', 'm', 'W/mm^2']],
        'res_int_se.dat': [['Horizontal Position', 'Vertical Position', before_propagation_name, 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        #TODO(pjm): improve multi-electron label
        'res_int_pr_me.dat': [['Horizontal Position', 'Vertical Position', 'After Propagation', 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        'res_int_pr_se.dat': [['Horizontal Position', 'Vertical Position', 'After Propagation (E={photonEnergy} eV)', 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        'res_mirror.dat': [['Horizontal Position', 'Vertical Position', 'Optical Path Difference', 'Optical Path Difference'], ['m', 'm', 'm']],
    }

    if model_data['report'] == 'trajectoryReport':
        assert model_data['models']['trajectoryReport']['plotAxis'] in ['x', 'y']
        if model_data['models']['trajectoryReport']['plotAxis'] == 'x':
            axis_name = 'Horizontal'
        else:
            axis_name = 'Vertical'
        file_info['res_trj.dat'][0][1] = '{} {}'.format(axis_name, file_info['res_trj.dat'][0][1])
        data, mode, allrange, arLabels, arUnits = uti_plot_com.file_load(
            filename,
            traj_report=True,
            traj_axis=model_data['models']['trajectoryReport']['plotAxis'],
        )
    else:
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


def find_tab_undulator_length(zip_file, gap):
    """Find undulator length from the specified zip-archive with the magnetic measurements data.

    Args:
        zip_file: zip-archive with the magnetic measurements data.
        gap: undulator gap [mm].

    Returns:
        dict: dictionary with the found length, *.dat file name where the length was found and the closest gap.
    """
    z = zipfile.ZipFile(zip_file)
    index_dir, index_file = _find_index_file(z)
    with z.open(os.path.join(index_dir, index_file)) as f:
        sum_content = f.readlines()
    gap = float(gap)
    gaps_list = []
    dat_files_list = []
    for row in sum_content:
        v = row.split()
        gaps_list.append(float(v[0]))
        dat_files_list.append(v[3])

    d = _find_closest_value(gaps_list, gap)
    closest_gap = d['closest_value']
    dat_file = dat_files_list[d['idx']]

    with z.open(os.path.join(index_dir, dat_file)) as f:
        dat_content = f.readlines()

    step = float(dat_content[8].split('#')[1].strip())
    number_of_points = int(dat_content[9].split('#')[1].strip())
    found_length = round(step * number_of_points, 6)

    return {
        'found_length': found_length,
        'dat_file': dat_file,
        'closest_gap': closest_gap
    }


def fixup_electron_beam(data):
    if 'driftCalculationMethod' not in data['models']['electronBeam']:
        data['models']['electronBeam']['driftCalculationMethod'] = 'auto'  # can be either 'auto' or 'manual'

    if data['models']['simulation']['sourceType'] == 't':
        und = 'tabulatedUndulator'
    else:
        und = 'undulator'

    beam_parameters = _process_beam_parameters(
        data['models']['simulation']['sourceType'],
        data['models']['tabulatedUndulator']['undulatorType'],
        float(data['models'][und]['length']),
        float(data['models'][und]['period']) / 1000.0,
        data['models']['electronBeam'],
        )

    data['models']['electronBeam']['drift'] = beam_parameters['drift']

    if 'beamDefinition' not in data['models']['electronBeam']:
        data['models']['electronBeam']['beamDefinition'] = 't'  # "t" = Twiss; "m" = Moments
        for field in ['rmsSizeX', 'rmsDivergX', 'xxprX', 'rmsSizeY', 'rmsDivergY', 'xxprY']:
            data['models']['electronBeam'][field] = beam_parameters[field]
    return data


def fixup_old_data(data):
    """Fixup data to match the most recent schema."""
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
    if data['models']['fluxReport']:
        data['models']['fluxReport']['method'] = -1  # always approximate for static Flux Report
        data['models']['fluxReport']['precision'] = 0.01  # is not used in static Flux Report
        if 'initialHarmonic' not in data['models']['fluxReport']:
            data['models']['fluxReport']['initialHarmonic'] = 1
            data['models']['fluxReport']['finalHarmonic'] = 15
    if 'fluxAnimation' in data['models']:
        if 'method' not in data['models']['fluxAnimation']:
            data['models']['fluxAnimation']['method'] = 1
            data['models']['fluxAnimation']['precision'] = 0.01
            data['models']['fluxAnimation']['initialHarmonic'] = 1
            data['models']['fluxAnimation']['finalHarmonic'] = 15
    if data['models']['intensityReport']:
        if 'method' not in data['models']['intensityReport']:
            if data['models']['simulation']['sourceType'] in ['u', 't']:
                data['models']['intensityReport']['method'] = 1
            elif data['models']['simulation']['sourceType'] == 'm':
                data['models']['intensityReport']['method'] = 2
            else:
                data['models']['intensityReport']['method'] = 0
            data['models']['intensityReport']['precision'] = 0.01
            data['models']['intensityReport']['fieldUnits'] = 1
    if 'sourceIntensityReport' in data['models']:
        if 'precision' not in data['models']['sourceIntensityReport']:
            data['models']['sourceIntensityReport']['precision'] = 0.01
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
    if 'numberOfMacroElectrons' not in data['models']['multiElectronAnimation']:  # added 08/10/2016 for ticket #278
        data['models']['multiElectronAnimation']['numberOfMacroElectrons'] = 100000
    for item in data['models']['beamline']:
        if item['type'] == 'ellipsoidMirror':
            if 'firstFocusLength' not in item:
                item['firstFocusLength'] = item['position']
        if item['type'] in ['grating', 'ellipsoidMirror', 'sphericalMirror']:
            if 'grazingAngle' not in item:
                angle = 0
                if item['normalVectorX']:
                    angle = math.acos(abs(float(item['normalVectorX']))) * 1000
                elif item['normalVectorY']:
                    angle = math.acos(abs(float(item['normalVectorY']))) * 1000
                item['grazingAngle'] = angle
        if item['type'] in ['crystal', 'ellipsoidMirror', 'mirror', 'sphericalMirror']:
            if 'heightProfileDimension' not in item:
                item['heightProfileDimension'] = 1
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
            'magneticFile': _PREDEFINED_MAGNETIC_ZIP_FILES[0]['fileName'],
            'longitudinalPosition': 1.305,
            'magnMeasFolder': '',
            'indexFile': '',
        }
    if 'verticalAmplitude' not in data['models']['tabulatedUndulator']:
        data['models']['tabulatedUndulator']['undulatorType'] = 'u_t'
        data['models']['tabulatedUndulator']['period'] = 21
        data['models']['tabulatedUndulator']['length'] = 1.5
        data['models']['tabulatedUndulator']['horizontalAmplitude'] = 0
        data['models']['tabulatedUndulator']['horizontalInitialPhase'] = 0
        data['models']['tabulatedUndulator']['horizontalSymmetry'] = 1
        data['models']['tabulatedUndulator']['verticalAmplitude'] = 0.8
        data['models']['tabulatedUndulator']['verticalInitialPhase'] = 0
        data['models']['tabulatedUndulator']['verticalSymmetry'] = -1

    # Fixup electron beam parameters (drift, moments, etc.):
    data = fixup_electron_beam(data)

    if 'fluxAnimation' not in data['models']:
        data['models']['fluxAnimation'] = data['models']['fluxReport'].copy()
        data['models']['fluxAnimation']['photonEnergyPointCount'] = 1000
        data['models']['fluxAnimation']['initialEnergy'] = 10000.0
        data['models']['fluxAnimation']['finalEnergy'] = 20000.0
        data['models']['fluxAnimation']['method'] = 1
        data['models']['fluxAnimation']['precision'] = 0.01
        data['models']['fluxAnimation']['initialHarmonic'] = 1
        data['models']['fluxAnimation']['finalHarmonic'] = 15
    if 'numberOfMacroElectrons' not in data['models']['fluxReport']:  # added 08/09/2016 for ticket #188
        data['models']['fluxReport']['numberOfMacroElectrons'] = 1
    if 'numberOfMacroElectrons' not in data['models']['fluxAnimation']:  # added 08/09/2016 for ticket #188
        data['models']['fluxAnimation']['numberOfMacroElectrons'] = 100000
    for rep in ['undulator', 'tabulatedUndulator']:
        if 'undulatorParameter' not in data['models'][rep]:
            data['models'][rep]['undulatorParameter'] = round(_process_undulator_definition({
                'undulator_definition': 'B',
                'undulator_parameter': None,
                'vertical_amplitude': float(data['models'][rep]['verticalAmplitude']),
                'undulator_period': float(data['models'][rep]['period']) / 1000.0
            })['undulator_parameter'], 8)
    if 'folder' not in data['models']['simulation']:
        if data['models']['simulation']['name'] in _EXAMPLE_FOLDERS:
            data['models']['simulation']['folder'] = _EXAMPLE_FOLDERS[data['models']['simulation']['name']]
        else:
            data['models']['simulation']['folder'] = '/'

    # Trajectory report:
    if 'trajectoryReport' not in data['models']:
        data['models']['trajectoryReport'] = {
            'timeMomentEstimation': 'auto',
            'initialTimeMoment': 0.0,
            'finalTimeMoment': 0.0,
            'numberOfPoints': 10000,
            'plotAxis': 'x',
            'magneticField': 2,
        }
    # Update tabulated undulator length:
    data['models']['tabulatedUndulator'] = _compute_undulator_length(data['models']['tabulatedUndulator'])


def generate_parameters_file(data, schema, run_dir=None, run_async=False):
    # Process method and magnetic field values for intensity, flux and intensity distribution reports:
    # Intensity report:
    d = _process_intensity_reports(
        data['models']['simulation']['sourceType'],
        data['models']['tabulatedUndulator']['undulatorType']
    )
    rep = 'intensityReport'
    field = 'magneticField'
    data['models'][rep][field] = d[field]

    # Flux* reports:
    field = 'magneticField'
    for rep in ['fluxReport', 'fluxAnimation']:
        d = _process_flux_reports(
            data['models'][rep]['method'],
            rep,
            data['models']['simulation']['sourceType'],
            data['models']['tabulatedUndulator']['undulatorType']
        )
        data['models'][rep][field] = d[field]

    # Intensity Distribution (2D) report:
    d = _process_intensity_reports(
        data['models']['simulation']['sourceType'],
        data['models']['tabulatedUndulator']['undulatorType']
    )
    rep = 'sourceIntensityReport'
    field = 'magneticField'
    data['models'][rep][field] = d[field]

    if data['models']['simulation']['sourceType'] != 't' or data['models']['tabulatedUndulator']['undulatorType'] != 'u_t':
        data['models']['trajectoryReport']['magneticField'] = 1

    if 'report' in data:
        if data['report'] == 'fluxAnimation':
            data['models']['fluxReport'] = data['models'][data['report']].copy()
        elif re.search('watchpointReport', data['report']) or data['report'] == 'sourceIntensityReport':
            # render the watchpoint report settings in the initialIntensityReport template slot
            data['models']['initialIntensityReport'] = data['models'][data['report']].copy()

    if data['models']['simulation']['sourceType'] == 't':
        undulator_type = data['models']['tabulatedUndulator']['undulatorType']
        data['models']['undulator'] = data['models']['tabulatedUndulator'].copy()
        if undulator_type == 'u_i':
            data['models']['tabulatedUndulator']['gap'] = 0.0
            data['models']['tabulatedUndulator']['indexFile'] = ''

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

    if 'report' in data and data['report'] in data['models'] and 'distanceFromSource' in data['models'][data['report']]:
        position = data['models'][data['report']]['distanceFromSource']
    else:
        position = _get_first_element_position(data)
    v['beamlineFirstElementPosition'] = position

    # 1: auto-undulator 2: auto-wiggler
    v['energyCalculationMethod'] = 1 if data['models']['simulation']['sourceType'] in ['u', 't'] else 2

    v['userDefinedElectronBeam'] = 1
    if 'isReadOnly' in data['models']['electronBeam'] and data['models']['electronBeam']['isReadOnly']:
        v['userDefinedElectronBeam'] = 0
    if 'report' in data:
        v[data['report']] = 1
    return pkjinja.render_resource('srw.py', v)


def get_animation_name(data):
    return data['modelName']


def get_application_data(data):
    if data['method'] == 'compute_grazing_angle':
        return _compute_grazing_angle(data['optical_element'])
    elif data['method'] == 'compute_crl_characteristics':
        return _compute_crl_focus(_compute_crl_characteristics(data['optical_element'], data['photon_energy']))
    elif data['method'] == 'compute_fiber_characteristics':
        model = _compute_crl_characteristics(
            data['optical_element'],
            data['photon_energy'],
            prefix='external',
        )
        model = _compute_crl_characteristics(
            model,
            data['photon_energy'],
            prefix='core',
        )
        return model
    elif data['method'] == 'compute_crystal_init':
        return _compute_crystal_init(data['optical_element'])
    elif data['method'] == 'compute_crystal_orientation':
        return _compute_crystal_orientation(data['optical_element'])
    elif data['method'] == 'process_intensity_reports':
        return _process_intensity_reports(data['source_type'], data['undulator_type'])
    elif data['method'] == 'process_flux_reports':
        return _process_flux_reports(data['method_number'], data['report_name'], data['source_type'], data['undulator_type'])
    elif data['method'] == 'process_beam_parameters':
        return _process_beam_parameters(
            data['source_type'],
            data['undulator_type'],
            data['undulator_length'],
            data['undulator_period'],
            data['ebeam'],
        )
    elif data['method'] == 'compute_undulator_length':
        return _compute_undulator_length(data['report_model'])
    elif data['method'] == 'process_undulator_definition':
        return _process_undulator_definition(data)
    raise RuntimeError('unknown application data method: {}'.format(data['method']))


def get_data_file(run_dir, model, frame):
    filename = 'res_int_pr_se.dat' if 'watchpointReport' in model else _DATA_FILE_FOR_MODEL[model]
    with open(str(run_dir.join(filename))) as f:
        return filename, f.read(), 'application/octet-stream'
    raise RuntimeError('output file unknown for model: {}'.format(model))


def get_simulation_frame(run_dir, data, model_data):
    return extract_report_data(str(run_dir.join(_DATA_FILE_FOR_MODEL[data['report']])), data)


def import_file(request, lib_dir, tmp_dir):
    f = request.files['file']
    input_text = f.read()
    # attempt to decode the input as json first, if invalid try python
    try:
        data = json.loads(input_text)
        data['models']['simulation']['name'] += ' (imported)'
        return None, data
    except ValueError:
        pass
    arguments = str(request.form['arguments'])
    pkdp('{}: arguments={}', f.filename, arguments)
    return sirepo.importer.import_python(
        input_text,
        lib_dir=lib_dir,
        tmp_dir=tmp_dir,
        user_filename=f.filename,
        arguments=arguments,
    )


def models_related_to_report(data):
    """What models are required for this data['report']

    Args:
        data (dict): simulation
    Returns:
        list: Named models that affect report or [] if don't know
    """
    r = data['report']
    watchpoint = 'watchpointReport' in r
    if not (
        watchpoint
        or r in (
            'fluxReport', 'initialIntensityReport', 'intensityReport',
            'mirrorReport', 'powerDensityReport', 'sourceIntensityReport',
            'trajectoryReport',
        )
    ):
        return []
    res = [
        'electronBeam', 'gaussianBeam', 'multipole', 'simulation',
        'tabulatedUndulator', 'undulator',
    ]
    if watchpoint or r == 'mirrorReport':
        res.append('beamline')
        if watchpoint:
            res.extend(['postPropagation', 'propagation'])
    return res


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
    for f in _PREDEFINED_MAGNETIC_ZIP_FILES:
        if filename == f['fileName'] and not filepath.check():
            _STATIC_FOLDER.join('dat', f['fileName']).copy(run_dir)
    zip_file = zipfile.ZipFile(str(filepath))
    zip_file.extractall(str(run_dir))
    index_dir, index_file = _find_index_file(zip_file)
    if not index_dir:
        index_dir = './'
    data['models']['tabulatedUndulator']['magnMeasFolder'] = index_dir
    data['models']['tabulatedUndulator']['indexFile'] = index_file


def prepare_for_client(data):
    return data


def remove_last_frame(run_dir):
    pass


def run_all_text(data):
    """TODO(mrakitin): the code is duplicated from sirepo/pkcli/srw.py, need to invent something universal."""
    content = [
        'v = srwl_bl.srwl_uti_parse_options(varParam)',
        'source_type, mag = srwl_bl.setup_source(v)',
        'op = None'
    ]
    if 'report' not in data or data['report'] == 'intensityReport':
        content.append('v.ss = True')
        content.append("v.ss_pl = 'e'")
    elif data['report'] in ['fluxReport', 'fluxAnimation']:
        content.append('v.sm = True')
        content.append("v.sm_pl = 'e'")
    elif data['report'] == 'powerDensityReport':
        content.append('v.pw = True')
        content.append("v.pw_pl = 'xy'")
    elif data['report'] == 'initialIntensityReport' or data['report'] == 'sourceIntensityReport':
        content.append('v.si = True')
        content.append("v.si_pl = 'xy'")
    elif data['report'] == 'trajectoryReport':
        content.append('v.tr = True')
        content.append("v.tr_pl = 'xxpyypz'")
    elif data['report'] == 'mirrorReport':
        pass
    elif re.search('^watchpointReport', data['report']):
        content.append('op = set_optics()')
        content.append('v.ws = True')
        content.append("v.ws_pl = 'xy'")
    elif data['report'] == 'multiElectronAnimation':
        content.append('v.wm = True')
    else:
        raise Exception('unknown report: {}'.format(data['report']))
    content.append('srwl_bl.SRWLBeamline(_name=v.name, _mag_approx=mag).calc_all(v, op)')

    text = """

def main():
{}


if __name__ == '__main__':
    main()
""".format('\n'.join(['{}{}'.format('    ', x) for x in content]))
    return text


def static_lib_files():
    """Library shared between simulations of this type

    Returns:
        list: py.path.local objects
    """
    res = [_STATIC_FOLDER.join('dat', m['fileName']) for m in _PREDEFINED_MIRRORS]
    res += [_STATIC_FOLDER.join('dat', m['fileName']) for m in _PREDEFINED_MAGNETIC_ZIP_FILES]
    return res


def validate_file(file_type, path):
    """Ensure the data file contains parseable rows data"""
    match = re.search(r'\.(\w+)$', str(path))
    extension = None
    if match:
        extension = match.group(1).lower()
    else:
        return 'invalid file extension'

    if extension == 'dat':
        # mirror file
        try:
            count = 0
            with open(str(path)) as f:
                for line in f.readlines():
                    parts = line.split("\t")
                    if len(parts) > 0:
                        float(parts[0])
                    if len(parts) > 1:
                        float(parts[1])
                        count += 1
            if count == 0:
                return 'no data rows found in file'
        except ValueError as e:
            return 'invalid file format: {}'.format(e)
    elif extension == 'zip':
        # undulator magnetic data file
        #TODO(pjm): add additional zip file validation
        zip_file = zipfile.ZipFile(str(path))
        is_valid = False
        for f in zip_file.namelist():
            if re.search('\.txt', f.lower()):
                is_valid = True
                break
        if not is_valid:
            return 'zip file missing txt index file'
    else:
        return 'invalid file type: {}'.format(extension)
    return None


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


def _beamline_element(template, item, fields, propagation, shift=''):
    return '{}    el.append({})'.format(
        shift,
        template.format(*map(lambda x: item[x], fields))
    ), _propagation_params(propagation[str(item['id'])][0], shift)


def _compute_crl_characteristics(model, photon_energy, prefix=''):
    fields_with_prefix = {
        'material': 'material',
        'refractiveIndex': 'refractiveIndex',
        'attenuationLength': 'attenuationLength',
    }
    if prefix:
        for k in fields_with_prefix.keys():
            fields_with_prefix[k] = '{}{}{}'.format(
                prefix,
                fields_with_prefix[k][0].upper(),
                fields_with_prefix[k][1:],
            )

    if model[fields_with_prefix['material']] == 'User-defined':
        return model

    # Index of refraction:
    kwargs = {
        'energy': photon_energy,
    }
    if model['method'] == 'server':
        kwargs['precise'] = True
        kwargs['formula'] = model[fields_with_prefix['material']]
    elif model['method'] == 'file':
        kwargs['precise'] = True
        kwargs['data_file'] = '{}_delta.dat'.format(model[fields_with_prefix['material']])
    else:
        kwargs['calc_delta'] = True
        kwargs['formula'] = model[fields_with_prefix['material']]
    delta = bnlcrl.pkcli.simulate.find_delta(**kwargs)
    model[fields_with_prefix['refractiveIndex']] = delta['characteristic_value']

    # Attenuation length:
    kwargs['characteristic'] = 'atten'
    if model['method'] == 'file':
        kwargs['precise'] = True
        kwargs['data_file'] = '{}_atten.dat'.format(model[fields_with_prefix['material']])
    if model['method'] == 'calculation':
        # The method 'calculation' in bnlcrl library is not supported yet for attenuation length calculation.
        pass
    else:
        atten = bnlcrl.pkcli.simulate.find_delta(**kwargs)
        model[fields_with_prefix['attenuationLength']] = atten['characteristic_value']

    return model


def _compute_crl_focus(model):
    d = bnlcrl.pkcli.simulate.calc_ideal_focus(
        radius=model['radius'],
        n=model['numberOfLenses'],
        delta=model['refractiveIndex'],
        p0=model['position']
    )
    model['focalDistance'] = d['ideal_focus']
    model['absoluteFocusPosition'] = d['p1_ideal_from_source']
    return model


def _compute_crystal_init(model):
    parms_list = ['dSpacing', 'psi0r', 'psi0i', 'psiHr', 'psiHi', 'psiHBr', 'psiHBi', 'grazingAngle']
    try:
        material_raw = model['material']  # name contains either "(SRW)" or "(X0h)"
        material = material_raw.split()[0]  # short name for SRW (e.g., Si), long name for X0h (e.g., Silicon)
        h = int(model['h'])
        k = int(model['k'])
        l = int(model['l'])
        millerIndices = [h, k, l]
        energy = model['energy']
        grazingAngle = None
        if re.search('(X0h)', material_raw):
            crystal_parameters = crystal.get_crystal_parameters(material, energy, h, k, l)
            dc = crystal_parameters['d']
            xr0 = crystal_parameters['xr0']
            xi0 = crystal_parameters['xi0']
            xrh = crystal_parameters['xrh']
            xih = crystal_parameters['xih']
        elif re.search('(SRW)', material_raw):
            dc = srwl_uti_cryst_pl_sp(millerIndices, material)
            xr0, xi0, xrh, xih = srwl_uti_cryst_pol_f(energy, millerIndices, material)
        else:
            dc = xr0 = xi0 = xrh = xih = None

        if dc:
            angles_data = crystal.calc_bragg_angle(d=dc, energy_eV=energy, n=1)
            grazingAngle = angles_data['bragg_angle']
        model['dSpacing'] = dc
        model['psi0r'] = xr0
        model['psi0i'] = xi0
        model['psiHr'] = xrh
        model['psiHi'] = xih
        model['psiHBr'] = xrh
        model['psiHBi'] = xih
        model['grazingAngle'] = grazingAngle
    except Exception:
        pkdp('{}: error: {}', material_raw, pkdexc())
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


def _compute_undulator_length(model):
    zip_file = simulation_db.simulation_lib_dir('srw').join(model['magneticFile'])
    if zip_file.check():
        zip_file = str(zip_file)
        d = find_tab_undulator_length(zip_file, model['gap'])
        model['length'] = d['found_length']
    return model


def _convert_ebeam_units(field_name, value, to_si=True):
    """Convert values from the schema to SI units (m, rad) and back.

    Args:
        field_name: name of the field in _SCHEMA['model']['electronBeam'].
        value: value of the field.
        to_si: if set to True, convert to SI units, otherwise convert back to the units in the schema.

    Returns:
        value: converted value.
    """
    if field_name in _SCHEMA['model']['electronBeam'].keys():
        label, field_type = _SCHEMA['model']['electronBeam'][field_name]
        if field_type == 'Float':
            if re.search('\[m(m|rad)\]', label):
                value *= _invert_value(1e3, to_si)
            elif re.search('\[\xb5(m|rad)\]', label):  # mu
                value *= _invert_value(1e6, to_si)
            elif re.search('\[n(m|rad)\]', label):
                value *= _invert_value(1e9, to_si)
    return value


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
    el.append(opCr)\n'''.format(
        template.format(*map(lambda x: item[x], fields)),
        item['nvx'], item['nvy'], item['nvz'], item['tvx'], item['tvy']
    )
    return res, _propagation_params(propagation[str(item['id'])][0])


def _find_closest_value(values_list, value):
    """Find closest value to the specified input.

    Args:
        values_list: a list of float values.
        value: a value for which the closest value should be found.

    Returns:
        dict: dictionary with the index of the found value (``idx``) and the closest value (``closest_value``).
    """
    assert type(value) is float
    indices_previous = []
    indices_next = []
    for i in range(len(values_list)):
        if values_list[i] <= value:
            indices_previous.append(i)
        else:
            indices_next.append(i)

    assert indices_previous or indices_next
    idx_previous = indices_previous[-1] if indices_previous else indices_next[0]
    idx_next = indices_next[0] if indices_next else indices_previous[-1]

    idx = idx_previous if abs(values_list[idx_previous] - value) <= abs(values_list[idx_next] - value) else idx_next
    return {
        'idx': idx,
        'closest_value': values_list[idx],
    }


def _find_index_file(zip_object):
    """The function finds an index file (``*.txt``) in the provided zip-object.

    Args:
        zip_object: an object created by ``zipfile.ZipFile()``.

    Returns:
        index_dir (str): found dir of the index file.
        index_file (str): found index file (e.g., ``ivu21_srx_sum.txt``).
    """
    index_file = None
    index_dir = None
    for f in zip_object.namelist():
        if re.search('\.txt', f):
            index_file = os.path.basename(f)
            index_dir = os.path.dirname(f)
            break
    assert index_file is not None
    return index_dir, index_file


def _generate_beamline_optics(models, last_id):
    beamline = models['beamline']
    propagation = models['propagation']
    res_el = 'el = []\n'
    res_pp = '    pp = []\n'

    prev = None
    has_item = False
    last_element = False
    want_final_propagation = True

    height_profile_counter = 1
    for item in beamline:
        if last_element:
            want_final_propagation = False
            break
        if prev:
            has_item = True
            size = item['position'] - prev['position']
            if size != 0:
                res_el += '    el.append(srwlib.SRWLOptD({}))\n'.format(size)
                res_pp += _propagation_params(propagation[str(prev['id'])][1])
        if item['type'] == 'aperture':
            el, pp = _beamline_element(
                'srwlib.SRWLOptA("{}", "a", {}, {}, {}, {})',
                item,
                ['shape', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
                propagation)
            res_el += el
            res_pp += pp
        elif item['type'] == 'crl':
            el, pp = _beamline_element(
                'srwlib.srwl_opt_setup_CRL({}, {}, {}, {}, {}, {}, {}, {}, {}, 0, 0)',
                item,
                ['focalPlane', 'refractiveIndex', 'attenuationLength', 'shape', 'horizontalApertureSize', 'verticalApertureSize', 'radius', 'numberOfLenses', 'wallThickness'],
                propagation)
            res_el += el
            res_pp += pp
        elif item['type'] == 'crystal':
            el, pp = _crystal_element(
                'srwlib.SRWLOptCryst(_d_sp={}, _psi0r={}, _psi0i={}, _psi_hr={}, _psi_hi={}, _psi_hbr={}, _psi_hbi={}, _tc={}, _ang_as={})',
                item,
                ['dSpacing', 'psi0r', 'psi0i', 'psiHr', 'psiHi', 'psiHBr', 'psiHBi', 'crystalThickness', 'asymmetryAngle'],
                propagation)
            res_el += el
            res_pp += pp

            el, pp = _height_profile_element(
                item,
                propagation,
                overwrite_propagation=True,
                height_profile_el_name='Cryst{}'.format(height_profile_counter)
            )
            if pp:
                height_profile_counter += 1
            res_el += el
            res_pp += pp
        elif item['type'] == 'ellipsoidMirror':
            el, pp = _beamline_element(
                'srwlib.SRWLOptMirEl(_p={}, _q={}, _ang_graz={}, _size_tang={}, _size_sag={}, _nvx={}, _nvy={}, _nvz={}, _tvx={}, _tvy={})',
                item,
                ['firstFocusLength', 'focalLength', 'grazingAngle', 'tangentialSize', 'sagittalSize', 'normalVectorX', 'normalVectorY', 'normalVectorZ', 'tangentialVectorX', 'tangentialVectorY'],
                propagation)
            res_el += el
            res_pp += pp

            el, pp = _height_profile_element(
                item,
                propagation,
                overwrite_propagation=True,
                height_profile_el_name='ElMirror{}'.format(height_profile_counter)
            )
            if pp:
                height_profile_counter += 1
            res_el += el
            res_pp += pp
        elif item['type'] == 'fiber':
            el, pp = _beamline_element(
                'srwlib.srwl_opt_setup_cyl_fiber(_foc_plane={}, _delta_ext={}, _delta_core={}, _atten_len_ext={}, _atten_len_core={}, _diam_ext={}, _diam_core={}, _xc={}, _yc={})',
                item,
                ['focalPlane', 'externalRefractiveIndex', 'coreRefractiveIndex', 'externalAttenuationLength', 'coreAttenuationLength', 'externalDiameter', 'coreDiameter', 'horizontalCenterPosition', 'verticalCenterPosition'],
                propagation)
            res_el += el
            res_pp += pp
        elif item['type'] == 'grating':
            el, pp = _beamline_element(
                'srwlib.SRWLOptG(_mirSub=srwlib.SRWLOptMirPl(_size_tang={}, _size_sag={}, _nvx={}, _nvy={}, _nvz={}, _tvx={}, _tvy={}), _m={}, _grDen={}, _grDen1={}, _grDen2={}, _grDen3={}, _grDen4={})',
                item,
                ['tangentialSize', 'sagittalSize', 'normalVectorX', 'normalVectorY', 'normalVectorZ', 'tangentialVectorX', 'tangentialVectorY', 'diffractionOrder', 'grooveDensity0', 'grooveDensity1', 'grooveDensity2', 'grooveDensity3', 'grooveDensity4'],
                propagation)
            res_el += el
            res_pp += pp
        elif item['type'] == 'lens':
            el, pp = _beamline_element(
                'srwlib.SRWLOptL({}, {}, {}, {})',
                item,
                ['horizontalFocalLength', 'verticalFocalLength', 'horizontalOffset', 'verticalOffset'],
                propagation)
            res_el += el
            res_pp += pp
        elif item['type'] == 'mirror':
            el, pp = _height_profile_element(
                item,
                propagation,
                height_profile_el_name='Mirror{}'.format(height_profile_counter)
            )
            if pp:
                height_profile_counter += 1
            res_el += el
            res_pp += pp
        elif item['type'] == 'obstacle':
            el, pp = _beamline_element(
                'srwlib.SRWLOptA("{}", "o", {}, {}, {}, {})',
                item,
                ['shape', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
                propagation)
            res_el += el
            res_pp += pp
        elif item['type'] == 'sphericalMirror':
            el, pp = _beamline_element(
                'srwlib.SRWLOptMirSph(_r={}, _size_tang={}, _size_sag={}, _nvx={}, _nvy={}, _nvz={}, _tvx={}, _tvy={})',
                item,
                ['radius', 'tangentialSize', 'sagittalSize', 'normalVectorX', 'normalVectorY', 'normalVectorZ', 'tangentialVectorX', 'tangentialVectorY'],
                propagation)
            res_el += el
            res_pp += pp

            el, pp = _height_profile_element(
                item,
                propagation,
                overwrite_propagation=True,
                height_profile_el_name='SphMirror{}'.format(height_profile_counter)
            )
            if pp:
                height_profile_counter += 1
            res_el += el
            res_pp += pp
        elif item['type'] == 'watch':
            if not has_item:
                res_el += '    el.append(srwlib.SRWLOptD({}))\n'.format(1.0e-16)
                res_pp += _propagation_params(propagation[str(item['id'])][0])
            if last_id and last_id == int(item['id']):
                last_element = True
        prev = item
        res_el += '\n'
        res_pp += '\n'

    # final propagation parameters
    if want_final_propagation:
        res_pp += _propagation_params(models['postPropagation'])

    res = res_el + res_pp + '\n    return srwlib.SRWLOptC(el, pp)\n'
    return res


def _get_first_element_position(data):
    beamline = data['models']['beamline']
    if len(beamline):
        return beamline[0]['position']
    return 20


def _height_profile_element(item, propagation, overwrite_propagation=False, height_profile_el_name='Mirror'):
    shift = '    '
    if overwrite_propagation:
        if item['heightProfileFile'] and item['heightProfileFile'] != 'None':
            propagation[str(item['id'])][0] = [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0]
        else:
            return '', ''
    res = '\n{}ifn{} = "{}"\n'.format(shift, height_profile_el_name, item['heightProfileFile'])
    res += '{}if ifn{}:\n'.format(shift, height_profile_el_name)
    add_args = ', 0, 1' if int(item['heightProfileDimension']) == 1 else ''
    res += '{}    hProfData{} = srwlib.srwl_uti_read_data_cols(ifn{}, "\\t"{})\n'.format(shift, height_profile_el_name, height_profile_el_name, add_args)
    fields = ['orientation', 'grazingAngle', 'heightAmplification']
    hProfData = 'hProfData{}'.format(height_profile_el_name)
    surf_height_func = 'srwlib.srwl_opt_setup_surf_height_{}d'.format(item['heightProfileDimension'])
    if 'horizontalTransverseSize' in item:
        template = surf_height_func + '(' + hProfData + ', _dim="{}", _ang={}, _amp_coef={}, _size_x={}, _size_y={})'
        fields.extend(('horizontalTransverseSize', 'verticalTransverseSize'))
    else:
        template = surf_height_func + '(' + hProfData + ', _dim="{}", _ang={}, _amp_coef={})'
    el, pp = _beamline_element(template, item, fields, propagation, shift=shift)
    res += el
    pp = '{}if ifn{}:\n{}'.format(shift, height_profile_el_name, pp)
    return res, pp


def _intensity_units(is_gaussian, model_data):
    if is_gaussian:
        if 'report' in model_data and 'fieldUnits' in model_data['models'][model_data['report']]:
            i = model_data['models'][model_data['report']]['fieldUnits']
        else:
            i = model_data['models']['initialIntensityReport']['fieldUnits']
        return _SCHEMA['enum']['FieldUnits'][int(i)][1]
    return 'ph/s/.1%bw/mm^2'


def _invert_value(value, invert=False):
    """Invert specified value - 1 / value."""
    if invert:
        value **= (-1)
    return value


def _process_beam_drift(source_type, undulator_type, undulator_length, undulator_period):
    """Calculate drift for ideal undulator."""
    drift = 0.0
    if source_type == 'u' or (source_type == 't' and undulator_type == 'u_i'):
        # initial drift = 1/2 undulator length + 2 periods
        drift = -0.5 * float(undulator_length) - 2 * float(undulator_period)
    return drift


def _process_beam_parameters(source_type, undulator_type, undulator_length, undulator_period, ebeam):
    if 'drift' not in ebeam or 'driftCalculationMethod' not in ebeam or ebeam['driftCalculationMethod'] == 'auto':
        drift = _process_beam_drift(source_type, undulator_type, undulator_length, undulator_period)
    else:
        drift = ebeam['drift']
    model = {
        'drift': drift,
    }

    moments_fields = ['rmsSizeX', 'xxprX', 'rmsDivergX', 'rmsSizeY', 'xxprY', 'rmsDivergY']
    for k in moments_fields:
        model[k] = ebeam[k] if k in ebeam else 0

    if 'beamDefinition' not in ebeam or ebeam['beamDefinition'] == 't':  # Twiss
        import copy
        ebeam = copy.deepcopy(ebeam)

        # Convert to SI units to perform SRW calculation:
        for k in ebeam:
            ebeam[k] = _convert_ebeam_units(k, ebeam[k])

        import srwlib
        beam = srwlib.SRWLPartBeam()
        beam.from_Twiss(
            _e=ebeam['energy'],
            _sig_e=ebeam['rmsSpread'],
            _emit_x=ebeam['horizontalEmittance'],
            _beta_x=ebeam['horizontalBeta'],
            _alpha_x=ebeam['horizontalAlpha'],
            _eta_x=ebeam['horizontalDispersion'],
            _eta_x_pr=ebeam['horizontalDispersionDerivative'],
            _emit_y=ebeam['verticalEmittance'],
            _beta_y=ebeam['verticalBeta'],
            _alpha_y=ebeam['verticalAlpha'],
            _eta_y=ebeam['verticalDispersion'],
            _eta_y_pr=ebeam['verticalDispersionDerivative'],
        )

        for i, k in enumerate(moments_fields):
            model[k] = beam.arStatMom2[i] if k in ['xxprX', 'xxprY'] else beam.arStatMom2[i] ** 0.5

        # Convert to the units used in the schema:
        for k in model.keys():
            model[k] = _convert_ebeam_units(k, model[k], to_si=False)

    return model


def _process_flux_reports(method_number, report_name, source_type, undulator_type):
    # Magnetic field processing:
    magnetic_field = 1
    if source_type == 't' and undulator_type == 'u_t' and report_name == 'fluxAnimation' and (int(method_number) in [1, 2]):
        magnetic_field = 2

    return {'magneticField': magnetic_field}


def _process_intensity_reports(source_type, undulator_type):
    # Magnetic field processing:
    magnetic_field = 2 if source_type == 't' and undulator_type == 'u_t' else 1
    return {'magneticField': magnetic_field}


def _process_undulator_definition(model):
    """Convert K -> B and B -> K."""
    from srwlib import SRWLMagFldH, SRWLMagFldU
    try:
        if model['undulator_definition'] == 'B':
            # Convert B -> K:
            und = SRWLMagFldU([SRWLMagFldH(1, 'v', float(model['vertical_amplitude']), 0, 1)], float(model['undulator_period']))
            model['undulator_parameter'] = und.get_K()
        elif model['undulator_definition'] == 'K':
            # Convert K to B:
            und = SRWLMagFldU([], float(model['undulator_period']))
            model['vertical_amplitude'] = und.K_2_B(float(model['undulator_parameter']))
        return model
    except:
        return model


def _propagation_params(prop, shift=''):
    return '{}    pp.append([{}])\n'.format(shift, ', '.join([str(x) for x in prop]))


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
