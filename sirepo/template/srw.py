# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import crystal
from sirepo import simulation_db
from sirepo.template import template_common
import bnlcrl.pkcli.simulate
import copy
import glob
import math
import numpy as np
import os
import py.path
import re
import srwl_uti_cryst
import srwl_uti_smp
import srwl_uti_src
import srwlib
import traceback
import uti_math
import uti_plot_com
import zipfile
import werkzeug

WANT_BROWSER_FRAME_CACHE = False

#: Simulation type
SIM_TYPE = 'srw'

_ARBITRARY_FIELD_COL_COUNT = 3

_BRILLIANCE_OUTPUT_FILE = 'res_brilliance.dat'

_MIRROR_OUTPUT_FILE = 'res_mirror.dat'

_WATCHPOINT_REPORT_NAME = 'watchpointReport'

_DATA_FILE_FOR_MODEL = pkcollections.Dict({
    'coherenceXAnimation': {'filename': 'res_int_pr_me_dcx.dat', 'dimension': 3},
    'coherenceYAnimation': {'filename': 'res_int_pr_me_dcy.dat', 'dimension': 3},
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

_FILE_TYPE_EXTENSIONS = {
    'mirror': ['dat', 'txt'],
    'sample': ['tif', 'tiff', 'png', 'bmp', 'gif', 'jpg', 'jpeg'],
    'undulatorTable': ['zip'],
    'arbitraryField': ['dat', 'txt'],
}

_LOG_DIR = '__srwl_logs__'

#: Where server files and static files are found
_RESOURCE_DIR = template_common.resource_dir(SIM_TYPE)

_PREDEFINED = None

_REPORT_STYLE_FIELDS = ['intensityPlotsWidth', 'intensityPlotsScale', 'colorMap', 'plotAxisX', 'plotAxisY', 'plotAxisY2', 'copyCharacteristic', 'notes', 'aspectRatio']

_RUN_ALL_MODEL = 'simulation'

_SCHEMA = simulation_db.get_schema(SIM_TYPE)

_TABULATED_UNDULATOR_DATA_DIR = 'tabulatedUndulator'

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
        s = file_desc.read().decode().replace('\r\n', '\n').replace('\r', '\n')
        content = s.split('\n')
        return content


def background_percent_complete(report, run_dir, is_running):
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
        status_files = pkio.sorted_glob(run_dir.join(_LOG_DIR, 'srwl_*.json'))
        if status_files:  # Read the status file if SRW produces the multi-e logs
            progress_file = py.path.local(status_files[-1])
            if progress_file.exists():
                status = simulation_db.read_json(progress_file)
        t = int(filename.mtime())
        if not is_running and report == 'fluxAnimation':
            # let the client know which flux method was used for the output
            data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
            res['method'] = data['models']['fluxAnimation']['method']
        if report == 'multiElectronAnimation':
            # let client know that degree of coherence reports are also available
            res['calcCoherence'] = run_dir.join(get_filename_for_model('coherenceXAnimation')).exists()
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
    # copy results and log for the long-running simulations
    for d in ('fluxAnimation', 'multiElectronAnimation'):
        source_dir = py.path.local(source_path).join(d)
        if source_dir.exists():
            target_dir = py.path.local(target_path).join(d)
            pkio.mkdir_parent(str(target_dir))
            for f in glob.glob(str(source_dir.join('*'))):
                name = os.path.basename(f)
                if re.search(r'^res.*\.dat$', name) or re.search(r'\.json$', name):
                    py.path.local(f).copy(target_dir)
            source_log_dir = source_dir.join(_LOG_DIR)
            if source_log_dir.exists():
                target_log_dir = target_dir.join(_LOG_DIR)
                pkio.mkdir_parent(str(target_log_dir))
                for f in glob.glob(str(source_log_dir.join('*.json'))):
                    py.path.local(f).copy(target_log_dir)


def clean_run_dir(run_dir):
    zip_dir = run_dir.join(_TABULATED_UNDULATOR_DATA_DIR)
    if zip_dir.exists():
        zip_dir.remove()


def extensions_for_file_type(file_type):
    return ['*.{}'.format(x) for x in _FILE_TYPE_EXTENSIONS[file_type]]


def extract_report_data(filename, model_data):
    #TODO(pjm): remove fixup after dcx/dcy files can be read by uti_plot_com
    if re.search(r'/res_int_pr_me_dc.\.dat', filename):
        _fix_file_header(filename)
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
        'res_int_pr_me_dcx.dat': [['Horizontal Position (conj.)', 'Horizontal Position', '', 'Degree of Coherence'], ['m', 'm', '']],
        'res_int_pr_me_dcy.dat': [['Vertical Position (conj.)', 'Vertical Position', '', 'Degree of Coherence'], ['m', 'm', '']],
        'res_int_pr_se.dat': [['Horizontal Position', 'Vertical Position', 'After Propagation (E={photonEnergy} eV)', 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, model_data)]],
        _MIRROR_OUTPUT_FILE: [['Horizontal Position', 'Vertical Position', 'Optical Path Difference', 'Optical Path Difference'], ['m', 'm', 'm']],
    })
    filename = os.path.basename(filename)
    title = file_info[filename][0][2]
    if '{photonEnergy}' in title:
        title = title.format(photonEnergy=model_data['models']['simulation']['photonEnergy'])
    elif '{sourcePhotonEnergy}' in title:
        title = title.format(sourcePhotonEnergy=model_data['models']['sourceIntensityReport']['photonEnergy'])
    y_units = file_info[filename][1][1]
    if y_units == 'm':
        y_units = '[m]'
    else:
        y_units = '({})'.format(y_units)

    subtitle = ''
    if 'report' in model_data:
        schema_enum = []
        model_report = model_data['report']
        this_report = model_data['models'][model_report]
        subtitle_datum = ''
        subtitle_format = '{}'
        if model_report in ['intensityReport']:
            schema_enum = _SCHEMA['enum']['Polarization']
            subtitle_datum = this_report['polarization']
            subtitle_format = '{} Polarization'
        elif model_report in ['initialIntensityReport', 'sourceIntensityReport'] or model_report.startswith('watchpointReport'):
            schema_enum = _SCHEMA['enum']['Characteristic']
            subtitle_datum = this_report['characteristic']
        # Schema enums are indexed by strings, but model data may be numeric
        schema_values = [e for e in schema_enum if e[0] == str(subtitle_datum)]
        if len(schema_values) > 0:
            subtitle = subtitle_format.format(schema_values[0][1])

    info = pkcollections.Dict({
        'title': title,
        'subtitle': subtitle,
        'x_range': [allrange[0], allrange[1]],
        'y_label': _superscript(file_info[filename][0][1] + ' ' + y_units),
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


def fixup_old_data(data):
    """Fixup data to match the most recent schema."""
    for m in ('arbitraryMagField', 'brillianceReport', 'coherenceXAnimation', 'coherenceYAnimation', 'fluxAnimation', 'fluxReport', 'gaussianBeam', 'initialIntensityReport', 'intensityReport', 'mirrorReport', 'powerDensityReport', 'simulation', 'sourceIntensityReport', 'tabulatedUndulator', 'trajectoryReport'):
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
            if k == 'initialIntensityReport' or template_common.is_watchpoint(k):
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
    # default sourceIntensityReport.method based on source type
    if 'method' not in data['models']['sourceIntensityReport']:
        if _is_undulator_source(data['models']['simulation']):
            data['models']['sourceIntensityReport']['method'] = '1'
        elif _is_dipole_source(data['models']['simulation']):
            data['models']['sourceIntensityReport']['method'] = '2'
        elif _is_arbitrary_source(data['models']['simulation']):
            data['models']['sourceIntensityReport']['method'] = '2'
        else:
            data['models']['sourceIntensityReport']['method'] = '0'
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


def get_animation_name(data):
    if data['modelName'] in ('coherenceXAnimation', 'coherenceYAnimation'):
        # degree of coherence reports are calculated out of the multiElectronAnimation directory
        return 'multiElectronAnimation'
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
    elif data['method'] == 'compute_dual_characteristics':
        return _compute_material_characteristics(
            _compute_material_characteristics(
                data['optical_element'],
                data['photon_energy'],
                prefix=data['prefix1'],
            ),
            data['photon_energy'],
            prefix=data['prefix2'],
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


def get_file_list(file_type):
    lib_dir = simulation_db.simulation_lib_dir(SIM_TYPE)
    res = []
    for ext in extensions_for_file_type(file_type):
        for f in glob.glob(str(lib_dir.join(ext))):
            if os.path.isfile(f) and _test_file_type(file_type, f):
                res.append(os.path.basename(f))
    return res


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
    return extract_report_data(str(run_dir.join(get_filename_for_model(data['modelName']))), model_data)


def import_file(request, lib_dir, tmp_dir):
    f = request.files['file']
    input_path = str(tmp_dir.join('import.py'))
    f.save(input_path)
    arguments = str(request.form.get('arguments', ''))
    pkdlog('{}: arguments={}', f.filename, arguments)
    data = simulation_db.default_data(SIM_TYPE)
    data['models']['backgroundImport'] = {
        'inputPath': input_path,
        'arguments': arguments,
        'userFilename': f.filename,
        'libDir': str(simulation_db.simulation_lib_dir(SIM_TYPE)),
    }
    return data


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
            pkdc('dm.tabulatedUndulator.magneticFile',dm.tabulatedUndulator.magneticFile)
            res.append(dm.tabulatedUndulator.magneticFile)
    if _is_arbitrary_source(dm.simulation):
        res.append(dm.arbitraryMagField.magneticFile)
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
    res = template_common.report_fields(data, r, _REPORT_STYLE_FIELDS) + [
        'electronBeam', 'electronBeamPosition', 'gaussianBeam', 'multipole',
        'simulation.sourceType', 'tabulatedUndulator', 'undulator',
        'arbitraryMagField',
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
    sim = data['models']['simulation']
    sim['sourceType'] = new_simulation_data['sourceType']
    if _is_gaussian_source(sim):
        data['models']['initialIntensityReport']['sampleFactor'] = 0
    elif _is_dipole_source(sim):
        data['models']['intensityReport']['method'] = "2"
    elif _is_arbitrary_source(sim):
        data['models']['sourceIntensityReport']['method'] = "2"
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


def prepare_output_file(run_dir, data):
    if data['report'] in ('brillianceReport', 'mirrorReport'):
        return
    #TODO(pjm): only need to rerun extract_report_data() if report style fields have changed
    fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
    if fn.exists():
        fn.remove()
        output_file = run_dir.join(get_filename_for_model(data['report']))
        if output_file.exists():
            res = extract_report_data(str(output_file), data)
            simulation_db.write_result(res, run_dir=run_dir)


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
    if extension not in _FILE_TYPE_EXTENSIONS[file_type]:
        return 'invalid file type: {}'.format(extension)
    if file_type == 'mirror':
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
    elif file_type == 'undulatorTable':
        # undulator magnetic data file
        try:
            _validate_safe_zip(str(path), '.', validate_magnet_data_file)
        except AssertionError as err:
            return err.message
    elif file_type == 'sample':
        filename = os.path.splitext(os.path.basename(str(path)))[0]
        # Save the processed file:
        srwl_uti_smp.SRWLUtiSmp(file_path=str(path), is_save_images=True, prefix=filename)
    if not _test_file_type(file_type, path):
        return 'Column count is incorrect for file type: {}'.format(file_type)
    return None


def validate_magnet_data_file(zf):
    """Validate a zip file containing tabulated magentic data

    Performs the following checks:

        - Only .txt and .dat files are allowed
        - Zip file must contain one and only one .txt file to use as an index
        - The index file must list the data files with the name in the 4th column
        - Zip file must contain only the index file and the data files it lists

    Args:
        zf (zipfile.ZipFile): the zip file to examine
    Returns:
        True if all conditions are met, False otherwise
        A string for debugging purposes
    """
    import collections

    def index_file_name(zf):
        # Apparently pkio.has_file_extension will return true for any extension if fed a directory path ('some_dir/')
        text_files = [f for f in zf.namelist() if not f.endswith('/') and pkio.has_file_extension(f, 'txt')]
        if len(text_files) != 1:
            return None
        return text_files[0]

    # Check against whitelist
    for f in zf.namelist():
        # allow directories
        if f.endswith('/'):
            continue
        if not template_common.file_extension_ok(f, white_list=['txt', 'dat']):
            return False, 'File {} has forbidden type'.format(f)

    file_name_column = 3

    # Assure unique index exists
    if index_file_name(zf) is None:
        return False, 'Zip file has no unique index'

    # Validate correct number of columns (plus other format validations if needed)
    index_file = zf.open(index_file_name(zf))
    lines = index_file.readlines()
    file_names_in_index = []
    for line in lines:
        cols = line.split()
        if len(cols) <= file_name_column:
            return False, 'Index file {} has bad format'.format(index_file_name())
        file_names_in_index.append(cols[file_name_column].decode())

    # Compare index and zip contents
    # Does not include the index itself, nor any directories
    # also extract the filename since the index does not include path info
    file_names_in_zip = map(lambda path: os.path.basename(path),  [f for f in zf.namelist() if not f.endswith('/') and f != index_file_name(zf)])
    files_match = collections.Counter(file_names_in_index) == collections.Counter(file_names_in_zip)
    return files_match, '' if files_match else 'Files in index {} do not match files in zip {}'.format(file_names_in_index, file_names_in_zip)


def write_parameters(data, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    pkdc('write_parameters file to {}'.format(run_dir))
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data, run_dir=run_dir)
    )


def _add_report_filenames(v):
    for k in _DATA_FILE_FOR_MODEL:
        v['{}Filename'.format(k)] = _DATA_FILE_FOR_MODEL[k]['filename']


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
            crystal_parameters = crystal.get_crystal_parameters(material, energy, h, k, l)
            dc = crystal_parameters['d']
            xr0 = crystal_parameters['xr0']
            xi0 = crystal_parameters['xi0']
            xrh = crystal_parameters['xrh']
            xih = crystal_parameters['xih']
        elif re.search('(SRW)', material_raw):
            dc = srwl_uti_cryst.srwl_uti_cryst_pl_sp(millerIndices, material)
            xr0, xi0, xrh, xih = srwl_uti_cryst.srwl_uti_cryst_pol_f(energy, millerIndices, material)
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
        pkdlog('{}: error: {}', material_raw, pkdexc())
        for key in parms_list:
            model[key] = None

    return model


def _compute_crystal_grazing_angle(model):
    model['grazingAngle'] = math.acos(math.sqrt(1 - model['tvx'] ** 2 - model['tvy'] **2)) * 1e3


def _compute_crystal_orientation(model):
    if not model['dSpacing']:
        return model
    parms_list = ['nvx', 'nvy', 'nvz', 'tvx', 'tvy', 'grazingAngle']
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
        orientDataCr = opCr.find_orient(_en=model['energy'], _ang_dif_pl=float(model['diffractionAngle']))[0]
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
        _compute_crystal_grazing_angle(model)
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
    # z is always negative
    model['normalVectorZ'] = - abs(math.sin(grazing_angle))
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
    label = template_common.enum_text(_SCHEMA, 'BrillianceReportType', model['reportType'])
    if model['reportType'] in ('3', '4'):
        label += ' [rad]'
    elif model['reportType'] in ('5', '6'):
        label += ' [m]'
    x_points = []
    points = []
    scale_adjustment = 1000.0
    if 'brightnessComponent' in model and model['brightnessComponent'] == 'spectral-detuning':
        scale_adjustment = 1.0
    for f in data:
        m = re.search('^f(\d+)', f)
        if m:
            x_points.append((np.array(data[f]['data']) * scale_adjustment).tolist())
            points.append(data['e{}'.format(m.group(1))]['data'])
    title = template_common.enum_text(_SCHEMA, 'BrightnessComponent', model['brightnessComponent'])
    if model['brightnessComponent'] == 'k-tuning':
        if model['initialHarmonic'] == model['finalHarmonic']:
            title += ', Harmonic {}'.format(model['initialHarmonic'])
        else:
            title += ', Harmonic {} - {}'.format(model['initialHarmonic'], model['finalHarmonic'])
    else:
        title += ', Harmonic {}'.format(model['harmonic'])

    return {
        'title': title,
        'y_label': label,
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
                #TODO(pjm): refactor with template_common.compute_plot_color_and_range()
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


def _find_closest_angle(angle, allowed_angles):
    """Find closest string value from the input list to
       the specified angle (in radians)."""

    def wrap(ang):
        """Convert an angle to constraint it between -pi and pi.
           See https://stackoverflow.com/a/29237626/4143531 for details.
        """
        return np.arctan2(np.sin(ang), np.cos(ang))

    angles_array = np.array([float(x) for x in allowed_angles])
    threshold = np.min(np.diff(angles_array))
    idx = np.where(np.abs(wrap(angle) - angles_array) < threshold / 2.0)[0][0]
    return allowed_angles[idx]


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

        if item['type'] == 'crystal':
            if 'diffractionAngle' not in item:
                allowed_angles = [x[0] for x in _SCHEMA['enum']['DiffractionPlaneAngle']]
                item['diffractionAngle'] = _find_closest_angle(item['grazingAngle'] or 0, allowed_angles)
                if item['tvx'] == '':
                    item['tvx'] = item['tvy'] = 0
                _compute_crystal_grazing_angle(item)

        if item['type'] == 'sample':
            if 'horizontalCenterCoordinate' not in item:
                item['horizontalCenterCoordinate'] = _SCHEMA['model']['sample']['horizontalCenterCoordinate'][2]
                item['verticalCenterCoordinate'] = _SCHEMA['model']['sample']['verticalCenterCoordinate'][2]
            if 'cropArea' not in item:
                for f in ['cropArea', 'areaXStart', 'areaXEnd', 'areaYStart', 'areaYEnd', 'rotateAngle', 'rotateReshape',
                          'cutoffBackgroundNoise', 'backgroundColor', 'tileImage', 'tileRows', 'tileColumns',
                          'shiftX', 'shiftY', 'invert', 'outputImageFormat']:
                    item[f] = _SCHEMA['model']['sample'][f][2]
            if 'transmissionImage' not in item:
                item['transmissionImage'] = _SCHEMA['model']['sample']['transmissionImage'][2]
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


def _fix_file_header(filename):
    # fixes file header for coherenceXAnimation and coherenceYAnimation reports
    rows = []
    with pkio.open_text(filename) as f:
        for line in f:
            rows.append(line)
            if len(rows) == 10:
                if rows[4] == rows[7]:
                    # already fixed up
                    return
                if re.search(r'^\#0 ', rows[4]):
                    rows[4] = rows[7]
                    rows[5] = rows[8]
                    rows[6] = rows[9]
                else:
                    rows[7] = rows[4]
                    rows[8] = rows[5]
                    rows[9] = rows[6]
    pkio.write_text(filename, ''.join(rows))


def _generate_beamline_optics(report, models, last_id):
    if not _is_beamline_report(report):
        return '    pass', ''
    has_beamline_elements = len(models.beamline) > 0
    if has_beamline_elements and not last_id:
        last_id = models.beamline[-1].id
    names = []
    items = []
    prev = None
    propagation = models.propagation
    max_name_size = 0

    for item in models.beamline:
        is_disabled = 'isDisabled' in item and item.isDisabled
        name = _safe_beamline_item_name(item.title, names)
        max_name_size = max(max_name_size, len(name))

        if prev:
            size = item.position - prev.position
            if size != 0:
                # add a drift
                drift_name = _safe_beamline_item_name('{}_{}'.format(prev.name, name), names)
                max_name_size = max(max_name_size, len(drift_name))
                names.append(drift_name)
                items.append(pkcollections.Dict({
                    'name': drift_name,
                    'type': 'drift',
                    'position': prev.position,
                    'propagation': prev.drift_propagation,
                    'length': size,
                }))
        pp = propagation[str(item.id)]
        item.propagation = pp[0]
        item.drift_propagation = pp[1]
        item.name = name
        if not is_disabled:
            if item.type == 'watch' and not len(items):
                # first item is a watch, insert a 0 length drift in front
                items.append(pkcollections.Dict({
                    'name': 'zero_drift',
                    'type': 'drift',
                    'position': item.position,
                    'propagation': item.propagation,
                    'length': 0,
                }))
                names.append(items[-1].name)
            if 'heightProfileFile' in item:
                item.heightProfileDimension = _height_profile_dimension(item)
            items.append(item)
            names.append(name)
        if int(last_id) == int(item.id):
            break
        prev = item
    args = {
        'items': items,
        'names': names,
        'postPropagation': models.postPropagation,
        'wantPostPropagation': has_beamline_elements and (int(last_id) == int(models.beamline[-1].id)),
        'maxNameSize': max_name_size,
        'nameMap': {
            'apertureShape': 'ap_shape',
            'asymmetryAngle': 'ang_as',
            'attenuationLength': 'atten_len',
            'complementaryAttenuationLength': 'atLen2',
            'complementaryRefractiveIndex': 'delta2',
            'coreAttenuationLength': 'atten_len_core',
            'coreDiameter': 'diam_core',
            'coreRefractiveIndex': 'delta_core',
            'crystalThickness': 'tc',
            'dSpacing': 'd_sp',
            'diffractionOrder': 'm',
            'externalAttenuationLength': 'atten_len_ext',
            'externalRefractiveIndex': 'delta_ext',
            'firstFocusLength': 'p',
            'focalLength': 'q',
            'focalPlane': 'foc_plane',
            'grazingAngle': 'ang',
            'gridShape': 'grid_sh',
            'grooveDensity0': 'grDen',
            'grooveDensity1': 'grDen1',
            'grooveDensity2': 'grDen2',
            'grooveDensity3': 'grDen3',
            'grooveDensity4': 'grDen4',
            'heightAmplification': 'amp_coef',
            'heightProfileFile': 'hfn',
            'horizontalApertureSize': 'apert_h',
            'horizontalCenterPosition': 'xc',
            'horizontalFocalLength': 'Fx',
            'horizontalGridDimension': 'grid_dx',
            'horizontalGridPitch': 'pitch_x',
            'horizontalGridsNumber': 'grid_nx',
            'horizontalMaskCoordinate': 'mask_x0',
            'horizontalOffset': 'x',
            'horizontalPixelsNumber': 'mask_Nx',
            'horizontalSamplingInterval': 'hx',
            'horizontalSize': 'Dx',
            'horizontalTransverseSize': 'size_x',
            'imageFile': 'file_path',
            'length': 'L',
            'mainAttenuationLength': 'atLen1',
            'mainRefractiveIndex': 'delta1',
            'maskThickness': 'thick',
            'normalVectorX': 'nvx',
            'normalVectorY': 'nvy',
            'normalVectorZ': 'nvz',
            'numberOfLenses': 'n',
            'numberOfZones': 'nZones',
            'orientation': 'dim',
            'outerRadius': 'rn',
            'radius': 'r',
            'refractiveIndex': 'delta',
            'sagittalRadius': 'rs',
            'sagittalSize': 'size_sag',
            'tangentialRadius': 'rt',
            'tangentialSize': 'size_tang',
            'tangentialVectorX': 'tvx',
            'tangentialVectorY': 'tvy',
            'thickness': 'thick',
            'tipRadius': 'r_min',
            'tipWallThickness': 'wall_thick',
            'transmissionImage': 'extTransm',
            'verticalApertureSize': 'apert_v',
            'verticalCenterPosition': 'yc',
            'verticalFocalLength': 'Fy',
            'verticalGridDimension': 'grid_dy',
            'verticalGridPitch': 'pitch_y',
            'verticalGridsNumber': 'grid_ny',
            'verticalMaskCoordinate': 'mask_y0',
            'verticalOffset': 'y',
            'verticalPixelsNumber': 'mask_Ny',
            'verticalSamplingInterval': 'hy',
            'verticalSize': 'Dy',
            'verticalTransverseSize': 'size_y',
        },
    }
    optics = template_common.render_jinja(SIM_TYPE, args, 'beamline_optics.py')
    prop = template_common.render_jinja(SIM_TYPE, args, 'beamline_parameters.py')
    return optics, prop


def _generate_parameters_file(data, plot_reports=False, run_dir=None):
    # Process method and magnetic field values for intensity, flux and intensity distribution reports:
    # Intensity report:
    source_type = data['models']['simulation']['sourceType']
    undulator_type = data['models']['tabulatedUndulator']['undulatorType']
    magnetic_field = _process_intensity_reports(source_type, undulator_type)['magneticField']
    data['models']['intensityReport']['magneticField'] = magnetic_field
    data['models']['sourceIntensityReport']['magneticField'] = magnetic_field
    data['models']['trajectoryReport']['magneticField'] = magnetic_field
    data['models']['powerDensityReport']['magneticField'] = magnetic_field
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
    if report == 'multiElectronAnimation':
        last_id = data['models']['multiElectronAnimation']['watchpointId']
    if int(data['models']['simulation']['samplingMethod']) == 2:
        data['models']['simulation']['sampleFactor'] = 0
    res, v = template_common.generate_parameters_file(data)

    v['rs_type'] = source_type
    if _is_idealized_undulator(source_type, undulator_type):
        v['rs_type'] = 'u'

    if report == 'mirrorReport':
        v['mirrorOutputFilename'] = _MIRROR_OUTPUT_FILE
        return template_common.render_jinja(SIM_TYPE, v, 'mirror.py')
    if report == 'brillianceReport':
        v['brillianceOutputFilename'] = _BRILLIANCE_OUTPUT_FILE
        return template_common.render_jinja(SIM_TYPE, v, 'brilliance.py')
    if report == 'backgroundImport':
        return template_common.render_jinja(SIM_TYPE, v, 'import.py')
    v['beamlineOptics'], v['beamlineOpticsParameters'] = _generate_beamline_optics(report, data['models'], last_id)

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

    if run_dir and _uses_tabulated_zipfile(data):
        src_zip = str(run_dir.join(v['tabulatedUndulator_magneticFile']))
        target_dir = str(run_dir.join(_TABULATED_UNDULATOR_DATA_DIR))
        # The MagnMeasZip class defined above has convenient properties we can use here
        mmz = MagnMeasZip(src_zip)
        zindex = _zip_path_for_file(mmz.z, mmz.index_file)
        zdata = map(lambda fn: _zip_path_for_file(mmz.z, fn), mmz.dat_files)
        # extract only the index file and the data files it lists
        mmz.z.extract(zindex, target_dir)
        for df in zdata:
            mmz.z.extract(df, target_dir)
        v.magneticMeasurementsDir = _TABULATED_UNDULATOR_DATA_DIR + '/' + mmz.index_dir
        v.magneticMeasurementsIndexFile = mmz.index_file
    return res + template_common.render_jinja(SIM_TYPE, v)


def _generate_srw_main(data, plot_reports):
    report = data['report']
    source_type = data['models']['simulation']['sourceType']
    run_all = report == _RUN_ALL_MODEL
    content = [
        'v = srwl_bl.srwl_uti_parse_options(varParam, use_sys_argv={})'.format(plot_reports),
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
        #TODO(pjm): work-around for #1593
        content.append('mag = None')
        content.append("if v.rs_type == 'm':")
        for line in (
                'mag = srwlib.SRWLMagFldC()',
                'mag.arXc.append(0)',
                'mag.arYc.append(0)',
                'mag.arMagFld.append(srwlib.SRWLMagFldM(v.mp_field, v.mp_order, v.mp_distribution, v.mp_len))',
                'mag.arZc.append(v.mp_zc)',
        ):
            content.append('    {}'.format(line))
        content.append('srwl_bl.SRWLBeamline(_name=v.name, _mag_approx=mag).calc_all(v, op)')
    return '\n'.join(['    {}'.format(x) for x in content])


def _get_first_element_position(data):
    beamline = data['models']['beamline']
    if len(beamline):
        return beamline[0]['position']
    if 'distanceFromSource' in data['models']['simulation']:
        return data['models']['simulation']['distanceFromSource']
    return template_common.DEFAULT_INTENSITY_DISTANCE


def _height_profile_dimension(item):
    """Find the dimension of the provided height profile .dat file.
    1D files have 2 columns, 2D - 8 columns.
    """
    dimension = 0
    if item['heightProfileFile'] and item['heightProfileFile'] != 'None':
        dat_file = str(simulation_db.simulation_lib_dir(SIM_TYPE).join(item['heightProfileFile']))
        with open(dat_file, 'r') as f:
            header = f.readline().strip().split()
            dimension = 1 if len(header) == 2 else 2
    return dimension


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


def _is_arbitrary_source(sim):
    return sim['sourceType'] == 'a'


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
    try:
        if filepath.exists():
            return simulation_db.read_json(filepath)
    except Exception:
        pkdlog('user list read failed, resetting contents: {}', filepath)
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
    # This should just be a basename, but this ensures it.
    path = str(simulation_db.simulation_lib_dir(data.simulationType).join(werkzeug.secure_filename(data.baseImage)))
    m = data['model']
    with pkio.save_chdir(simulation_db.tmp_dir()):
        s = srwl_uti_smp.SRWLUtiSmp(
            file_path=path,
            area=None if not int(m['cropArea']) else (m['areaXStart'], m['areaXEnd'], m['areaYStart'], m['areaYEnd']),
            rotate_angle=float(m['rotateAngle']),
            rotate_reshape=int(m['rotateReshape']),
            cutoff_background_noise=float(m['cutoffBackgroundNoise']),
            background_color=int(m['backgroundColor']),
            invert=int(m['invert']),
            tile=None if not int(m['tileImage']) else (m['tileRows'], m['tileColumns']),
            shift_x=m['shiftX'],
            shift_y=m['shiftY'],
            is_save_images=True,
            prefix=str(py.path.local()),
            output_image_format=m['outputImageFormat'],
        )
        return py.path.local(s.processed_image_name)


def _process_intensity_reports(source_type, undulator_type):
    # Magnetic field processing:
    return pkcollections.Dict({
        'magneticField': 2 if source_type == 'a' or _is_tabulated_undulator_with_magnetic_file(source_type, undulator_type) else 1,
    })


def _process_undulator_definition(model):
    """Convert K -> B and B -> K."""
    try:
        if model['undulator_definition'] == 'B':
            # Convert B -> K:
            und = srwlib.SRWLMagFldU([srwlib.SRWLMagFldH(1, 'v', float(model['amplitude']), 0, 1)], float(model['undulator_period']))
            model['undulator_parameter'] = und.get_K()
        elif model['undulator_definition'] == 'K':
            # Convert K to B:
            und = srwlib. SRWLMagFldU([], float(model['undulator_period']))
            model['amplitude'] = und.K_2_B(float(model['undulator_parameter']))
        return model
    except Exception:
        return model


def _remap_3d(info, allrange, z_label, z_units, width_pixels, scale='linear'):
    x_range = [allrange[3], allrange[4], allrange[5]]
    y_range = [allrange[6], allrange[7], allrange[8]]
    ar2d = info['points']

    totLen = int(x_range[2] * y_range[2])
    n = len(ar2d) if totLen > len(ar2d) else totLen
    ar2d = np.reshape(ar2d[0:n], (y_range[2], x_range[2]))

    if scale != 'linear':
        ar2d[np.where(ar2d <= 0.)] = 1.e-23
        ar2d = getattr(np, scale)(ar2d)

    # rescale width and height to maximum of width_pixels
    if width_pixels and (width_pixels < x_range[2] or width_pixels < y_range[2]):
        x_resize = 1.0
        y_resize = 1.0
        if width_pixels < x_range[2]:
            x_resize = float(width_pixels) / float(x_range[2])
        if width_pixels < y_range[2]:
            y_resize = float(width_pixels) / float(y_range[2])
        pkdlog('Size before: {}  Dimensions: {}, Resize: [{}, {}]', ar2d.size, ar2d.shape, y_resize, x_resize)
        try:
            from scipy import ndimage
            ar2d = ndimage.zoom(ar2d, [y_resize, x_resize], order=1)
            # Remove for #670, this may be required for certain reports?
            # if scale == 'linear':
            #     ar2d[np.where(ar2d < 0.)] = 0.0
            pkdlog('Size after : {}  Dimensions: {}', ar2d.size, ar2d.shape)
            x_range[2] = ar2d.shape[1]
            y_range[2] = ar2d.shape[0]
        except Exception:
            pkdlog('Cannot resize the image - scipy.ndimage.zoom() cannot be imported.')
            pass
    z_label = z_label
    if z_units:
        z_label += ' [' + z_units + ']'
    return pkcollections.Dict({
        'x_range': x_range,
        'y_range': y_range,
        'x_label': info['x_label'],
        'y_label': info['y_label'],
        'z_label': _superscript(z_label),
        'title': info['title'],
        'subtitle': info['subtitle'],
        'z_matrix': ar2d.tolist(),
    })


def _safe_beamline_item_name(name, names):
    name = re.sub(r'\W+', '_', name)
    name = re.sub(r'_+', '_', name)
    name = re.sub(r'^_|_$', '', name)
    name = re.sub(r'^_+', '', name)
    name = re.sub(r'_+$', '', name)
    name = re.sub(r'^op_', '', name)
    if not name or name == 'fin':
        name = 'element'
    idx = 2
    current = name
    while current in names:
        current = '{}{}'.format(name, idx)
        idx += 1
    return current


def _save_user_model_list(model_name, beam_list):
    pkdc('saving {} list', model_name)
    filepath = simulation_db.simulation_lib_dir(SIM_TYPE).join(_USER_MODEL_LIST_FILENAME[model_name])
    #TODO(pjm): want atomic replace?
    simulation_db.write_json(filepath, beam_list)


def _superscript(val):
    return re.sub(r'\^2', u'\u00B2', val)


def _test_file_type(file_type, file_path):
    # special handling for mirror and arbitraryField - scan for first data row and count columns
    if file_type not in ('mirror', 'arbitraryField'):
        return True
    with pkio.open_text(str(file_path)) as f:
        for line in f:
            if re.search(r'^\s*#', line):
                continue
            col_count = len(line.split())
            if col_count > 0:
                if file_type == 'arbitraryField':
                    return col_count == _ARBITRARY_FIELD_COL_COUNT
                return col_count != _ARBITRARY_FIELD_COL_COUNT
    return False


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

def _validate_safe_zip(zip_file_name, target_dir='.', *args):
    """Determine whether a zip file is safe to extract from

    Performs the following checks:

        - Each file must end up at or below the target directory
        - Files must be 100MB or smaller
        - If possible to determine, disallow "non-regular" and executable files
        - Existing files cannot be overwritten

    Args:
        zip_file_name (str): name of the zip file to examine
        target_dir (str): name of the directory to extract into (default to current directory)
        *args: list of validator functions taking a zip file as argument and returning True or False and a string
    Throws:
        AssertionError if any test fails, otherwise completes silently
    """
    import zipfile
    import os

    def path_is_sub_path(path, dir_name):
        real_dir = os.path.realpath(dir_name)
        end_path = os.path.realpath(real_dir + '/' + path)
        return end_path.startswith(real_dir)

    def file_exists_in_dir(file_name, dir_name):
        return os.path.exists(os.path.realpath(dir_name + '/' + file_name))

    def file_attrs_ok(attrs):

        # ms-dos attributes only use two bytes and don't contain much useful info, so pass them
        if attrs < 2 << 16:
            return True

        # UNIX file attributes live in the top two bytes
        mask = attrs >> 16
        is_file_or_dir = mask & (0o0100000 | 0o0040000) != 0
        no_exec = mask & (0o0000100 | 0o0000010 | 0o0000001) == 0

        return is_file_or_dir and no_exec

    # 100MB
    max_file_size = 100000000

    zip_file = zipfile.ZipFile(zip_file_name)

    for f in zip_file.namelist():

        i = zip_file.getinfo(f)
        s = i.file_size
        attrs = i.external_attr

        assert path_is_sub_path(f, target_dir), 'Cannot extract {} above target directory'.format(f)
        assert s <= max_file_size, '{} too large ({} > {})'.format(f, str(s), str(max_file_size))
        assert file_attrs_ok(attrs), '{} not a normal file or is executable'.format(f)
        assert not file_exists_in_dir(f, target_dir), 'Cannot overwrite file {} in target directory {}'.format(f, target_dir)

    for validator in args:
        res, err_string = validator(zip_file)
        assert res, '{} failed validator: {}'.format(os.path.basename(zip_file_name), err_string)


def _zip_path_for_file(zf, file_to_find):
    """Find the full path of the specified file within the zip.

    For a zip zf containing:
        foo1
        foo2
        bar/
        bar/foo3

    _zip_path_for_file(zf, 'foo3') will return 'bar/foo3'

    Args:
        zf(zipfile.ZipFile): the zip file to examine
        file_to_find (str): name of the file to find

    Returns:
        The first path in the zip that matches the file name, or None if no match is found
    """
    import os

    # Get the base file names from the zip (directories have a basename of '')
    file_names_in_zip = map(lambda path: os.path.basename(path),  zf.namelist())
    return zf.namelist()[file_names_in_zip.index(file_to_find)]

_init()
