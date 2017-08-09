# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from scipy.ndimage import zoom
from sirepo import crystal
from sirepo import simulation_db
from sirepo.template import srw_importer
from sirepo.template import template_common
from srwl_uti_cryst import srwl_uti_cryst_pl_sp, srwl_uti_cryst_pol_f
from srwlib import SRWLMagFldH, SRWLMagFldU
import bnlcrl.pkcli.simulate
import copy
import glob
import json
import math
import numpy as np
import os
import py.path
import re
import srwl_uti_smp
import srwl_uti_src
import srwlib
import traceback
import uti_math
import uti_plot_com
import zipfile


WANT_BROWSER_FRAME_CACHE = False

#: Simulation type
SIM_TYPE = 'srw'

_WATCHPOINT_REPORT_NAME = 'watchpointReport'

_DATA_FILE_FOR_MODEL = pkcollections.Dict({
    'fluxAnimation': {'filename': 'res_spec_me.dat', 'dimension': 2},
    'fluxReport': {'filename': 'res_spec_me.dat', 'dimension': 2},
    'initialIntensityReport': {'filename': 'res_int_se.dat', 'dimension': 3},
    'intensityReport': {'filename': 'res_spec_se.dat', 'dimension': 2},
    'mirrorReport': {'filename': '', 'dimension': 3},
    'multiElectronAnimation': {'filename': 'res_int_pr_me.dat', 'dimension': 3},
    'powerDensityReport': {'filename': 'res_pow.dat', 'dimension': 3},
    'sourceIntensityReport': {'filename': 'res_int_se.dat', 'dimension': 3},
    'trajectoryReport': {'filename': 'res_trj.dat', 'dimension': 2},
    _WATCHPOINT_REPORT_NAME: {'filename': 'res_int_pr_se.dat', 'dimension': 3},
})

_EXAMPLE_FOLDERS = pkcollections.Dict({
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
})

#: Where server files and static files are found
_RESOURCE_DIR = template_common.resource_dir(SIM_TYPE)

_PREDEFINED = None

_REPORT_STYLE_FIELDS = ['intensityPlotsWidth', 'intensityPlotsScale']

_RUN_ALL_MODEL = 'simulation'

_SCHEMA = simulation_db.get_schema(SIM_TYPE)

_USER_MODEL_LIST_FILENAME = pkcollections.Dict({
    'electronBeam': '_user_beam_list.json',
    'tabulatedUndulator': '_user_undulator_list.json',
})


class MagnMeasZip:
    def __init__(self, archive_name):
        """The class for convenient operation with an archive with the magnetic measurements.

        Args:
            archive_name: the name of the archive.
        """
        self.archive_name = archive_name
        self.z = zipfile.ZipFile(archive_name)
        self.index_dir = None
        self.index_file = None
        self.index_content = None
        self.gaps = None
        self.dat_files = None

        # .dat file from the index file (depends on the provided gap):
        self.idx = None
        self.closest_gap = None
        self.dat_file = None

        # .dat file information:
        self.dat_file_step = None
        self.dat_file_number_of_points = None
        self.dat_file_found_length = None

        self._find_index_file()
        self._find_dat_files_from_index_file()

    def find_closest_gap(self, gap):
        d = _find_closest_value(self.gaps, float(gap))
        self.idx = d['idx']
        self.closest_gap = d['closest_value']
        self.dat_file = self.dat_files[self.idx]
        self._get_gap_parameters(self.get_file_content(self.dat_file))

    def get_file_content(self, file_name):
        with self.z.open(self._full_path(file_name)) as f:
            return _normalize_eol(f)

    def save_file(self, run_dir, file_name, content):
        with open(self._full_path(file_name, run_dir), 'w') as f:
            f.write('\n'.join(content) + '\n')

    def _find_dat_files_from_index_file(self):
        self.gaps, self.dat_files = _find_dat_files_from_index_file(self.index_content)

    def _find_index_file(self):
        self.index_dir, self.index_file = _find_index_file(self.z)
        self.index_content = self.get_file_content(self.index_file)

    def _full_path(self, file_name, run_dir=None):
        if not run_dir:
            return os.path.join(self.index_dir, file_name)
        abs_dir = os.path.join(run_dir, self.index_dir)
        abs_dir = os.path.abspath(abs_dir)
        if not os.path.isdir(abs_dir):
            os.mkdir(abs_dir)
        return os.path.join(abs_dir, file_name)

    def _get_gap_parameters(self, dat_content):
        self.dat_file_step = float(dat_content[8].split('#')[1].strip())
        self.dat_file_number_of_points = int(dat_content[9].split('#')[1].strip())
        self.dat_file_found_length = round(self.dat_file_step * self.dat_file_number_of_points, 6)


def background_percent_complete(report, run_dir, is_running, schema):
    res = pkcollections.Dict({
        'percentComplete': 0,
        'frameCount': 0,
    })
    filename = run_dir.join(get_filename_for_model(report))
    if filename.exists():
        status = pkcollections.Dict({
            'progress': 100,
            'particle_number': 0,
            'total_num_of_particles': 0,
        })
        status_files = pkio.sorted_glob(run_dir.join('__srwl_logs__', 'srwl_*.json'))
        if status_files:  # Read the status file if SRW produces the multi-e logs
            progress_file = py.path.local(status_files[-1])
            if progress_file.exists():
                status = simulation_db.read_json(progress_file)
        t = int(filename.mtime())
        res.update({
            'frameCount': 1,
            'frameId': t,
            'lastUpdateTime': t,
            'percentComplete': status['progress'],
            'particleNumber': status['particle_number'],
            'particleCount': status['total_num_of_particles'],
        })
    return res


def copy_related_files(data, source_path, target_path):
    _copy_lib_files(
        data,
        py.path.local(os.path.dirname(source_path)).join('lib'),
        py.path.local(os.path.dirname(target_path)).join('lib'),
    )


def extensions_for_file_type(file_type):
    if file_type == 'mirror':
        return ['*.dat', '*.txt']
    if file_type == 'sample':
        return ['*.tif', '*.tiff', '*.TIF', '*.TIFF', '*.npy', '*.NPY']
    if file_type == 'undulatorTable':
        return ['*.zip']
    raise RuntimeError('unknown file_type: ', file_type)


