# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
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

_BRILLIANCE_OUTPUT_FILE = 'res_brilliance.dat'

_MIRROR_OUTPUT_FILE = 'res_mirror.dat'

_WATCHPOINT_REPORT_NAME = 'watchpointReport'

_DATA_FILE_FOR_MODEL = pkcollections.Dict({
    'fluxAnimation': {'filename': 'res_spec_me.dat', 'dimension': 2},
    'fluxReport': {'filename': 'res_spec_me.dat', 'dimension': 2},
    'initialIntensityReport': {'filename': 'res_int_se.dat', 'dimension': 3},
    'intensityReport': {'filename': 'res_spec_se.dat', 'dimension': 2},
    'mirrorReport': {'filename': _MIRROR_OUTPUT_FILE, 'dimension': 3},
    'multiElectronAnimation': {'filename': 'res_int_pr_me.dat', 'dimension': 3},
    'powerDensityReport': {'filename': 'res_pow.dat', 'dimension': 3},
    'sourceIntensityReport': {'filename': 'res_int_se.dat', 'dimension': 3},
    'brillianceReport': {'filename': _BRILLIANCE_OUTPUT_FILE, 'dimension': 2},
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

# beamline element [template, fields, height profile name, height profile overwrite propagation]
_ITEM_DEF = {
    'aperture': [
        'srwlib.SRWLOptA("{}", "a", {}, {}, {}, {})',
        ['shape', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
    ],
    'crl': [
        'srwlib.srwl_opt_setup_CRL({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})',
        ['focalPlane', 'refractiveIndex', 'attenuationLength', 'shape', 'horizontalApertureSize', 'verticalApertureSize', 'tipRadius', 'numberOfLenses', 'tipWallThickness', 'horizontalOffset', 'verticalOffset'],
    ],
    'crystal': [
        'srwlib.SRWLOptCryst(_d_sp={}, _psi0r={}, _psi0i={}, _psi_hr={}, _psi_hi={}, _psi_hbr={}, _psi_hbi={}, _tc={}, _ang_as={})',
        ['dSpacing', 'psi0r', 'psi0i', 'psiHr', 'psiHi', 'psiHBr', 'psiHBi', 'crystalThickness', 'asymmetryAngle'],
        'Cryst',
        True,
    ],
    'ellipsoidMirror': [
        'srwlib.SRWLOptMirEl(_p={}, _q={}, _ang_graz={}, _size_tang={}, _size_sag={}, _nvx={}, _nvy={}, _nvz={}, _tvx={}, _tvy={}, _x={}, _y={})',
        ['firstFocusLength', 'focalLength', 'grazingAngle', 'tangentialSize', 'sagittalSize', 'normalVectorX', 'normalVectorY', 'normalVectorZ', 'tangentialVectorX', 'tangentialVectorY', 'horizontalOffset', 'verticalOffset'],
        'ElMirror',
        True,
    ],
    'fiber': [
        'srwlib.srwl_opt_setup_cyl_fiber(_foc_plane={}, _delta_ext={}, _delta_core={}, _atten_len_ext={}, _atten_len_core={}, _diam_ext={}, _diam_core={}, _xc={}, _yc={})',
        ['focalPlane', 'externalRefractiveIndex', 'coreRefractiveIndex', 'externalAttenuationLength', 'coreAttenuationLength', 'externalDiameter', 'coreDiameter', 'horizontalCenterPosition', 'verticalCenterPosition'],
    ],
    'grating': [
        'srwlib.SRWLOptG(_mirSub=srwlib.SRWLOptMirPl(_size_tang={}, _size_sag={}, _nvx={}, _nvy={}, _nvz={}, _tvx={}, _tvy={}, _x={}, _y={}), _m={}, _grDen={}, _grDen1={}, _grDen2={}, _grDen3={}, _grDen4={})',
        ['tangentialSize', 'sagittalSize', 'normalVectorX', 'normalVectorY', 'normalVectorZ', 'tangentialVectorX', 'tangentialVectorY', 'horizontalOffset', 'verticalOffset', 'diffractionOrder', 'grooveDensity0', 'grooveDensity1', 'grooveDensity2', 'grooveDensity3', 'grooveDensity4'],
    ],
    'lens': [
        'srwlib.SRWLOptL({}, {}, {}, {})',
        ['horizontalFocalLength', 'verticalFocalLength', 'horizontalOffset', 'verticalOffset'],
    ],
    'mask': [
        'srwlib.srwl_opt_setup_mask(_delta={}, _atten_len={}, _thick={}, _grid_sh={}, _grid_dx={}, _grid_dy={}, _pitch_x={}, _pitch_y={}, _grid_nx={}, _grid_ny={}, _mask_Nx={}, _mask_Ny={}, _grid_angle={}, _hx={}, _hy={}, _mask_x0={}, _mask_y0={})',
        ['refractiveIndex', 'attenuationLength', 'maskThickness', 'gridShape', 'horizontalGridDimension', 'verticalGridDimension', 'horizontalGridPitch', 'verticalGridPitch', 'horizontalGridsNumber', 'verticalGridsNumber', 'horizontalPixelsNumber', 'verticalPixelsNumber', 'gridTiltAngle', 'horizontalSamplingInterval', 'verticalSamplingInterval', 'horizontalMaskCoordinate', 'verticalMaskCoordinate'],
    ],
    'mirror': [
        '',
        '',
        'Mirror',
        False,
    ],
    'obstacle': [
        'srwlib.SRWLOptA("{}", "o", {}, {}, {}, {})',
        ['shape', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
    ],
    'sphericalMirror': [
        'srwlib.SRWLOptMirSph(_r={}, _size_tang={}, _size_sag={}, _nvx={}, _nvy={}, _nvz={}, _tvx={}, _tvy={}, _x={}, _y={})',
        ['radius', 'tangentialSize', 'sagittalSize', 'normalVectorX', 'normalVectorY', 'normalVectorZ', 'tangentialVectorX', 'tangentialVectorY', 'horizontalOffset', 'verticalOffset'],
        'SphMirror',
        True,
    ],
    'toroidalMirror': [
        'srwlib.SRWLOptMirTor(_rt={}, _rs={}, _size_tang={}, _size_sag={}, _x={}, _y={}, _ap_shape="{}", _nvx={}, _nvy={}, _nvz={}, _tvx={}, _tvy={})',
        ['tangentialRadius', 'sagittalRadius', 'tangentialSize', 'sagittalSize', 'horizontalPosition', 'verticalPosition', 'apertureShape', 'normalVectorX', 'normalVectorY', 'normalVectorZ', 'tangentialVectorX', 'tangentialVectorY'],
        'TorMirror',
        True,
    ],
}

#: Where server files and static files are found
_RESOURCE_DIR = template_common.resource_dir(SIM_TYPE)

_PREDEFINED = None

_REPORT_STYLE_FIELDS = ['intensityPlotsWidth', 'intensityPlotsScale', 'colorMap', 'plotAxisX', 'plotAxisY', 'plotAxisY2']

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
        self.z = zipfile.ZipFile(archive_name)
        self.index_dir = None
        self.index_file = None
        self.gaps = None
        self.dat_files = None
        self._find_index_file()
        self._find_dat_files_from_index_file()

    def find_closest_gap(self, gap):
        gap = float(gap)
        indices_previous = []
        indices_next = []
        for i in range(len(self.gaps)):
            if self.gaps[i] <= gap:
                indices_previous.append(i)
            else:
                indices_next.append(i)
        assert indices_previous or indices_next
        idx_previous = indices_previous[-1] if indices_previous else indices_next[0]
        idx_next = indices_next[0] if indices_next else indices_previous[-1]
        idx = idx_previous if abs(self.gaps[idx_previous] - gap) <= abs(self.gaps[idx_next] - gap) else idx_next
        dat_file = self.dat_files[idx]
        dat_content = self._get_file_content(dat_file)
        dat_file_step = float(dat_content[8].split('#')[1].strip())
        dat_file_number_of_points = int(dat_content[9].split('#')[1].strip())
        return round(dat_file_step * dat_file_number_of_points, 6)

    def _find_dat_files_from_index_file(self):
        self.gaps = []
        self.dat_files = []
        for row in self._get_file_content(self.index_file):
            v = row.strip()
            if v:
                v = v.split()
                self.gaps.append(float(v[0]))
                self.dat_files.append(v[3])

    def _find_index_file(self):
        # finds an index file (``*.txt``) in the provided zip-object.
        for f in self.z.namelist():
            if re.search(r'\.txt', f):
                self.index_file = os.path.basename(f)
                self.index_dir = os.path.dirname(f)
                break
        assert self.index_file is not None

    def _get_file_content(self, file_name):
        with self.z.open(os.path.join(self.index_dir, file_name)) as f:
            return self._normalize_eol(f)

    def _normalize_eol(self, file_desc):
        s = file_desc.read().replace('\r\n', '\n').replace('\r', '\n')
        content = s.split('\n')
        return content


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
        if not is_running and report == 'fluxAnimation':
            # let the client know which flux method was used for the output
            data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
            res['method'] = data['models']['fluxAnimation']['method']
        res.update({
            'frameCount': 1,
            'frameId': t,
            'lastUpdateTime': t,
            'percentComplete': status['progress'],
            'particleNumber': status['particle_number'],
            'particleCount': status['total_num_of_particles'],
        })
    return res


def extensions_for_file_type(file_type):
    if file_type == 'mirror':
        return ['*.dat', '*.txt']
    if file_type == 'sample':
        exts = ['tif', 'tiff', 'png', 'bmp', 'gif', 'jpg', 'jpeg']
        exts += [x.upper() for x in exts]
        return ['*.{}'.format(x) for x in exts]
    if file_type == 'undulatorTable':
        return ['*.zip']
    raise RuntimeError('unknown file_type: ', file_type)


def extract_report_data(filename, model_data):
    data, _, allrange, _, _ = uti_plot_com.file_load(filename, multicolumn_data=model_data['report'] in ('brillianceReport', 'trajectoryReport'))
    if model_data['report'] == 'brillianceReport':
        return _extract_brilliance_report(model_data['models']['brillianceReport'], data)
    if model_data['report'] == 'trajectoryReport':
        return _extract_trajectory_report(model_data['models']['trajectoryReport'], data)
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
        'res_spec_se.dat': [['Photon Energy', 'Intensity', 'On-Axis Spectrum from Filament Electron Beam'], ['eV', _intensity_units(is_gaussian, model_data)]],
        'res_spec_me.dat': [['Photon Energy', sValShort, sValType], ['eV', sValUnit]],
        'res_pow.dat': [['Horizontal Position', 'Vertical Position', 'Power Density', 'Power Density'], ['m', 'm', 'W/mm^2']],
        'res_int_se.dat': [['Horizontal Position', 'Vertical Position', before_propagation_name, 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        #TODO(pjm): improve multi-electron label
        'res_int_pr_me.dat': [['Horizontal Position', 'Vertical Position', before_propagation_name, 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        'res_int_pr_se.dat': [['Horizontal Position', 'Vertical Position', 'After Propagation (E={photonEnergy} eV)', 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        _MIRROR_OUTPUT_FILE: [['Horizontal Position', 'Vertical Position', 'Optical Path Difference', 'Optical Path Difference'], ['m', 'm', 'm']],
    })
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


def fixup_old_data(data):
    """Fixup data to match the most recent schema."""
    for m in ('fluxAnimation', 'fluxReport', 'gaussianBeam', 'initialIntensityReport', 'intensityReport', 'mirrorReport', 'powerDensityReport', 'simulation', 'sourceIntensityReport', 'tabulatedUndulator', 'trajectoryReport'):
        if m not in data['models']:
            data['models'][m] = pkcollections.Dict()
        template_common.update_model_defaults(data['models'][m], m, _SCHEMA)
    for m in data['models']:
        if template_common.is_watchpoint(m):
            template_common.update_model_defaults(data['models'][m], 'watchpointReport', _SCHEMA)
    # move sampleFactor to simulation model
    if 'sampleFactor' in data['models']['initialIntensityReport']:
        if 'sampleFactor' not in data['models']['simulation']:
            data['models']['simulation']['sampleFactor'] = data['models']['initialIntensityReport']['sampleFactor']
        for k in data['models']:
            if k == 'sourceIntensityReport' or k == 'initialIntensityReport' or template_common.is_watchpoint(k):
                if 'sampleFactor' in data['models'][k]:
                    del data['models'][k]['sampleFactor']
    # default intensityReport.method based on source type
    if 'method' not in data['models']['intensityReport']:
        if _is_undulator_source(data['models']['simulation']):
            data['models']['intensityReport']['method'] = '1'
        elif _is_dipole_source(data['models']['simulation']):
            data['models']['intensityReport']['method'] = '2'
        else:
            data['models']['intensityReport']['method'] = '0'
    if 'simulationStatus' not in data['models'] or 'state' in data['models']['simulationStatus']:
        data['models']['simulationStatus'] = pkcollections.Dict()
    if 'facility' in data['models']['simulation']:
        del data['models']['simulation']['facility']
    if 'multiElectronAnimation' not in data['models']:
        m = data['models']['initialIntensityReport']
        data['models']['multiElectronAnimation'] = pkcollections.Dict({
            'horizontalPosition': m['horizontalPosition'],
            'horizontalRange': m['horizontalRange'],
            'verticalPosition': m['verticalPosition'],
            'verticalRange': m['verticalRange'],
        })
    template_common.update_model_defaults(data['models']['multiElectronAnimation'], 'multiElectronAnimation', _SCHEMA)
    _fixup_beamline(data)
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
    if 'indexFile' in data.models.tabulatedUndulator:
        del data.models.tabulatedUndulator['indexFile']

    # Fixup electron beam parameters (drift, moments, etc.):
    data = _fixup_electron_beam(data)

    for component in ['horizontal', 'vertical']:
        if '{}DeflectingParameter'.format(component) not in data['models']['undulator']:
            undulator = data['models']['undulator']
            undulator['{}DeflectingParameter'.format(component)] = round(_process_undulator_definition(pkcollections.Dict({
                'undulator_definition': 'B',
                'undulator_parameter': None,
                'amplitude': float(undulator['{}Amplitude'.format(component)]),
                'undulator_period': float(undulator['period']) / 1000.0
            }))['undulator_parameter'], 8)
    if 'effectiveDeflectingParameter' not in  data['models']['undulator']:
        undulator = data['models']['undulator']
        undulator['effectiveDeflectingParameter'] = math.sqrt(undulator['horizontalDeflectingParameter']**2 + \
                                                              undulator['verticalDeflectingParameter']**2)

    if 'folder' not in data['models']['simulation']:
        if data['models']['simulation']['name'] in _EXAMPLE_FOLDERS:
            data['models']['simulation']['folder'] = _EXAMPLE_FOLDERS[data['models']['simulation']['name']]
        else:
            data['models']['simulation']['folder'] = '/'

    for k in ['photonEnergy', 'horizontalPointCount', 'horizontalPosition', 'horizontalRange',
              'sampleFactor', 'samplingMethod', 'verticalPointCount', 'verticalPosition', 'verticalRange']:
        if k not in data['models']['sourceIntensityReport']:
            data['models']['sourceIntensityReport'][k] = data['models']['simulation'][k]

    if 'photonEnergy' not in data['models']['gaussianBeam']:
        data['models']['gaussianBeam']['photonEnergy'] = data['models']['simulation']['photonEnergy']

    if 'length' in data['models']['tabulatedUndulator']:
        tabulated_undulator = data['models']['tabulatedUndulator']
        und_length = _compute_undulator_length(tabulated_undulator)
        if _uses_tabulated_zipfile(data) and 'length' in und_length:
            data['models']['undulator']['length'] = und_length['length']
        del tabulated_undulator['length']

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

    if len(data['models']['postPropagation']) == 9:
        data['models']['postPropagation'] += [0, 0, 0, 0, 0, 0, 0, 0]
        for item_id in data['models']['propagation']:
            for row in data['models']['propagation'][item_id]:
                row += [0, 0, 0, 0, 0, 0, 0, 0]

    if 'brillianceReport' not in data['models']:
        data['models']['brillianceReport'] = {
            "minDeflection": 0.2,
            "initialHarmonic": 1,
            "finalHarmonic": 5,
            "detuning": 0,
            "energyPointCount": 100,
            "reportType": "0",
        }

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
        return _compute_crl_focus(_compute_material_characteristics(data['optical_element'], data['photon_energy']))
    elif data['method'] == 'compute_fiber_characteristics':
        return _compute_material_characteristics(
            _compute_material_characteristics(
                data['optical_element'],
                data['photon_energy'],
                prefix='external',
            ),
            data['photon_energy'],
            prefix='core',
        )
    elif data['method'] == 'compute_delta_atten_characteristics':
        return _compute_material_characteristics(data['optical_element'], data['photon_energy'])
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


def get_mirror_profile_name_list():
    mirror_names = []
    for k in _ITEM_DEF:
        item_def = _ITEM_DEF[k]
        if len(item_def) > 2:
            mirror_names.append(item_def[2])
    return mirror_names


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


def lib_files(data, source_lib):
    """Returns list of auxiliary files

    Args:
        data (dict): simulation db
        source_lib (py.path): directory of source

    Returns:
        list: py.path.local of source files
    """
    res = []
    dm = data.models
    # the mirrorReport.heightProfileFile may be different than the file in the beamline
    report = data.report if 'report' in data else None
    if report == 'mirrorReport':
        res.append(dm['mirrorReport']['heightProfileFile'])
    if _uses_tabulated_zipfile(data):
        if 'tabulatedUndulator' in dm and dm.tabulatedUndulator.magneticFile:
            res.append(dm.tabulatedUndulator.magneticFile)
    if _is_beamline_report(report):
        for m in dm.beamline:
            for k, v in _SCHEMA.model[m.type].items():
                t = v[1]
                if m[k] and t in ['MirrorFile', 'ImageFile']:
                    res.append(m[k])
    return template_common.filename_to_path(res, source_lib)


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
            'mirrorReport.heightProfileFile',
            _lib_file_datetime(data['models']['mirrorReport']['heightProfileFile']),
            'mirrorReport.orientation',
            'mirrorReport.grazingAngle',
            'mirrorReport.heightAmplification',
        ]
    res = _report_fields(data, r) + [
        'electronBeam', 'electronBeamPosition', 'gaussianBeam', 'multipole',
        'simulation.sourceType', 'tabulatedUndulator', 'undulator',
    ]
    if _uses_tabulated_zipfile(data):
        res.append(_lib_file_datetime(data['models']['tabulatedUndulator']['magneticFile']))

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
            'simulation.distanceFromSource',
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
            if item['type'] == 'mirror':
                res.append(_lib_file_datetime(item['heightProfileFile']))
            elif item['type'] == 'sample':
                res.append(_lib_file_datetime(item['imageFile']))
            elif item['type'] == 'watch' and item['id'] == wid:
                break
        if beamline[-1]['id'] == wid:
            res.append('postPropagation')
    return res


def new_simulation(data, new_simulation_data):
    source = new_simulation_data['sourceType']
    data['models']['simulation']['sourceType'] = source
    if source == 'g':
        data['models']['initialIntensityReport']['sampleFactor'] = 0
    elif source == 'm':
        data['models']['intensityReport']['method'] = "2"
    elif _is_tabulated_undulator_source(data['models']['simulation']):
        data['models']['undulator']['length'] = _compute_undulator_length(data['models']['tabulatedUndulator'])['length']
        data['models']['electronBeamPosition']['driftCalculationMethod'] = 'manual'


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
    if data['report'] in ('brillianceReport', 'mirrorReport'):
        return
    #TODO(pjm): only need to rerun extract_report_data() if report style fields have changed
    fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, report_info.run_dir)
    if fn.exists():
        fn.remove()
        output_file = report_info.run_dir.join(get_filename_for_model(data['report']))
        if output_file.exists():
            res = extract_report_data(str(output_file), data)
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


def validate_delete_file(data, filename, file_type):
    """Returns True if the filename is in use by the simulation data."""
    dm = data.models
    if file_type == 'undulatorTable':
        if _is_tabulated_undulator_source(dm.simulation):
            return dm.tabulatedUndulator.magneticFile == filename
        return False
    field = None
    if file_type == 'mirror':
        field = 'MirrorFile'
    elif file_type == 'sample':
        field = 'ImageFile'
    if not field:
        return False
    for m in dm.beamline:
        for k, v in _SCHEMA.model[m.type].items():
            t = v[1]
            if m[k] and t == field:
                if m[k] == filename:
                    return True
    return False


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
    elif extension.lower() in ['tif', 'tiff', 'png', 'bmp', 'gif', 'jpg', 'jpeg', 'npy']:
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
        _generate_parameters_file(data, run_dir=run_dir)
    )


def _add_report_filenames(v):
    for k in _DATA_FILE_FOR_MODEL:
        v['{}Filename'.format(k)] = _DATA_FILE_FOR_MODEL[k]['filename']


def _beamline_element(template, item, fields, propagation, shift='', is_crystal=False):
    el = template.format(*map(lambda x: item[x], fields))
    pp = _propagation_params(propagation[str(item['id'])][0], shift)
    # special case for crystal elements
    if is_crystal:
        el = '''    opCr = {}
    # Set crystal orientation:
    opCr.set_orient({}, {}, {}, {}, {})
    el.append(opCr)'''.format(
        el,
        item['nvx'], item['nvy'], item['nvz'], item['tvx'], item['tvy']
    )
    else:
        el = '{}    el.append({})'.format(shift, el)
    return el, pp


def _calculate_beam_drift(ebeam_position, source_type, undulator_type, undulator_length, undulator_period):
    if ebeam_position['driftCalculationMethod'] == 'auto':
        """Calculate drift for ideal undulator."""
        if _is_idealized_undulator(source_type, undulator_type):
            # initial drift = 1/2 undulator length + 2 periods
            return -0.5 * float(undulator_length) - 2 * float(undulator_period)
        return 0
    return ebeam_position['drift']


def _compute_material_characteristics(model, photon_energy, prefix=''):
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
    if not model['dSpacing']:
        return model
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
    if model['autocomputeVectors'] == 'horizontal':
        preserve_sign(model, 'normalVectorX', math.cos(grazing_angle))
        preserve_sign(model, 'tangentialVectorX', math.sin(grazing_angle))
        model['normalVectorY'] = 0
        model['tangentialVectorY'] = 0
    elif model['autocomputeVectors'] == 'vertical':
        preserve_sign(model, 'normalVectorY', math.cos(grazing_angle))
        preserve_sign(model, 'tangentialVectorY', math.sin(grazing_angle))
        model['normalVectorX'] = 0
        model['tangentialVectorX'] = 0
    return model


def _compute_undulator_length(model):
    if model['undulatorType'] == 'u_i':
        return {}
    zip_file = simulation_db.simulation_lib_dir(SIM_TYPE).join(model['magneticFile'])
    if zip_file.check():
        return {
            'length': MagnMeasZip(str(zip_file)).find_closest_gap(model['gap']),
        }
    return {}


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


def _create_user_model(data, model_name):
    model = data['models'][model_name]
    if model_name == 'tabulatedUndulator':
        model = model.copy()
        model['undulator'] = data['models']['undulator']
    return model


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


def _extract_brilliance_report(model, data):
    x_points = []
    points = []
    for f in data:
        m = re.search('^f(\d+)', f)
        if m:
            x_points.append((np.array(data[f]['data']) * 1000.0).tolist())
            points.append(np.log10(data['e{}'.format(m.group(1))]['data']).tolist())
    return {
        'title': '',
        'y_label': 'Flux (Ph/s/0.1%bw) log10',
        'x_label': 'Photon Energy [eV]',
        'x_range': [np.amin(x_points), np.amax(x_points)],
        'y_range': [np.amin(points), np.amax(points)],
        'x_points': x_points,
        'points': points,
    }


def _extract_trajectory_report(model, data):
    available_axes = {}
    for s in _SCHEMA['enum']['TrajectoryPlotAxis']:
        available_axes[s[0]] = s[1]
    x_points = data[model['plotAxisX']]['data']
    plots = []
    y_range = []

    for f in ('plotAxisY', 'plotAxisY2'):
        if model[f] != 'None':
            points = data[model[f]]['data']
            if y_range:
                y_range = [min(y_range[0], min(points)), max(y_range[1], max(points))]
            else:
                y_range = [min(points), max(points)]
            plots.append({
                'points': points,
                'label': available_axes[model[f]],
                'color': '#ff7f0e' if len(plots) else '#1f77b4',
            })
    return {
        'title': 'Electron Trajectory',
        'x_range': [min(x_points), max(x_points)],
        'x_points': x_points,
        'y_label': '[' + data[model['plotAxisY']]['units'] + ']',
        'x_label': available_axes[model['plotAxisX']] + ' [' + data[model['plotAxisX']]['units'] + ']',
        'y_range': y_range,
        'plots': plots,
    }


def _fixup_beamline(data):
    for item in data['models']['beamline']:
        if item['type'] == 'ellipsoidMirror':
            if 'firstFocusLength' not in item:
                item['firstFocusLength'] = item['position']
        if item['type'] in ['grating', 'ellipsoidMirror', 'sphericalMirror', 'toroidalMirror']:
            if 'grazingAngle' not in item:
                angle = 0
                if item['normalVectorX']:
                    angle = math.acos(abs(float(item['normalVectorX']))) * 1000
                elif item['normalVectorY']:
                    angle = math.acos(abs(float(item['normalVectorY']))) * 1000
                item['grazingAngle'] = angle
        if 'grazingAngle' in item and 'normalVectorX' in item and 'autocomputeVectors' not in item:
            item['autocomputeVectors'] = '1'
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
            if not item['focalDistance']:
                item = _compute_crl_focus(item)
        if item['type'] == 'sample':
            if 'horizontalCenterCoordinate' not in item:
                item['horizontalCenterCoordinate'] = _SCHEMA['model']['sample']['horizontalCenterCoordinate'][2]
                item['verticalCenterCoordinate'] = _SCHEMA['model']['sample']['verticalCenterCoordinate'][2]
            if 'cropArea' not in item:
                for f in ['cropArea', 'areaXStart', 'areaXEnd', 'areaYStart', 'areaYEnd', 'rotateAngle', 'rotateReshape',
                          'cutoffBackgroundNoise', 'backgroundColor', 'tileImage', 'tileRows', 'tileColumns',
                          'shiftX', 'shiftY', 'invert', 'outputImageFormat']:
                    item[f] = _SCHEMA['model']['sample'][f][2]
        if item['type'] in ('crl', 'grating', 'ellipsoidMirror', 'sphericalMirror') and 'horizontalOffset' not in item:
            item['horizontalOffset'] = 0
            item['verticalOffset'] = 0
        if 'autocomputeVectors' in item:
            if item['autocomputeVectors'] == '0':
                item['autocomputeVectors'] = 'none'
            elif item['autocomputeVectors'] == '1':
                item['autocomputeVectors'] = 'vertical' if item['normalVectorX'] == 0 else 'horizontal'


def _fixup_electron_beam(data):
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


def _generate_beamline_optics(report, models, last_id):
    if not _is_beamline_report(report):
        return '    pass'
    res = {
        'el': '    el = []\n',
        'pp': '    pp = []\n',
        'propagation': models['propagation'],
        'height_profile_counter': 1,
        'sample_counter': 1,
    }
    prev = None
    has_item = False
    last_element = False
    want_final_propagation = True

    for item in models['beamline']:
        is_disabled = 'isDisabled' in item and item['isDisabled']
        if last_element:
            if is_disabled:
                continue
            # active element is past the selected watchpoint, don't include postPropagation
            want_final_propagation = False
            break
        if prev:
            has_item = True
            size = item['position'] - prev['position']
            if size != 0:
                res['el'] += '    el.append(srwlib.SRWLOptD({}))\n'.format(size)
                res['pp'] += _propagation_params(res['propagation'][str(prev['id'])][1])
        if is_disabled:
            pass
        else:
            res['el'] += '    # {}: {} {}m\n'.format(item['title'], item['type'], item['position'])
            res['pp'] += '    # {}\n'.format(item['title'])
            if item['type'] == 'sample':
                _generate_sample(res, item)
            elif item['type'] == 'watch':
                if not has_item:
                    res['el'] += '    el.append(srwlib.SRWLOptD({}))'.format(1.0e-16)
                    res['pp'] += _propagation_params(res['propagation'][str(item['id'])][0])
                if last_id and last_id == int(item['id']):
                    last_element = True
            else:
                _generate_item(res, item)
        prev = item
        res['el'] += '\n'

    # final propagation parameters
    if want_final_propagation:
        res['pp'] += '    # final post-propagation\n'
        res['pp'] += _propagation_params(models['postPropagation'])

    return res['el'] + res['pp'] + '    return srwlib.SRWLOptC(el, pp)'


def _generate_item(res, item):
    item_def = _ITEM_DEF[item['type']]
    if item_def[0]:
        el, pp = _beamline_element(item_def[0], item, item_def[1], res['propagation'], is_crystal=item['type'] == 'crystal')
        res['el'] += el
        res['pp'] += pp

    if len(item_def) >= 3:
        el, pp = _height_profile_element(
            item,
            res['propagation'],
            '{}{}'.format(item_def[2], res['height_profile_counter']),
            item_def[3],
        )
        if item_def[0]:
            res['el'] += '\n'
        if pp:
            res['height_profile_counter'] += 1
        res['el'] += el
        res['pp'] += pp


def _generate_parameters_file(data, plot_reports=False, run_dir=None):
    # Process method and magnetic field values for intensity, flux and intensity distribution reports:
    # Intensity report:
    source_type = data['models']['simulation']['sourceType']
    undulator_type = data['models']['tabulatedUndulator']['undulatorType']
    magnetic_field = _process_intensity_reports(source_type, undulator_type)['magneticField']
    data['models']['intensityReport']['magneticField'] = magnetic_field
    data['models']['sourceIntensityReport']['magneticField'] = magnetic_field

    if magnetic_field == 1:
        data['models']['trajectoryReport']['magneticField'] = 1

    report = data['report']
    if report == 'fluxAnimation':
        data['models']['fluxReport'] = data['models'][report].copy()
        if _is_idealized_undulator(source_type, undulator_type) and int(data['models']['fluxReport']['magneticField']) == 2:
            data['models']['fluxReport']['magneticField'] = 1
    elif template_common.is_watchpoint(report) or report == 'sourceIntensityReport':
        # render the watchpoint report settings in the initialIntensityReport template slot
        data['models']['initialIntensityReport'] = data['models'][report].copy()
    if report == 'sourceIntensityReport':
        for k in ['photonEnergy', 'horizontalPointCount', 'horizontalPosition', 'horizontalRange',
                  'sampleFactor', 'samplingMethod', 'verticalPointCount', 'verticalPosition', 'verticalRange']:
            data['models']['simulation'][k] = data['models']['sourceIntensityReport'][k]

    if _is_tabulated_undulator_source(data['models']['simulation']):
        if undulator_type == 'u_i':
            data['models']['tabulatedUndulator']['gap'] = 0.0

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

    if report == 'mirrorReport':
        v['mirrorOutputFilename'] = _MIRROR_OUTPUT_FILE
        return template_common.render_jinja(SIM_TYPE, v, 'mirror.py')
    if report == 'brillianceReport':
        v['brillianceOutputFilename'] = _BRILLIANCE_OUTPUT_FILE
        return template_common.render_jinja(SIM_TYPE, v, 'brilliance.py')

    v['beamlineOptics'] = _generate_beamline_optics(report, data['models'], last_id)

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
    v['setupMagneticMeasurementFiles'] = plot_reports and _uses_tabulated_zipfile(data)
    v['srwMain'] = _generate_srw_main(data, plot_reports)

    # Beamline optics defined through the parameters list:
    v['beamlineOpticsParameters'] = ''
    sample_counter = 1
    for el in data['models']['beamline']:
        if el['type'] == 'sample':
            v['beamlineOpticsParameters'] += '''\n    ['op_sample{0}', 's', '{1}', 'input file of the sample #{0}'],'''.format(sample_counter, el['imageFile'])
            sample_counter += 1

    if run_dir and _uses_tabulated_zipfile(data):
        z = zipfile.ZipFile(str(run_dir.join(v['tabulatedUndulator_magneticFile'])))
        z.extractall(str(run_dir))
        for f in z.namelist():
            if re.search(r'\.txt', f):
                v.magneticMeasurementsDir = os.path.dirname(f) or './'
                v.magneticMeasurementsIndexFile = os.path.basename(f)
                break
    return template_common.render_jinja(SIM_TYPE, v)


def _generate_sample(res, item):
    file_name = 'op_sample{}'.format(res['sample_counter'])
    area = '{}'.format(None if not bool(int(item['cropArea'])) else (item['areaXStart'], item['areaXEnd'], item['areaYStart'], item['areaYEnd']))
    tile = '{}'.format(None if not bool(int(item['tileImage'])) else (item['tileRows'], item['tileColumns']))
    rotate_reshape = '{}'.format(bool(int(item['rotateReshape'])))
    invert = '{}'.format(bool(int(item['invert'])))
    res['sample_counter'] += 1
    el, pp = _beamline_element(
        """srwl_uti_smp.srwl_opt_setup_transm_from_file(
                    file_path=v.""" + file_name + """,
                    resolution={},
                    thickness={},
                    delta={},
                    atten_len={},
                    xc={}, yc={},
                    area=""" + area + """,
                    rotate_angle={}, rotate_reshape=""" + rotate_reshape + """,
                    cutoff_background_noise={},
                    background_color={},
                    tile=""" + tile + """,
                    shift_x={}, shift_y={},
                    invert=""" + invert + """,
                    is_save_images=True,
                    prefix='""" + file_name + """',
                    output_image_format='{}',
                    )""",
        item,
        ['resolution', 'thickness', 'refractiveIndex', 'attenuationLength',
         'horizontalCenterCoordinate', 'verticalCenterCoordinate',
         'rotateAngle',
         'cutoffBackgroundNoise',
         'backgroundColor',
         'shiftX', 'shiftY',
         'outputImageFormat',
        ],
        res['propagation'])
    res['el'] += el
    res['pp'] += pp


def _generate_srw_main(data, plot_reports):
    report = data['report']
    source_type = data['models']['simulation']['sourceType']
    run_all = report == _RUN_ALL_MODEL
    content = [
        'v = srwl_bl.srwl_uti_parse_options(varParam, use_sys_argv={})'.format(plot_reports),
        'source_type, mag = srwl_bl.setup_source(v)',
    ]
    if plot_reports and _uses_tabulated_zipfile(data):
        content.append('setup_magnetic_measurement_files("{}", v)'.format(data['models']['tabulatedUndulator']['magneticFile']))
    if run_all or template_common.is_watchpoint(report) or report == 'multiElectronAnimation':
        content.append('op = set_optics(v)')
    else:
        # set_optics() can be an expensive call for mirrors, only invoke if needed
        content.append('op = None')
    if (run_all and source_type != 'g') or report == 'intensityReport':
        content.append('v.ss = True')
        if plot_reports:
            content.append("v.ss_pl = 'e'")
    if (run_all and source_type not in ('g', 'm')) or report in 'fluxReport':
        content.append('v.sm = True')
        if plot_reports:
            content.append("v.sm_pl = 'e'")
    if (run_all and source_type != 'g') or report == 'powerDensityReport':
        content.append('v.pw = True')
        if plot_reports:
            content.append("v.pw_pl = 'xy'")
    if run_all or report in ['initialIntensityReport', 'sourceIntensityReport']:
        content.append('v.si = True')
        if plot_reports:
            content.append("v.si_pl = 'xy'")
    if (run_all and source_type != 'g') or report == 'trajectoryReport':
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
    if 'distanceFromSource' in data['models']['simulation']:
        return data['models']['simulation']['distanceFromSource']
    return template_common.DEFAULT_INTENSITY_DISTANCE


def _height_profile_element(item, propagation, height_profile_el_name, overwrite_propagation):
    shift = '    '
    if overwrite_propagation:
        if item['heightProfileFile'] and item['heightProfileFile'] != 'None':
            propagation[str(item['id'])][0] = [0, 0, 1.0, 0, 0, 1.0, 1.0, 1.0, 1.0]
        else:
            return '', ''

    dat_file = str(simulation_db.simulation_lib_dir(SIM_TYPE).join(item['heightProfileFile']))
    dimension = find_height_profile_dimension(dat_file)

    res = '{}ifn{} = "{}"\n'.format(shift, height_profile_el_name, item['heightProfileFile'])
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


def _is_beamline_report(report):
    if not report or template_common.is_watchpoint(report) or report in ['multiElectronAnimation', _RUN_ALL_MODEL]:
        return True
    return False


def _is_dipole_source(sim):
    return sim['sourceType'] == 'm'


def _is_gaussian_source(sim):
    return sim['sourceType'] == 'g'


def _is_idealized_undulator(source_type, undulator_type):
    return source_type == 'u' or (source_type == 't' and undulator_type == 'u_i')


def _is_tabulated_undulator_source(sim):
    return sim['sourceType'] == 't'


def _is_tabulated_undulator_with_magnetic_file(source_type, undulator_type):
    return source_type == 't' and undulator_type == 'u_t'


def _is_undulator_source(sim):
    return sim['sourceType'] in ['u', 't']


def _is_user_defined_model(ebeam):
    if 'isReadOnly' in ebeam and ebeam['isReadOnly']:
        return False
    return True


def _lib_file_datetime(filename):
    path = simulation_db.simulation_lib_dir(SIM_TYPE).join(filename)
    if path.exists():
        return path.mtime()
    pkdlog('error, missing lib file: {}', path)
    return 0


def _load_user_model_list(model_name):
    filepath = simulation_db.simulation_lib_dir(SIM_TYPE).join(_USER_MODEL_LIST_FILENAME[model_name])
    if filepath.exists():
        return simulation_db.read_json(filepath)
    _save_user_model_list(model_name, [])
    return _load_user_model_list(model_name)


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
    m = data['model']
    with pkio.save_chdir(simulation_db.tmp_dir()) as d:
        res = py.path.local(fn.purebasename)
        s = srwl_uti_smp.SRWLUtiSmp(
            file_path=str(fn),
            area=None if not bool(int(m['cropArea'])) else (m['areaXStart'], m['areaXEnd'], m['areaYStart'], m['areaYEnd']),
            rotate_angle=float(m['rotateAngle']),
            rotate_reshape=bool(int(m['rotateReshape'])),
            cutoff_background_noise=float(m['cutoffBackgroundNoise']),
            background_color=int(m['backgroundColor']),
            invert=bool(int(m['invert'])),
            tile=None if not bool(int(m['tileImage'])) else (m['tileRows'], m['tileColumns']),
            shift_x=m['shiftX'],
            shift_y=m['shiftY'],
            is_save_images=True,
            prefix=str(res),
            output_image_format=m['outputImageFormat'],
        )
        res += '_processed.{}'.format(m['outputImageFormat'])
        res.check()
    return res


def _process_intensity_reports(source_type, undulator_type):
    # Magnetic field processing:
    return pkcollections.Dict({
        'magneticField': 2 if _is_tabulated_undulator_with_magnetic_file(source_type, undulator_type) else 1,
    })


def _process_undulator_definition(model):
    """Convert K -> B and B -> K."""
    try:
        if model['undulator_definition'] == 'B':
            # Convert B -> K:
            und = SRWLMagFldU([SRWLMagFldH(1, 'v', float(model['amplitude']), 0, 1)], float(model['undulator_period']))
            model['undulator_parameter'] = und.get_K()
        elif model['undulator_definition'] == 'K':
            # Convert K to B:
            und = SRWLMagFldU([], float(model['undulator_period']))
            model['amplitude'] = und.K_2_B(float(model['undulator_parameter']))
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
            ar2d = zoom(ar2d, resize_factor, order=1)
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

def _uses_tabulated_zipfile(data):
    return _is_tabulated_undulator_with_magnetic_file(data['models']['simulation']['sourceType'], data['models']['tabulatedUndulator']['undulatorType'])


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