def extract_report_data(filename, model_data):
    flux_type = 1
    if 'report' in model_data and model_data['report'] in ['fluxReport', 'fluxAnimation']:
        flux_type = int(model_data['models'][model_data['report']]['fluxType'])
    sValShort = 'Flux'; sValType = 'Flux through Finite Aperture'; sValUnit = 'ph/s/.1%bw'
    if flux_type == 2:
        sValShort = 'Intensity'
        sValUnit = 'ph/s/.1%bw/mm^2'
    is_gaussian = False
    if 'models' in model_data and _is_gaussian_source(model_data['models']['simulation']):
        is_gaussian = True
    #TODO(pjm): move filename and metadata to a constant, using _DATA_FILE_FOR_MODEL
    if model_data['report'] == 'initialIntensityReport':
        before_propagation_name = 'Before Propagation (E={photonEnergy} eV)'
    elif model_data['report'] == 'sourceIntensityReport':
        before_propagation_name = 'E={sourcePhotonEnergy} eV'
    else:
        before_propagation_name = 'E={photonEnergy} eV'
    file_info = pkcollections.Dict({
        'res_trj.dat': [['Longitudinal Position', 'Position', 'Electron Trajectory'], ['m', 'm']],
        'res_spec_se.dat': [['Photon Energy', 'Intensity', 'On-Axis Spectrum from Filament Electron Beam'], ['eV', _intensity_units(is_gaussian, model_data)]],
        'res_spec_me.dat': [['Photon Energy', sValShort, sValType], ['eV', sValUnit]],
        'res_pow.dat': [['Horizontal Position', 'Vertical Position', 'Power Density', 'Power Density'], ['m', 'm', 'W/mm^2']],
        'res_int_se.dat': [['Horizontal Position', 'Vertical Position', before_propagation_name, 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        #TODO(pjm): improve multi-electron label
        'res_int_pr_me.dat': [['Horizontal Position', 'Vertical Position', before_propagation_name, 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        'res_int_pr_se.dat': [['Horizontal Position', 'Vertical Position', 'After Propagation (E={photonEnergy} eV)', 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        'res_mirror.dat': [['Horizontal Position', 'Vertical Position', 'Optical Path Difference', 'Optical Path Difference'], ['m', 'm', 'm']],
    })

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
    elif '{sourcePhotonEnergy}' in title:
        title = title.format(sourcePhotonEnergy=model_data['models']['sourceIntensityReport']['photonEnergy'])
    info = pkcollections.Dict({
        'title': title,
        'x_range': [allrange[0], allrange[1]],
        'y_label': _superscript(file_info[filename][0][1] + ' [' + file_info[filename][1][1] + ']'),
        'x_label': file_info[filename][0][0] + ' [' + file_info[filename][1][0] + ']',
        'x_units': file_info[filename][1][0],
        'y_units': file_info[filename][1][1],
        'points': data,
    })
    orig_rep_name = model_data['report']
    rep_name = _WATCHPOINT_REPORT_NAME if template_common.is_watchpoint(orig_rep_name) else orig_rep_name
    if _DATA_FILE_FOR_MODEL[rep_name]['dimension'] == 3:
        width_pixels = int(model_data['models'][orig_rep_name]['intensityPlotsWidth'])
        scale = model_data['models'][orig_rep_name]['intensityPlotsScale']
        info = _remap_3d(info, allrange, file_info[filename][0][3], file_info[filename][1][2], width_pixels, scale)
    return info


def find_height_profile_dimension(dat_file):
    """Find the dimension of the provided height profile .dat file.
    1D files have 2 columns, 2D - 8 columns.

    Args:
        dat_file (str): full path to height profile .dat file.

    Returns:
        dimension (int): found dimension.
    """
    with open(dat_file, 'r') as f:
        header = f.readline().strip().split()
        dimension = 1 if len(header) == 2 else 2
    return dimension


def fixup_electron_beam(data):
    if 'electronBeamPosition' not in data['models']:
        ebeam = data['models']['electronBeam']
        data['models']['electronBeamPosition'] = pkcollections.Dict({
            'horizontalPosition': ebeam['horizontalPosition'],
            'verticalPosition': ebeam['verticalPosition'],
            'driftCalculationMethod': ebeam['driftCalculationMethod'] if 'driftCalculationMethod' in ebeam else 'auto',
            'drift': ebeam['drift'] if 'drift' in ebeam else 0,
        })
        for f in ('horizontalPosition', 'verticalPosition', 'driftCalculationMethod', 'drift'):
            if f in ebeam:
                del ebeam[f]
    if 'horizontalAngle' not in data['models']['electronBeamPosition']:
        data['models']['electronBeamPosition']['horizontalAngle'] = _SCHEMA['model']['electronBeamPosition']['horizontalAngle'][2]
        data['models']['electronBeamPosition']['verticalAngle'] = _SCHEMA['model']['electronBeamPosition']['verticalAngle'][2]
    if 'beamDefinition' not in data['models']['electronBeam']:
        _process_beam_parameters(data['models']['electronBeam'])
        data['models']['electronBeamPosition']['drift'] = _calculate_beam_drift(
            data['models']['electronBeamPosition'],
            data['models']['simulation']['sourceType'],
            data['models']['tabulatedUndulator']['undulatorType'],
            float(data['models']['undulator']['length']),
            float(data['models']['undulator']['period']) / 1000.0,
        )
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
                if k == 'sourceIntensityReport' or k == 'initialIntensityReport' or template_common.is_watchpoint(k):
                    del data['models'][k]['sampleFactor']
    if data['models']['fluxReport']:
        data['models']['fluxReport']['method'] = -1  # always approximate for static Flux Report
        data['models']['fluxReport']['precision'] = 0.01  # is not used in static Flux Report
        if 'initialHarmonic' not in data['models']['fluxReport']:
            data['models']['fluxReport']['initialHarmonic'] = 1
            data['models']['fluxReport']['finalHarmonic'] = 15
        if 'magneticField' not in data['models']['fluxReport']:
            data['models']['fluxReport']['magneticField'] = 1
    if 'fluxAnimation' in data['models']:
        if 'method' not in data['models']['fluxAnimation']:
            data['models']['fluxAnimation']['method'] = 1
            data['models']['fluxAnimation']['precision'] = 0.01
            data['models']['fluxAnimation']['initialHarmonic'] = 1
            data['models']['fluxAnimation']['finalHarmonic'] = 15
        if 'magneticField' not in data['models']['fluxAnimation']:
            data['models']['fluxAnimation']['magneticField'] = 1
    if data['models']['intensityReport']:
        if 'method' not in data['models']['intensityReport']:
            if _is_undulator_source(data['models']['simulation']):
                data['models']['intensityReport']['method'] = 1
            elif _is_dipole_source(data['models']['simulation']):
                data['models']['intensityReport']['method'] = 2
            else:
                data['models']['intensityReport']['method'] = 0
            data['models']['intensityReport']['precision'] = 0.01
            data['models']['intensityReport']['fieldUnits'] = 1
    if 'sourceIntensityReport' in data['models']:
        if 'precision' not in data['models']['sourceIntensityReport']:
            data['models']['sourceIntensityReport']['precision'] = 0.01
    if 'simulationStatus' not in data['models'] or 'state' in data['models']['simulationStatus']:
        data['models']['simulationStatus'] = pkcollections.Dict()
    if 'outOfSessionSimulationId' not in data['models']['simulation']:
        data['models']['simulation']['outOfSessionSimulationId'] = ''
    if 'multiElectronAnimation' not in data['models']:
        m = data['models']['initialIntensityReport']
        data['models']['multiElectronAnimation'] = pkcollections.Dict({
            'horizontalPosition': m['horizontalPosition'],
            'horizontalRange': m['horizontalRange'],
            'verticalPosition': m['verticalPosition'],
            'verticalRange': m['verticalRange'],
            'stokesParameter': '0',
        })
    if 'numberOfMacroElectrons' not in data['models']['multiElectronAnimation']:  # added 08/10/2016 for ticket #278
        data['models']['multiElectronAnimation']['numberOfMacroElectrons'] = 100000
    if 'photonEnergyBandWidth' not in data['models']['multiElectronAnimation']:  # added 03/29/2017 for ticket #708
        data['models']['multiElectronAnimation']['photonEnergyBandWidth'] = _SCHEMA['model']['multiElectronAnimation']['photonEnergyBandWidth'][2]
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
    for item in data['models']['beamline']:
        if item['type'] == 'crl':
            key_value_pairs = pkcollections.Dict({
                'material': 'User-defined',
                'method': 'server',
                'absoluteFocusPosition': None,
                'focalDistance': None,
                'tipRadius': float(item['radius']) * 1e6,  # m -> um
                'tipWallThickness': float(item['wallThickness']) * 1e6,  # m -> um
            })
            for field in key_value_pairs.keys():
                if field not in item:
                    item[field] = key_value_pairs[field]
    for item in data['models']['beamline']:
        if item['type'] == 'sample':
            if 'horizontalCenterCoordinate' not in item:
                item['horizontalCenterCoordinate'] = _SCHEMA['model']['sample']['horizontalCenterCoordinate'][2]
                item['verticalCenterCoordinate'] = _SCHEMA['model']['sample']['verticalCenterCoordinate'][2]

    for k in data['models']:
        if k == 'sourceIntensityReport' or k == 'initialIntensityReport' or template_common.is_watchpoint(k):
            if 'fieldUnits' not in data['models'][k]:
                data['models'][k]['fieldUnits'] = 1
    if 'samplingMethod' not in data['models']['simulation']:
        simulation = data['models']['simulation']
        simulation['samplingMethod'] = 1 if simulation['sampleFactor'] > 0 else 2
        for k in ['horizontalPosition', 'horizontalRange', 'verticalPosition', 'verticalRange']:
            simulation[k] = data['models']['initialIntensityReport'][k]
    if 'horizontalPosition' in data['models']['initialIntensityReport']:
        for k in data['models']:
            if k == 'sourceIntensityReport' or k == 'initialIntensityReport' or template_common.is_watchpoint(k):
                for f in ['horizontalPosition', 'horizontalRange', 'verticalPosition', 'verticalRange']:
                    del data['models'][k][f]
    if 'documentationUrl' not in data['models']['simulation']:
        data['models']['simulation']['documentationUrl'] = ''
    if 'tabulatedUndulator' not in data['models']:
        data['models']['tabulatedUndulator'] = pkcollections.Dict({
            'gap': 6.72,
            'phase': 0,
            'magneticFile': _PREDEFINED.magnetic_measurements[0]['fileName'],
            'longitudinalPosition': 1.305,
            'magnMeasFolder': '',
            'indexFileName': '',
        })
    else:
        if 'indexFile' in data.models.tabulatedUndulator:
            data.models.tabulatedUndulator.indexFileName = data.models.tabulatedUndulator.indexFile
            del data.models.tabulatedUndulator['indexFile']
    if 'undulatorType' not in data['models']['tabulatedUndulator']:
        data['models']['tabulatedUndulator']['undulatorType'] = 'u_t'

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
    if 'undulatorParameter' not in data['models']['undulator']:
        undulator = data['models']['undulator']
        undulator['undulatorParameter'] = round(_process_undulator_definition(pkcollections.Dict({
            'undulator_definition': 'B',
            'undulator_parameter': None,
            'vertical_amplitude': float(undulator['verticalAmplitude']),
            'undulator_period': float(undulator['period']) / 1000.0
        }))['undulator_parameter'], 8)
    if 'folder' not in data['models']['simulation']:
        if data['models']['simulation']['name'] in _EXAMPLE_FOLDERS:
            data['models']['simulation']['folder'] = _EXAMPLE_FOLDERS[data['models']['simulation']['name']]
        else:
            data['models']['simulation']['folder'] = '/'

    # Trajectory report:
    if 'trajectoryReport' not in data['models']:
        data['models']['trajectoryReport'] = pkcollections.Dict({
            'timeMomentEstimation': 'auto',
            'initialTimeMoment': 0.0,
            'finalTimeMoment': 0.0,
            'numberOfPoints': 10000,
            'plotAxis': 'x',
            'magneticField': 2,
        })
    # Update tabulated undulator length:
    _compute_undulator_length(data['models']['tabulatedUndulator'])

    if 'sizeDefinition' not in data['models']['gaussianBeam']:
        data['models']['gaussianBeam']['sizeDefinition'] = 1
        data['models']['gaussianBeam']['rmsDivergenceX'] = 0
        data['models']['gaussianBeam']['rmsDivergenceY'] = 0

    for k in ['photonEnergy', 'horizontalPointCount', 'horizontalPosition', 'horizontalRange',
              'sampleFactor', 'samplingMethod', 'verticalPointCount', 'verticalPosition', 'verticalRange']:
        if k not in data['models']['sourceIntensityReport']:
            data['models']['sourceIntensityReport'][k] = data['models']['simulation'][k]

    for k in data['models']:
        for rep_name in _DATA_FILE_FOR_MODEL.keys():
            if (k == rep_name or rep_name in k) and _DATA_FILE_FOR_MODEL[rep_name]['dimension'] == 3:
                work_rep_name = k if template_common.is_watchpoint(k) else rep_name
                if work_rep_name in data['models'] and 'intensityPlotsWidth' not in data['models'][work_rep_name]:
                    data['models'][work_rep_name]['intensityPlotsWidth'] = _SCHEMA['model'][rep_name]['intensityPlotsWidth'][2]
                if work_rep_name in data['models'] and 'intensityPlotsScale' not in data['models'][work_rep_name]:
                    data['models'][work_rep_name]['intensityPlotsScale'] = _SCHEMA['model'][rep_name]['intensityPlotsScale'][2]

    if 'longitudinalPosition' in data['models']['tabulatedUndulator']:
        tabulated_undulator = data['models']['tabulatedUndulator']
        for k in ['undulatorParameter', 'period', 'length', 'longitudinalPosition', 'horizontalAmplitude', 'horizontalSymmetry', 'horizontalInitialPhase', 'verticalAmplitude', 'verticalSymmetry', 'verticalInitialPhase']:
            if k in tabulated_undulator:
                if _is_tabulated_undulator_source(data['models']['simulation']):
                    data['models']['undulator'][k] = tabulated_undulator[k]
                del tabulated_undulator[k]

    if 'name' not in data['models']['tabulatedUndulator']:
        und = data['models']['tabulatedUndulator']
        und['name'] = und['undulatorSelector'] = 'Undulator'
        und['id'] = '1'


def get_animation_name(data):
    return data['modelName']


def get_application_data(data):
    if data['method'] == 'model_list':
        res = []
        model_name = data['model_name']
        if model_name == 'electronBeam':
            res.extend(_PREDEFINED.beams)
        res.extend(_load_user_model_list(model_name))
        if model_name == 'electronBeam':
            for beam in res:
                _process_beam_parameters(beam)
        return pkcollections.Dict({
            'modelList': res
        })
    if data['method'] == 'delete_user_models':
        return _delete_user_models(data['electron_beam'], data['tabulated_undulator'])
    if data['method'] == 'compute_grazing_angle':
        return _compute_grazing_angle(data['optical_element'])
    elif data['method'] == 'compute_crl_characteristics':
        return _compute_crl_focus(_compute_crl_characteristics(data['optical_element'], data['photon_energy']))
    elif data['method'] == 'compute_fiber_characteristics':
        return _compute_crl_characteristics(
            _compute_crl_characteristics(
                data['optical_element'],
                data['photon_energy'],
                prefix='external',
            ),
            data['photon_energy'],
            prefix='core',
        )
    elif data['method'] == 'compute_delta_atten_characteristics':
        return _compute_crl_characteristics(data['optical_element'], data['photon_energy'])
    elif data['method'] == 'compute_crystal_init':
        return _compute_crystal_init(data['optical_element'])
    elif data['method'] == 'compute_crystal_orientation':
        return _compute_crystal_orientation(data['optical_element'])
    elif data['method'] == 'process_intensity_reports':
        return _process_intensity_reports(data['source_type'], data['undulator_type'])
    elif data['method'] == 'process_beam_parameters':
        _process_beam_parameters(data['ebeam'])
        data['ebeam']['drift'] = _calculate_beam_drift(
            data['ebeam_position'],
            data['source_type'],
            data['undulator_type'],
            data['undulator_length'],
            data['undulator_period'],
        )
        return data['ebeam']
    elif data['method'] == 'compute_undulator_length':
        return _compute_undulator_length(data['tabulated_undulator'])
    elif data['method'] == 'process_undulator_definition':
        return _process_undulator_definition(data)
    elif data['method'] == 'processedImage':
        return _process_image(data)
    raise RuntimeError('unknown application data method: {}'.format(data['method']))


def get_data_file(run_dir, model, frame, **kwargs):
    filename = get_filename_for_model(model)
    with open(str(run_dir.join(filename))) as f:
        return filename, f.read(), 'application/octet-stream'
    raise RuntimeError('output file unknown for model: {}'.format(model))


def get_filename_for_model(model):
    if template_common.is_watchpoint(model):
        model = _WATCHPOINT_REPORT_NAME
    return _DATA_FILE_FOR_MODEL[model]['filename']


def get_predefined_beams():
    return _PREDEFINED['beams']


def get_simulation_frame(run_dir, data, model_data):
    if data['report'] == 'multiElectronAnimation':
        args = template_common.parse_animation_args(data, {'': ['intensityPlotsWidth', 'intensityPlotsScale']})
        m = model_data.models[data['report']]
        m.intensityPlotsWidth = args.intensityPlotsWidth
        m.intensityPlotsScale = args.intensityPlotsScale
    return extract_report_data(str(run_dir.join(get_filename_for_model(data['report']))), model_data)


def import_file(request, lib_dir, tmp_dir):
    f = request.files['file']
    input_text = f.read()
    # attempt to decode the input as json first, if invalid try python
    try:
        parsed_data = simulation_db.json_load(input_text)
    except ValueError as e:
        # Failed to read json
        arguments = str(request.form.get('arguments', ''))
        pkdlog('{}: arguments={}', f.filename, arguments)
        parsed_data = srw_importer.import_python(
            input_text,
            lib_dir=lib_dir,
            tmp_dir=tmp_dir,
            user_filename=f.filename,
            arguments=arguments,
        )
    return simulation_db.fixup_old_data(parsed_data, force=True)[0]


def lib_files(data, source_lib, report=None):
    """Returns list of auxiliary files

    Args:
        data (dict): simulation db
        source_lib (py.path): directory of source
        report

    Returns:
        list: py.path.local of source files
    """
    res = []

    #TODO(MR): possibly need to fix up old data before accessing the data - old tests fail.
    # fixup_old_data(data)

    dm = data.models
    # the mirrorReport.heightProfileFile may be different than the file in the beamline
    if report == 'mirrorReport':
        res.append(dm['mirrorReport']['heightProfileFile'])
    if _is_tabulated_undulator_source(dm.simulation):
        if 'tabulatedUndulator' in dm and dm.tabulatedUndulator.magneticFile:
            res.append(dm.tabulatedUndulator.magneticFile)
    for m in dm.beamline:
        for k, v in _SCHEMA.model[m.type].items():
            t = v[1]
            if m[k] and t in ['MirrorFile', 'ImageFile']:
                if not report or template_common.is_watchpoint(report) or report == 'multiElectronAnimation':
                    res.append(m[k])
    return template_common.internal_lib_files(res, source_lib)


def _report_fields(data, report_name):
    # if the model has "style" fields, then return the full list of non-style fields
    # otherwise returns the report name (which implies all model fields)
    m = data.models[report_name]
    for style_field in _REPORT_STYLE_FIELDS:
        if style_field not in m:
            continue
        res = []
        for f in m:
            if f in _REPORT_STYLE_FIELDS:
                continue
            res.append('{}.{}'.format(report_name, f))
        return res
    return [report_name]


def models_related_to_report(data):
    """What models are required for this data['report']

    Args:
        data (dict): simulation
    Returns:
        list: Named models, model fields or values (dict, list) that affect report
    """
    r = data['report']
    if r == 'mirrorReport':
        return [
            #TODO(pjm): will need to add file modified datetime value if file replacement is implemented
            'mirrorReport.heightProfileFile',
            'mirrorReport.orientation',
            'mirrorReport.grazingAngle',
            'mirrorReport.heightAmplification',
        ]
    res = _report_fields(data, r) + [
        'electronBeam', 'electronBeamPosition', 'gaussianBeam', 'multipole',
        'simulation.sourceType', 'tabulatedUndulator', 'undulator',
    ]
    watchpoint = template_common.is_watchpoint(r)
    if watchpoint or r == 'initialIntensityReport':
        res.extend([
            'simulation.horizontalPointCount',
            'simulation.horizontalPosition',
            'simulation.horizontalRange',
            'simulation.photonEnergy',
            'simulation.sampleFactor',
            'simulation.samplingMethod',
            'simulation.verticalPointCount',
            'simulation.verticalPosition',
            'simulation.verticalRange',
        ])
    if r == 'initialIntensityReport':
        beamline = data['models']['beamline']
        res.append([beamline[0]['position'] if len(beamline) else 0])
    if watchpoint:
        wid = template_common.watchpoint_id(r)
        beamline = data['models']['beamline']
        propagation = data['models']['propagation']
        for item in beamline:
            item_copy = item.copy()
            del item_copy['title']
            res.append(item_copy)
            res.append(propagation[str(item['id'])])
            if item['type'] == 'watch' and item['id'] == wid:
                break
        if beamline[-1]['id'] == wid:
            res.append('postPropagation')
    return res


def new_simulation(data, new_simulation_data):
    source = new_simulation_data['sourceType']
    data['models']['simulation']['sourceType'] = source
    if source == 'g':
        intensityReport = data['models']['initialIntensityReport']
        intensityReport['sampleFactor'] = 0


def prepare_aux_files(run_dir, data):
    _copy_lib_files(
        data,
        simulation_db.simulation_lib_dir(SIM_TYPE),
        run_dir,
        data['report'],
    )
    if not _is_tabulated_undulator_source(data['models']['simulation']):
        return
    filename = data['models']['tabulatedUndulator']['magneticFile']
    filepath = run_dir.join(filename)
    for f in _PREDEFINED.magnetic_measurements:
        if filename == f['fileName'] and not filepath.check():
            _RESOURCE_DIR.join(f['fileName']).copy(run_dir)
    m = MagnMeasZip(str(filepath))
    for f in m.dat_files + [m.index_file]:
        content = m.get_file_content(f)
        m.save_file(str(run_dir), f, content)
    data['models']['tabulatedUndulator']['magnMeasFolder'] = m.index_dir if m.index_dir else './'
    data['models']['tabulatedUndulator']['indexFileName'] = m.index_file


def _create_user_model(data, model_name):
    model = data['models'][model_name]
    if model_name == 'tabulatedUndulator':
        model = model.copy()
        model['undulator'] = data['models']['undulator']
    return model


def prepare_for_client(data):
    for model_name in _USER_MODEL_LIST_FILENAME.keys():
        model = data['models'][model_name]
        pluralKey = '{}s'.format(model_name)
        if _is_user_defined_model(model):
            user_model_list = _load_user_model_list(model_name)
            search_model = None
            if pluralKey not in data['models']:
                models_by_id = _user_model_map(user_model_list, 'id')
                if model['id'] in models_by_id:
                    search_model = models_by_id[model['id']]
            if search_model:
                data['models'][model_name] = search_model
                if model_name == 'tabulatedUndulator':
                    del data['models'][model_name]['undulator']
            else:
                pkdc('adding model: {}', model['name'])
                if model['name'] in _user_model_map(user_model_list, 'name'):
                    model['name'] = _unique_name(user_model_list, 'name', model['name'] + ' {}')
                    selectorName = 'beamSelector' if model_name == 'electronBeam' else 'undulatorSelector'
                    model[selectorName] = model['name']
                model['id'] = _unique_name(user_model_list, 'id', data['models']['simulation']['simulationId'] + ' {}')
                user_model_list.append(_create_user_model(data, model_name))
                _save_user_model_list(model_name, user_model_list)
                simulation_db.save_simulation_json(data)

        if pluralKey in data['models']:
            del data['models'][pluralKey]
            simulation_db.save_simulation_json(data)
    return data


def prepare_for_save(data):
    for model_name in _USER_MODEL_LIST_FILENAME.keys():
        model = data['models'][model_name]
        if _is_user_defined_model(model):
            user_model_list = _load_user_model_list(model_name)
            models_by_id = _user_model_map(user_model_list, 'id')

            if model['id'] not in models_by_id:
                pkdc('adding new model: {}', model['name'])
                user_model_list.append(_create_user_model(data, model_name))
                _save_user_model_list(model_name, user_model_list)
            elif models_by_id[model['id']] != model:
                pkdc('replacing beam: {}: {}', model['id'], model['name'])
                for i,m in enumerate(user_model_list):
                    if m['id'] == model['id']:
                        pkdc('found replace beam, id: {}, i: {}', m['id'], i)
                        user_model_list[i] = _create_user_model(data, model_name)
                        _save_user_model_list(model_name, user_model_list)
                        break
    return data


def prepare_output_file(report_info, data):
    if data['report'] == 'mirrorReport':
        return
    #TODO(pjm): only need to rerun extract_report_data() if report style fields have changed
    fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, report_info.run_dir)
    if fn.exists():
        fn.remove()
        res = extract_report_data(
            str(report_info.run_dir.join(get_filename_for_model(data['report']))),
            data)
        simulation_db.write_result(res, run_dir=report_info.run_dir)


def python_source_for_model(data, model):
    data['report'] = model or _RUN_ALL_MODEL
    return """{}

if __name__ == '__main__':
    main()
""".format(_generate_parameters_file(data, plot_reports=True))


def remove_last_frame(run_dir):
    pass


def resource_files():
    """Files to copy from resources when creating a new user

    Returns:
        list: py.path.local objects
    """
    res = []
    for k, v in _PREDEFINED.items():
        for v2 in v:
            try:
                res.append(_RESOURCE_DIR.join(v2['fileName']))
            except KeyError:
                pass
    return res


def validate_file(file_type, path):
    """Ensure the data file contains parseable rows data"""
    match = re.search(r'\.(\w+)$', str(path))
    extension = None
    if match:
        extension = match.group(1).lower()
    else:
        return 'invalid file extension'

    if extension == 'dat' or extension == 'txt':
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
            if re.search(r'\.txt', f.lower()):
                is_valid = True
                break
        if not is_valid:
            return 'zip file missing txt index file'
    elif extension.lower() in ['tif', 'tiff', 'npy']:
        filename = os.path.splitext(os.path.basename(str(path)))[0]
        # Save the processed file:
        srwl_uti_smp.SRWLUtiSmp(file_path=str(path), is_save_images=True, prefix=filename)
    else:
        return 'invalid file type: {}'.format(extension)
    return None


def write_parameters(data, schema, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        schema (dict): to validate data
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data)
    )


def _add_report_filenames(v):
    for k in _DATA_FILE_FOR_MODEL:
        v['{}Filename'.format(k)] = _DATA_FILE_FOR_MODEL[k]['filename']


def _beamline_element(template, item, fields, propagation, shift=''):
    return '{}    el.append({})'.format(
        shift,
        template.format(*map(lambda x: item[x], fields))
    ), _propagation_params(propagation[str(item['id'])][0], shift)


def _calculate_beam_drift(ebeam_position, source_type, undulator_type, undulator_length, undulator_period):
    if ebeam_position['driftCalculationMethod'] == 'auto':
        """Calculate drift for ideal undulator."""
        if source_type == 'u' or (source_type == 't' and undulator_type == 'u_i'):
            # initial drift = 1/2 undulator length + 2 periods
            return -0.5 * float(undulator_length) - 2 * float(undulator_period)
        return 0
    return ebeam_position['drift']

def _compute_crl_characteristics(model, photon_energy, prefix=''):
    fields_with_prefix = pkcollections.Dict({
        'material': 'material',
        'refractiveIndex': 'refractiveIndex',
        'attenuationLength': 'attenuationLength',
    })
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
    kwargs = pkcollections.Dict({
        'energy': photon_energy,
    })
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
        radius=float(model['tipRadius']) * 1e-6,  # um -> m
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
        pkdlog('{}: error: {}', material_raw, pkdexc())
        for key in parms_list:
            model[key] = None

    return model


def _compute_crystal_orientation(model):
    parms_list = ['nvx', 'nvy', 'nvz', 'tvx', 'tvy']
    try:
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
            rot = uti_math.trf_rotation([0, 1, 0], model['rotationAngle'], [0, 0, 0])[0]
            nCr = uti_math.matr_prod(rot, nCr)
            tCr = uti_math.matr_prod(rot, tCr)

        model['nvx'] = nCr[0]
        model['nvy'] = nCr[1]
        model['nvz'] = nCr[2]
        model['tvx'] = tCr[0]
        model['tvy'] = tCr[1]
    except Exception:
        pkdlog('\n{}', traceback.format_exc())
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
    if model['undulatorType'] == 'u_i':
        return model
    zip_file = simulation_db.simulation_lib_dir(SIM_TYPE).join(model['magneticFile'])
    if zip_file.check():
        m = MagnMeasZip(str(zip_file))
        m.find_closest_gap(model['gap'])
        model['length'] = m.dat_file_found_length
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


def _copy_lib_files(data, source_lib, target, report=None):
    """Copy auxiliary files to target

    Args:
        data (dict): simulation db
        source_lib (py.path.local): source directory
        target (py.path): destination directory
        report (str): report to copy [optional]
    """
    for f in lib_files(data, source_lib, report):
        path = target.join(f.basename)
        if f.exists() and not path.exists():
            f.copy(path)


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


def _delete_user_models(electron_beam, tabulated_undulator):
    """Remove the beam and undulator user model list files"""
    for model_name in _USER_MODEL_LIST_FILENAME.keys():
        model = electron_beam if model_name == 'electronBeam' else tabulated_undulator
        if not model or 'id' not in model:
            continue
        user_model_list = _load_user_model_list(model_name)
        for i,m in enumerate(user_model_list):
            if m['id'] == model.id:
                del user_model_list[i]
                _save_user_model_list(model_name, user_model_list)
                break
    return pkcollections.Dict({})


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
    return pkcollections.Dict({
        'idx': idx,
        'closest_value': values_list[idx],
    })


def _find_dat_files_from_index_file(index_content):
    gaps = []
    dat_files = []
    for row in index_content:
        v = row.strip()
        if v:
            v = v.split()
            gaps.append(float(v[0]))
            dat_files.append(v[3])
    return gaps, dat_files


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
        if re.search(r'\.txt', f):
            index_file = os.path.basename(f)
            index_dir = os.path.dirname(f)
            break
    assert index_file is not None
    return index_dir, index_file


def _generate_beamline_optics(models, last_id):
    beamline = models['beamline']
    propagation = models['propagation']
    res_el = '    el = []\n'
    res_pp = '    pp = []\n'

    prev = None
    has_item = False
    last_element = False
    want_final_propagation = True

    height_profile_counter = 1
    sample_counter = 1
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
        if 'isDisabled' in item and item['isDisabled']:
            pass
        elif item['type'] == 'aperture':
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
                ['focalPlane', 'refractiveIndex', 'attenuationLength', 'shape', 'horizontalApertureSize', 'verticalApertureSize', 'tipRadius', 'numberOfLenses', 'tipWallThickness'],
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
        elif item['type'] == 'mask':
            el, pp = _beamline_element(
                '''srwlib.srwl_opt_setup_mask(_delta={}, _atten_len={}, _thick={}, _grid_sh={},
                                         _grid_dx={}, _grid_dy={}, _pitch_x={}, _pitch_y={},
                                         _grid_nx={}, _grid_ny={}, _mask_Nx={}, _mask_Ny={},
                                         _grid_angle={}, _hx={}, _hy={},
                                         _mask_x0={}, _mask_y0={})''',
                item,
                ['refractiveIndex', 'attenuationLength', 'maskThickness', 'gridShape',
                 'horizontalGridDimension', 'verticalGridDimension', 'horizontalGridPitch', 'verticalGridPitch',
                 'horizontalGridsNumber', 'verticalGridsNumber', 'horizontalPixelsNumber', 'verticalPixelsNumber',
                 'gridTiltAngle', 'horizontalSamplingInterval', 'verticalSamplingInterval',
                 'horizontalMaskCoordinate', 'verticalMaskCoordinate'],
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
        elif item['type'] == 'sample':
            file_name = 'op_sample{}'.format(sample_counter)
            sample_counter += 1
            el, pp = _beamline_element(
                """srwl_uti_smp.srwl_opt_setup_transm_from_file(
                    file_path=v.""" + file_name + """,
                    resolution={},
                    thickness={},
                    delta={},
                    atten_len={},
                    xc={},
                    yc={},
                    is_save_images=True,
                    prefix='""" + file_name + """')""",
                item,
                ['resolution', 'thickness', 'refractiveIndex', 'attenuationLength',
                 'horizontalCenterCoordinate', 'verticalCenterCoordinate'],
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

    return res_el + res_pp + '    return srwlib.SRWLOptC(el, pp)'


def _generate_parameters_file(data, plot_reports=False):
    # Process method and magnetic field values for intensity, flux and intensity distribution reports:
    # Intensity report:
    magnetic_field = _process_intensity_reports(
        data['models']['simulation']['sourceType'],
        data['models']['tabulatedUndulator']['undulatorType']
    )['magneticField']
    data['models']['intensityReport']['magneticField'] = magnetic_field
    data['models']['sourceIntensityReport']['magneticField'] = magnetic_field

    if magnetic_field == 1:
        data['models']['trajectoryReport']['magneticField'] = 1

    report = data['report']
    if report == 'fluxAnimation':
        data['models']['fluxReport'] = data['models'][report].copy()
    elif template_common.is_watchpoint(report) or report == 'sourceIntensityReport':
        # render the watchpoint report settings in the initialIntensityReport template slot
        data['models']['initialIntensityReport'] = data['models'][report].copy()
    if report == 'sourceIntensityReport':
        for k in ['photonEnergy', 'horizontalPointCount', 'horizontalPosition', 'horizontalRange',
                  'sampleFactor', 'samplingMethod', 'verticalPointCount', 'verticalPosition', 'verticalRange']:
            data['models']['simulation'][k] = data['models']['sourceIntensityReport'][k]

    if _is_tabulated_undulator_source(data['models']['simulation']):
        undulator_type = data['models']['tabulatedUndulator']['undulatorType']
        if undulator_type == 'u_i':
            data['models']['tabulatedUndulator']['gap'] = 0.0
            data['models']['tabulatedUndulator']['indexFileName'] = ''

    if report != 'multiElectronAnimation' or data['models']['multiElectronAnimation']['photonEnergyBandWidth'] <= 0:
        data['models']['multiElectronAnimation']['photonEnergyIntegration'] = 0
        data['models']['simulation']['finalPhotonEnergy'] = -1.0
    else:
        data['models']['multiElectronAnimation']['photonEnergyIntegration'] = 1
        half_width = float(data['models']['multiElectronAnimation']['photonEnergyBandWidth']) / 2.0
        data['models']['simulation']['photonEnergy'] = float(data['models']['simulation']['photonEnergy'])
        data['models']['simulation']['finalPhotonEnergy'] = data['models']['simulation']['photonEnergy'] + half_width
        data['models']['simulation']['photonEnergy'] -= half_width

    _validate_data(data, _SCHEMA)
    last_id = None
    if template_common.is_watchpoint(report):
        last_id = template_common.watchpoint_id(report)
    if int(data['models']['simulation']['samplingMethod']) == 2:
        data['models']['simulation']['sampleFactor'] = 0
    v = template_common.flatten_data(data['models'], pkcollections.Dict())
    run_all = report == _RUN_ALL_MODEL
    v['beamlineOptics'] = _generate_beamline_optics(data['models'], last_id)
    # und_g and und_ph API units are mm rather than m
    v['tabulatedUndulator_gap'] *= 1000
    v['tabulatedUndulator_phase'] *= 1000

    if report in data['models'] and 'distanceFromSource' in data['models'][report]:
        position = data['models'][report]['distanceFromSource']
    else:
        position = _get_first_element_position(data)
    v['beamlineFirstElementPosition'] = position

    # 1: auto-undulator 2: auto-wiggler
    v['energyCalculationMethod'] = 1 if _is_undulator_source(data['models']['simulation']) else 2

    if _is_user_defined_model(data['models']['electronBeam']):
        v['electronBeam_name'] = ''  # MR: custom beam name should be empty to be processed by SRW correctly
    if data['models']['electronBeam']['beamDefinition'] == 'm':
        v['electronBeam_horizontalBeta'] = None
    v[report] = 1
    _add_report_filenames(v)
    v['srwMain'] = _generate_srw_main(report, run_all, plot_reports)

    # Beamline optics defined through the parameters list:
    v['beamlineOpticsParameters'] = ''
    sample_counter = 1
    for el in data['models']['beamline']:
        if el['type'] == 'sample':
            v['beamlineOpticsParameters'] += '''\n    ['op_sample{0}', 's', '{1}', 'input file of the sample #{0}'],'''.format(sample_counter, el['imageFile'])
            sample_counter += 1

    return pkjinja.render_resource('srw.py', v)


def _generate_srw_main(report, run_all, plot_reports):
    content = [
        'v = srwl_bl.srwl_uti_parse_options(varParam, use_sys_argv={})'.format(plot_reports),
        'source_type, mag = srwl_bl.setup_source(v)',
    ]
    if run_all or template_common.is_watchpoint(report) or report == 'multiElectronAnimation':
        content.append('op = set_optics(v)')
    else:
        # set_optics() can be an expensive call for mirrors, only invoke if needed
        content.append('op = None')
    if run_all or report == 'intensityReport':
        content.append('v.ss = True')
        if plot_reports:
            content.append("v.ss_pl = 'e'")
    if run_all or report in 'fluxReport':
        content.append('v.sm = True')
        if plot_reports:
            content.append("v.sm_pl = 'e'")
    if run_all or report == 'powerDensityReport':
        content.append('v.pw = True')
        if plot_reports:
            content.append("v.pw_pl = 'xy'")
    if run_all or report in ['initialIntensityReport', 'sourceIntensityReport']:
        content.append('v.si = True')
        if plot_reports:
            content.append("v.si_pl = 'xy'")
    if run_all or report == 'trajectoryReport':
        content.append('v.tr = True')
        if plot_reports:
            content.append("v.tr_pl = 'xz'")
    if run_all or template_common.is_watchpoint(report):
        content.append('v.ws = True')
        if plot_reports:
            content.append("v.ws_pl = 'xy'")
    if plot_reports or not _is_background_report(report):
        content.append('srwl_bl.SRWLBeamline(_name=v.name, _mag_approx=mag).calc_all(v, op)')
    return '\n'.join(['    {}'.format(x) for x in content])


def _get_first_element_position(data):
    beamline = data['models']['beamline']
    if len(beamline):
        return beamline[0]['position']
    return template_common.DEFAULT_INTENSITY_DISTANCE


def _height_profile_element(item, propagation, overwrite_propagation=False, height_profile_el_name='Mirror'):
    shift = '    '
    if overwrite_propagation:
        if item['heightProfileFile'] and item['heightProfileFile'] != 'None':
            propagation[str(item['id'])][0] = [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0]
        else:
            return '', ''

    dat_file = str(simulation_db.simulation_lib_dir(SIM_TYPE).join(item['heightProfileFile']))
    dimension = find_height_profile_dimension(dat_file)

    res = '\n{}ifn{} = "{}"\n'.format(shift, height_profile_el_name, item['heightProfileFile'])
    res += '{}if ifn{}:\n'.format(shift, height_profile_el_name)
    add_args = ', 0, 1' if dimension == 1 else ''
    res += '{}    hProfData{} = srwlib.srwl_uti_read_data_cols(ifn{}, "\\t"{})\n'.format(shift, height_profile_el_name, height_profile_el_name, add_args)
    fields = ['orientation', 'grazingAngle', 'heightAmplification']
    hProfData = 'hProfData{}'.format(height_profile_el_name)
    surf_height_func = 'srwlib.srwl_opt_setup_surf_height_{}d'.format(dimension)
    if 'horizontalTransverseSize' in item:
        template = surf_height_func + '(' + hProfData + ', _dim="{}", _ang={}, _amp_coef={}, _size_x={}, _size_y={})'
        fields.extend(('horizontalTransverseSize', 'verticalTransverseSize'))
    else:
        template = surf_height_func + '(' + hProfData + ', _dim="{}", _ang={}, _amp_coef={})'
    el, pp = _beamline_element(template, item, fields, propagation, shift=shift)
    res += el
    pp = '{}if ifn{}:\n{}'.format(shift, height_profile_el_name, pp)
    return res, pp


def _init():
    global _PREDEFINED
    if _PREDEFINED:
        return
    _PREDEFINED = pkcollections.Dict()
    _PREDEFINED['mirrors'] = _predefined_files_for_type('mirror')
    _PREDEFINED['magnetic_measurements'] = _predefined_files_for_type('undulatorTable')
    _PREDEFINED['sample_images'] = _predefined_files_for_type('sample')
    beams = []
    for beam in srwl_uti_src.srwl_uti_src_e_beam_predef():
        info = beam[1]
        # _Iavg, _e, _sig_e, _emit_x, _beta_x, _alpha_x, _eta_x, _eta_x_pr, _emit_y, _beta_y, _alpha_y
        beams.append(pkcollections.Dict({
            'name': beam[0],
            'current': info[0],
            'energy': info[1],
            'rmsSpread': info[2],
            'horizontalEmittance': round(info[3] * 1e9, 6),
            'horizontalBeta': info[4],
            'horizontalAlpha': info[5],
            'horizontalDispersion': info[6],
            'horizontalDispersionDerivative': info[7],
            'verticalEmittance': round(info[8] * 1e9, 6),
            'verticalBeta': info[9],
            'verticalAlpha': info[10],
            'verticalDispersion': 0,
            'verticalDispersionDerivative': 0,
            'energyDeviation': 0,
            'horizontalPosition': 0,
            'verticalPosition': 0,
            'drift': 0.0,
            'isReadOnly': True,
        }))
    _PREDEFINED['beams'] = beams


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


def _is_background_report(report):
    return 'Animation' in report


def _is_dipole_source(sim):
    return sim['sourceType'] == 'm'

def _is_gaussian_source(sim):
    return sim['sourceType'] == 'g'


def _is_tabulated_undulator_source(sim):
    return sim['sourceType'] == 't'


def _is_undulator_source(sim):
    return sim['sourceType'] in ['u', 't']


def _is_user_defined_model(ebeam):
    if 'isReadOnly' in ebeam and ebeam['isReadOnly']:
        return False
    return True


def _load_user_model_list(model_name):
    filepath = simulation_db.simulation_lib_dir(SIM_TYPE).join(_USER_MODEL_LIST_FILENAME[model_name])
    if filepath.exists():
        return simulation_db.read_json(filepath)
    _save_user_model_list(model_name, [])
    return _load_user_model_list(model_name)


def _normalize_eol(file_desc):
    s = file_desc.read().replace('\r\n', '\n').replace('\r', '\n')
    content = s.split('\n')
    return content


def _predefined_files_for_type(file_type):
    res = []
    for extension in extensions_for_file_type(file_type):
        for f in glob.glob(str(_RESOURCE_DIR.join(extension))):
            if os.path.isfile(f):
                res.append(pkcollections.Dict({
                    'fileName': os.path.basename(f),
                }))
    return res


def _process_beam_parameters(ebeam):
    # if the beamDefinition is "twiss", compute the moments fields and set on ebeam
    moments_fields = ['rmsSizeX', 'xxprX', 'rmsDivergX', 'rmsSizeY', 'xxprY', 'rmsDivergY']
    for k in moments_fields:
        if k not in ebeam:
            ebeam[k] = 0
    if 'beamDefinition' not in ebeam:
        ebeam['beamDefinition'] = 't'

    if ebeam['beamDefinition'] == 't':  # Twiss
        model = copy.deepcopy(ebeam)
        # Convert to SI units to perform SRW calculation:
        for k in model:
            model[k] = _convert_ebeam_units(k, ebeam[k])
        beam = srwlib.SRWLPartBeam()
        beam.from_Twiss(
            _e=model['energy'],
            _sig_e=model['rmsSpread'],
            _emit_x=model['horizontalEmittance'],
            _beta_x=model['horizontalBeta'],
            _alpha_x=model['horizontalAlpha'],
            _eta_x=model['horizontalDispersion'],
            _eta_x_pr=model['horizontalDispersionDerivative'],
            _emit_y=model['verticalEmittance'],
            _beta_y=model['verticalBeta'],
            _alpha_y=model['verticalAlpha'],
            _eta_y=model['verticalDispersion'],
            _eta_y_pr=model['verticalDispersionDerivative'],
        )

        for i, k in enumerate(moments_fields):
            model[k] = beam.arStatMom2[i] if k in ['xxprX', 'xxprY'] else beam.arStatMom2[i] ** 0.5

        # Convert to the units used in the schema:
        for k in model:
            model[k] = _convert_ebeam_units(k, model[k], to_si=False)

        # copy moments values into the ebeam
        for k in moments_fields:
            ebeam[k] = model[k]


def _process_image(data):
    """Process image and return

    Args:
        data (dict): description of simulation

    Returns:
        py.path.local: file to return
    """
    import werkzeug
    # This should just be a basename, but this ensures it.
    b = werkzeug.secure_filename(data.baseImage)
    fn = simulation_db.simulation_lib_dir(data.simulationType).join(b)
    with pkio.save_chdir(simulation_db.tmp_dir()) as d:
        res = py.path.local(fn.purebasename)
        srwl_uti_smp.SRWLUtiSmp(
            file_path=str(fn),
            is_save_images=True,
            prefix=str(res),
        )
        res += '_processed.tif'
        res.check()
    return res


def _process_intensity_reports(source_type, undulator_type):
    # Magnetic field processing:
    return pkcollections.Dict({
        'magneticField': 2 if source_type == 't' and undulator_type == 'u_t' else 1,
    })


def _process_undulator_definition(model):
    """Convert K -> B and B -> K."""
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


def _remap_3d(info, allrange, z_label, z_units, width_pixels, scale='linear'):
    x_range = [allrange[3], allrange[4], allrange[5]]
    y_range = [allrange[6], allrange[7], allrange[8]]
    ar2d = info['points']

    totLen = int(x_range[2] * y_range[2])
    lenAr2d = len(ar2d)
    if lenAr2d > totLen:
        ar2d = np.array(ar2d[0:totLen])
    elif lenAr2d < totLen:
        auxAr = np.array('d', [0] * lenAr2d)
        for i in range(lenAr2d):
            auxAr[i] = ar2d[i]
        ar2d = np.array(auxAr)
    if isinstance(ar2d, (list, np.array)):
        ar2d = np.array(ar2d)
    ar2d = ar2d.reshape(y_range[2], x_range[2])

    if scale != 'linear':
        ar2d[np.where(ar2d <= 0.)] = 1.e-23
        ar2d = getattr(np, scale)(ar2d)
    if width_pixels and width_pixels < x_range[2]:
        try:
            resize_factor = float(width_pixels) / float(x_range[2])
            pkdlog('Size before: {}  Dimensions: {}', ar2d.size, ar2d.shape)
            ar2d = zoom(ar2d, resize_factor)
            # Remove for #670, this may be required for certain reports?
            # if scale == 'linear':
            #     ar2d[np.where(ar2d < 0.)] = 0.0
            pkdlog('Size after : {}  Dimensions: {}', ar2d.size, ar2d.shape)
            x_range[2] = ar2d.shape[1]
            y_range[2] = ar2d.shape[0]
        except:
            pkdlog('Cannot resize the image - scipy.ndimage.zoom() cannot be imported.')
            pass

    return pkcollections.Dict({
        'x_range': x_range,
        'y_range': y_range,
        'x_label': info['x_label'],
        'y_label': info['y_label'],
        'z_label': _superscript(z_label + ' [' + z_units + ']'),
        'title': info['title'],
        'z_matrix': ar2d.tolist(),
    })


def _save_user_model_list(model_name, beam_list):
    pkdc('saving {} list', model_name)
    filepath = simulation_db.simulation_lib_dir(SIM_TYPE).join(_USER_MODEL_LIST_FILENAME[model_name])
    #TODO(pjm): want atomic replace?
    simulation_db.write_json(filepath, beam_list)


def _superscript(val):
    return re.sub(r'\^2', u'\u00B2', val)


def _unique_name(items, field, template):
    #TODO(pjm): this is the same logic as sirepo.js uniqueName()
    values = pkcollections.Dict()
    for item in items:
        values[item[field]] = True
    index = 1
    while True:
        found_it = False
        id = template.replace('{}', str(index))
        if id in values:
            index += 1
        else:
            return id

def _user_model_map(model_list, field):
    res = pkcollections.Dict()
    for model in model_list:
        res[model[field]] = model
    return res


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    template_common.validate_models(data, schema)
    for item_id in data['models']['propagation']:
        _validate_propagation(data['models']['propagation'][item_id][0])
        _validate_propagation(data['models']['propagation'][item_id][1])
    _validate_propagation(data['models']['postPropagation'])


def _validate_propagation(prop):
    for i in range(len(prop)):
        prop[i] = int(prop[i]) if i in (0, 1, 3, 4) else float(prop[i])


_init()
