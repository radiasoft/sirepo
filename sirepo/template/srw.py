# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkinspect
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import crystal
from sirepo import simulation_db
from sirepo.template import srw_common
from sirepo.template import template_common
import bnlcrl.pkcli.simulate
import copy
import glob
import math
import numpy as np
import os
import py.path
import pykern.pkjson
import re
import sirepo.mpi
import sirepo.sim_data
import sirepo.template.srw_fixup
import sirepo.uri_router
import srwl_uti_cryst
import srwl_uti_smp
import srwl_uti_src
import srwlib
import time
import traceback
import uti_io
import uti_math
import uti_plot_com
import werkzeug
import zipfile

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

WANT_BROWSER_FRAME_CACHE = False

PARSED_DATA_ATTR = 'srwParsedData'

_BRILLIANCE_OUTPUT_FILE = 'res_brilliance.dat'

_MIRROR_OUTPUT_FILE = 'res_mirror.dat'

_DATA_FILE_FOR_MODEL = PKDict({
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
    'beamline3DReport': {'filename': 'beamline_orient.dat', 'dimension': 2},
    _SIM_DATA.WATCHPOINT_REPORT: {'filename': 'res_int_pr_se.dat', 'dimension': 3},
})

_LOG_DIR = '__srwl_logs__'

_TABULATED_UNDULATOR_DATA_DIR = 'tabulatedUndulator'

_USER_MODEL_LIST_FILENAME = PKDict({
    'electronBeam': '_user_beam_list.json',
    'tabulatedUndulator': '_user_undulator_list.json',
})

_IMPORT_PYTHON_POLLS = 60

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
    res = PKDict({
        'percentComplete': 0,
        'frameCount': 0,
    })
    filename = run_dir.join(get_filename_for_model(report))
    if filename.exists():
        status = PKDict({
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
            'frameCount': t + 1,
            'frameIndex': t,
            'lastUpdateTime': t,
            'percentComplete': status['progress'],
            'particleNumber': status['particle_number'],
            'particleCount': status['total_num_of_particles'],
        })
    return res


def calculate_beam_drift(ebeam_position, source_type, undulator_type, undulator_length, undulator_period):
    if ebeam_position['driftCalculationMethod'] == 'auto':
        """Calculate drift for ideal undulator."""
        if _SIM_DATA.srw_is_idealized_undulator(source_type, undulator_type):
            # initial drift = 1/2 undulator length + 2 periods
            return -0.5 * float(undulator_length) - 2 * float(undulator_period)
        return 0
    return ebeam_position['drift']


def compute_crl_focus(model):
    d = bnlcrl.pkcli.simulate.calc_ideal_focus(
        radius=float(model['tipRadius']) * 1e-6,  # um -> m
        n=model['numberOfLenses'],
        delta=model['refractiveIndex'],
        p0=model['position']
    )
    model['focalDistance'] = d['ideal_focus']
    model['absoluteFocusPosition'] = d['p1_ideal_from_source']
    return model


def compute_undulator_length(model):
    if model['undulatorType'] == 'u_i':
        return PKDict()
    if _SIM_DATA.lib_file_exists(model['magneticFile']):
        z = _SIM_DATA.lib_file_abspath(model['magneticFile'])
        return PKDict(
            length=_SIM_DATA.srw_format_float(
                MagnMeasZip(str(z)).find_closest_gap(model['gap']),
            ),
        )
    return PKDict()


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


def extract_report_data(filename, sim_in):
    r = sim_in.report
    m = sim_in.models
    #TODO(pjm): remove fixup after dcx/dcy files can be read by uti_plot_com
    if re.search(r'/res_int_pr_me_dc.\.dat', filename):
        _fix_file_header(filename)
    data, _, allrange, _, _ = uti_plot_com.file_load(filename, multicolumn_data=r in ('brillianceReport', 'trajectoryReport'))
    if r == 'brillianceReport':
        return _extract_brilliance_report(m['brillianceReport'], data)
    if r == 'trajectoryReport':
        return _extract_trajectory_report(m['trajectoryReport'], data)
    flux_type = 1
    if 'report' in sim_in and r in ['fluxReport', 'fluxAnimation']:
        flux_type = int(m[r]['fluxType'])
    sValShort = 'Flux'; sValType = 'Flux through Finite Aperture'; sValUnit = 'ph/s/.1%bw'
    if flux_type == 2:
        sValShort = 'Intensity'
        sValUnit = 'ph/s/.1%bw/mm^2'
    is_gaussian = False
    if 'models' in sim_in and _SIM_DATA.srw_is_gaussian_source(m['simulation']):
        is_gaussian = True
    #TODO(pjm): move filename and metadata to a constant, using _DATA_FILE_FOR_MODEL
    if r == 'initialIntensityReport':
        before_propagation_name = 'Before Propagation (E={photonEnergy} eV)'
    elif r == 'sourceIntensityReport':
        before_propagation_name = 'E={sourcePhotonEnergy} eV'
    else:
        before_propagation_name = 'E={photonEnergy} eV'
    file_info = PKDict({
        'res_spec_se.dat': [['Photon Energy', 'Intensity', 'On-Axis Spectrum from Filament Electron Beam'], ['eV', _intensity_units(is_gaussian, sim_in)]],
        'res_spec_me.dat': [['Photon Energy', sValShort, sValType], ['eV', sValUnit]],
        'res_pow.dat': [['Horizontal Position', 'Vertical Position', 'Power Density', 'Power Density'], ['m', 'm', 'W/mm^2']],
        'res_int_se.dat': [['Horizontal Position', 'Vertical Position', before_propagation_name, 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, sim_in)]],
        #TODO(pjm): improve multi-electron label
        'res_int_pr_me.dat': [['Horizontal Position', 'Vertical Position', before_propagation_name, 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, sim_in)]],
        'res_int_pr_me_dcx.dat': [['(X1 + X2) / 2', '(X1 - X2) / 2', '', 'Degree of Coherence'], ['m', 'm', '']],
        'res_int_pr_me_dcy.dat': [['(Y1 + Y2) / 2', '(Y1 - Y2) / 2', '', 'Degree of Coherence'], ['m', 'm', '']],
        'res_int_pr_se.dat': [['Horizontal Position', 'Vertical Position', 'After Propagation (E={photonEnergy} eV)', 'Intensity'], ['m', 'm', _intensity_units(is_gaussian, sim_in)]],
        _MIRROR_OUTPUT_FILE: [['Horizontal Position', 'Vertical Position', 'Optical Path Difference', 'Optical Path Difference'], ['m', 'm', 'm']],
    })
    filename = os.path.basename(filename)
    title = file_info[filename][0][2]
    if '{photonEnergy}' in title:
        title = title.format(photonEnergy=m['simulation']['photonEnergy'])
    elif '{sourcePhotonEnergy}' in title:
        title = title.format(sourcePhotonEnergy=m['sourceIntensityReport']['photonEnergy'])
    y_units = file_info[filename][1][1]
    if y_units == 'm':
        y_units = '[m]'
    else:
        y_units = '({})'.format(y_units)

    subtitle = ''
    schema_enum = []
    report_model = m[r]
    subtitle_datum = ''
    subtitle_format = '{}'
    if r in ('intensityReport',):
        schema_enum = _SCHEMA['enum']['Polarization']
        subtitle_datum = report_model['polarization']
        subtitle_format = '{} Polarization'
    elif r in ('initialIntensityReport', 'sourceIntensityReport') or _SIM_DATA.is_watchpoint(r):
        schema_enum = _SCHEMA['enum']['Characteristic']
        subtitle_datum = report_model['characteristic']
    # Schema enums are indexed by strings, but model data may be numeric
    schema_values = [e for e in schema_enum if e[0] == str(subtitle_datum)]
    if len(schema_values) > 0:
        subtitle = subtitle_format.format(schema_values[0][1])
    info = PKDict({
        'title': title,
        'subtitle': subtitle,
        'x_range': [allrange[0], allrange[1]],
        'y_label': _superscript(file_info[filename][0][1] + ' ' + y_units),
        'x_label': file_info[filename][0][0] + ' [' + file_info[filename][1][0] + ']',
        'x_units': file_info[filename][1][0],
        'y_units': file_info[filename][1][1],
        'points': data,
    })
    rep_name = _SIM_DATA.WATCHPOINT_REPORT if _SIM_DATA.is_watchpoint(r) else r
    if _DATA_FILE_FOR_MODEL[rep_name]['dimension'] == 3:
        width_pixels = int(report_model['intensityPlotsWidth'])
        rotate_angle = report_model.get('rotateAngle', 0)
        rotate_reshape = report_model.get('rotateReshape', '0')
        info = _remap_3d(info, allrange, file_info[filename][0][3], file_info[filename][1][2], width_pixels, rotate_angle, rotate_reshape)
    return info


def fixup_old_data(data):
    import sirepo.template.srw_fixup

    return sirepo.template.srw_fixup.do(pkinspect.this_module(), data)


def get_application_data(data, **kwargs):
    if data['method'] == 'model_list':
        res = []
        model_name = data['model_name']
        if model_name == 'electronBeam':
            res.extend(get_predefined_beams())
        res.extend(_load_user_model_list(model_name))
        if model_name == 'electronBeam':
            for beam in res:
                srw_common.process_beam_parameters(beam)
        return PKDict({
            'modelList': res
        })
    if data['method'] == 'delete_user_models':
        return _delete_user_models(data['electron_beam'], data['tabulated_undulator'])
    if data['method'] == 'compute_grazing_orientation':
        return _compute_grazing_orientation(data['optical_element'])
    elif data['method'] == 'compute_crl_characteristics':
        return compute_crl_focus(_compute_material_characteristics(data['optical_element'], data['photon_energy']))
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
    elif data['method'] == 'compute_PGM_value':
        return _compute_PGM_value(data['optical_element'])
    elif data['method'] == 'compute_grating_orientation':
        return _compute_grating_orientation(data['optical_element'])
    elif data['method'] == 'compute_crystal_init':
        return _compute_crystal_init(data['optical_element'])
    elif data['method'] == 'compute_crystal_orientation':
        return _compute_crystal_orientation(data['optical_element'])
    elif data['method'] == 'process_intensity_reports':
        return _process_intensity_reports(data['source_type'], data['undulator_type'])
    elif data['method'] == 'process_beam_parameters':
        data.ebeam = srw_common.process_beam_parameters(data.ebeam)
        data['ebeam']['drift'] = calculate_beam_drift(
            data['ebeam_position'],
            data['source_type'],
            data['undulator_type'],
            data['undulator_length'],
            data['undulator_period'],
        )
        return data['ebeam']
    elif data['method'] == 'compute_undulator_length':
        return compute_undulator_length(data['tabulated_undulator'])
    elif data['method'] == 'process_undulator_definition':
        return process_undulator_definition(data)
    elif data['method'] == 'processedImage':
        return _process_image(data, kwargs['tmp_dir'])
    raise RuntimeError('unknown application data method: {}'.format(data['method']))


def get_data_file(run_dir, model, frame, **kwargs):
    filename = get_filename_for_model(model)
    with open(str(run_dir.join(filename))) as f:
        return filename, f.read(), 'application/octet-stream'
    raise RuntimeError('output file unknown for model: {}'.format(model))


def get_filename_for_model(model):
    if _SIM_DATA.is_watchpoint(model):
        model = _SIM_DATA.WATCHPOINT_REPORT
    return _DATA_FILE_FOR_MODEL[model]['filename']


def get_predefined_beams():
    return _SIM_DATA.srw_predefined().beams


def sim_frame(frame_args):
    r = frame_args.frameReport
    if r == 'multiElectronAnimation':
        m = frame_args.sim_in.models[r]
        m.intensityPlotsWidth = frame_args.intensityPlotsWidth
        if frame_args.get('rotateAngle', 0):
            m.rotateAngle = float(frame_args.rotateAngle)
            m.rotateReshape = frame_args.rotateReshape
        else:
            m.rotateAngle = 0
    for i in (1, 2, 3):
        try:
            return extract_report_data(
                str(frame_args.run_dir.join(get_filename_for_model(r))),
                frame_args.sim_in,
            )
        except Exception:
            # sleep and retry to work-around concurrent file read/write
            pkdlog('sleep and retry simulation frame read: {} {}', i, r)
            time.sleep(2)
    return extract_report_data(
        str(frame_args.run_dir.join(get_filename_for_model(r))),
        frame_args.sim_in,
    )


def import_file(req, tmp_dir, **kwargs):
    import sirepo.server

    i = None
    try:
        r = kwargs['reply_op'](simulation_db.default_data(SIM_TYPE))
        d = pykern.pkjson.load_any(r.data)
        i = d.models.simulation.simulationId
        b = d.models.backgroundImport = PKDict(
            arguments=req.import_file_arguments,
            python=req.file_stream.read(),
            userFilename=req.filename,
        )
        # POSIT: import.py uses ''', but we just don't allow quotes in names
        if "'" in b.arguments:
            raise sirepo.util.UserAlert('arguments may not contain quotes')
        if "'" in b.userFilename:
            raise sirepo.util.UserAlert('filename may not contain quotes')
        d.pkupdate(
            report='backgroundImport',
            forceRun=True,
            simulationId=i,
        )
        r = sirepo.uri_router.call_api('runSimulation', data=d)
        for _ in range(_IMPORT_PYTHON_POLLS):
            if r.status_code != 200:
                raise sirepo.util.UserAlert(
                    'error parsing python',
                    'unexpected response status={} data={}',
                    r.status_code,
                    r.data,
                )
            try:
                r = pykern.pkjson.load_any(r.data)
            except Exception as e:
                raise sirepo.util.UserAlert(
                    'error parsing python',
                    'error={} parsing response data={}',
                    e,
                    r.data,
                )
            if 'error' in r:
                raise sirepo.util.UserAlert(r.get('error'))
            if PARSED_DATA_ATTR in r:
                break
            if 'nextRequest' not in r:
                raise sirepo.util.UserAlert(
                    'error parsing python',
                    'unable to find nextRequest in response={}',
                    PARSED_DATA_ATTR,
                    r,
                )
            time.sleep(r.nextRequestSeconds)
            r = sirepo.uri_router.call_api('runStatus', data=r.nextRequest)
        else:
            raise sirepo.util.UserAlert(
                'error parsing python',
                'polled too many times, last response={}',
                r,
            )
        r = r.get(PARSED_DATA_ATTR)
        r.models.simulation.simulationId = i
        r = simulation_db.save_simulation_json(r, do_validate=True)
    except Exception:
        raise
        if i:
            try:
                simulation_db.delete_simulation(req.type, i)
            except Exception:
                pass
        raise
    raise sirepo.util.Response(sirepo.server.api_simulationData(r.simulationType, i, pretty=False))


def new_simulation(data, new_simulation_data):
    sim = data['models']['simulation']
    sim['sourceType'] = new_simulation_data['sourceType']
    if _SIM_DATA.srw_is_gaussian_source(sim):
        data['models']['initialIntensityReport']['sampleFactor'] = 0
    elif _SIM_DATA.srw_is_dipole_source(sim):
        data['models']['intensityReport']['method'] = "2"
    elif _SIM_DATA.srw_is_arbitrary_source(sim):
        data['models']['sourceIntensityReport']['method'] = "2"
    elif _SIM_DATA.srw_is_tabulated_undulator_source(sim):
        data['models']['undulator']['length'] = compute_undulator_length(data['models']['tabulatedUndulator'])['length']
        data['models']['electronBeamPosition']['driftCalculationMethod'] = 'manual'


def prepare_for_client(data):
    save = False
    for model_name in _USER_MODEL_LIST_FILENAME.keys():
        if model_name == 'tabulatedUndulator' and not _SIM_DATA.srw_is_tabulated_undulator_source(data['models']['simulation']):
            # don't add a named undulator if tabulated is not the current source type
            continue
        model = data['models'][model_name]
        if _SIM_DATA.srw_is_user_defined_model(model):
            user_model_list = _load_user_model_list(model_name)
            search_model = None
            models_by_id = _user_model_map(user_model_list, 'id')
            if 'id' in model and model['id'] in models_by_id:
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
                save = True
    if save:
        pkdp("save simulation json with sim_data_template_fixup={}", data.get('sim_data_template_fixup', None))
        simulation_db.save_simulation_json(data)
    return data


def prepare_for_save(data):
    for model_name in _USER_MODEL_LIST_FILENAME.keys():
        if model_name == 'tabulatedUndulator' and not _SIM_DATA.srw_is_tabulated_undulator_source(data['models']['simulation']):
            # don't add a named undulator if tabulated is not the current source type
            continue
        model = data['models'][model_name]
        if _SIM_DATA.srw_is_user_defined_model(model):
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


def prepare_output_file(run_dir, sim_in):
    m = sim_in.report
    if m in ('brillianceReport', 'mirrorReport'):
        return
    #TODO(pjm): only need to rerun extract_report_data() if report style fields have changed
    fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
    if fn.exists():
        fn.remove()
        output_file = run_dir.join(get_filename_for_model(m))
        if output_file.exists():
            res = extract_report_data(str(output_file), sim_in)
            simulation_db.write_result(res, run_dir=run_dir)


def process_undulator_definition(model):
    """Convert K -> B and B -> K."""
    try:
        if model['undulator_definition'] == 'B':
            # Convert B -> K:
            und = srwlib.SRWLMagFldU([srwlib.SRWLMagFldH(1, 'v', float(model['amplitude']), 0, 1)], float(model['undulator_period']))
            model['undulator_parameter'] = _SIM_DATA.srw_format_float(und.get_K())
        elif model['undulator_definition'] == 'K':
            # Convert K to B:
            und = srwlib.SRWLMagFldU([], float(model['undulator_period']))
            model['amplitude'] = _SIM_DATA.srw_format_float(
                und.K_2_B(float(model['undulator_parameter'])),
            )
        return model
    except Exception:
        return model


def python_source_for_model(data, model):
    data['report'] = model or _SIM_DATA.SRW_RUN_ALL_MODEL
    return _generate_parameters_file(data, plot_reports=True)


def remove_last_frame(run_dir):
    pass


def validate_file(file_type, path):
    """Ensure the data file contains parseable rows data"""
    if not _SIM_DATA.srw_is_valid_file_type(file_type, path):
        return 'invalid file type: {}'.format(path.ext)
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
        srwl_uti_smp.SRWLUtiSmp(
            file_path=str(path),
            # srw processes the image so we save to tmp location
            is_save_images=True,
            prefix=path.purebasename,
        )
    if not _SIM_DATA.srw_is_valid_file(file_type, path):
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
        _trim(_generate_parameters_file(data, run_dir=run_dir))
    )


def _add_report_filenames(v):
    for k in _DATA_FILE_FOR_MODEL:
        v['{}Filename'.format(k)] = _DATA_FILE_FOR_MODEL[k]['filename']


def _compute_material_characteristics(model, photon_energy, prefix=''):
    fields_with_prefix = PKDict({
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
    kwargs = PKDict({
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

def _compute_PGM_value(model):
    if not model['energyAvg'] or not model['cff'] or not model['grazingAngle']:
        return model
    if model['cff'] == 1:
        return model
    parms_list = ['energyAvg', 'cff', 'grazingAngle']
    try:
        mirror = srwlib.SRWLOptMirPl(
            _size_tang=model['tangentialSize'],
            _size_sag=model['sagittalSize'],
            _nvx=model['nvx'],
            _nvy=model['nvy'],
            _nvz=model['nvz'],
            _tvx=model['tvx'],
            _tvy=model['tvy'],
            _x=model['horizontalOffset'],
            _y=model['verticalOffset'],
        )
        opGr = srwlib.SRWLOptG(
            _mirSub=mirror,
            _m=model['diffractionOrder'],
            _grDen=model['grooveDensity0'],
            _grDen1=model['grooveDensity1'],
            _grDen2=model['grooveDensity2'],
            _grDen3=model['grooveDensity3'],
            _grDen4=model['grooveDensity4'],
            _e_avg=model['energyAvg'],
            _cff=model['cff'],
            _ang_graz=model['grazingAngle'],
            _ang_roll=model['rollAngle'],
        )
        if model.computeParametersFrom == '1':
            grAng, defAng = opGr.cff2ang(_en=model['energyAvg'], _cff=model['cff'])
            model['grazingAngle'] = grAng * 1000.0
        elif model.computeParametersFrom == '2':
            cff, defAng = opGr.ang2cff(_en=model['energyAvg'], _ang_graz=model['grazingAngle']/1000.0)
            model['cff'] = cff
        angroll = model['rollAngle']
        if abs(angroll) < np.pi/4 or abs(angroll-np.pi) < np.pi/4:
            model['orientation'] = 'y'
        else: model['orientation'] = 'x'
        _compute_grating_orientation(model)
    except Exception:
        pkdlog('\n{}', traceback.format_exc())
        for key in parms_list:
            model[key] = None
    return model

def _compute_grating_orientation(model):
    if not model['grazingAngle']:
        return model
    parms_list = ['nvx', 'nvy', 'nvz', 'tvx', 'tvy', 'outoptvx', 'outoptvy', 'outoptvz', 'outframevx', 'outframevy']
    try:
        mirror = srwlib.SRWLOptMirPl(
            _size_tang=model['tangentialSize'],
            _size_sag=model['sagittalSize'],
            _nvx=model['nvx'],
            _nvy=model['nvy'],
            _nvz=model['nvz'],
            _tvx=model['tvx'],
            _tvy=model['tvy'],
            _x=model['horizontalOffset'],
            _y=model['verticalOffset'],
        )
        opGr = srwlib.SRWLOptG(
            _mirSub=mirror,
            _m=model['diffractionOrder'],
            _grDen=model['grooveDensity0'],
            _grDen1=model['grooveDensity1'],
            _grDen2=model['grooveDensity2'],
            _grDen3=model['grooveDensity3'],
            _grDen4=model['grooveDensity4'],
            _e_avg=model['energyAvg'],
            _cff=model['cff'],
            _ang_graz=model['grazingAngle'],
            _ang_roll=model['rollAngle'],
        )
        model['nvx'] = opGr.nvx
        model['nvy'] = opGr.nvy
        model['nvz'] = opGr.nvz
        model['tvx'] = opGr.tvx
        model['tvy'] = opGr.tvy
        orientDataGr_pp = opGr.get_orient(_e=model['energyAvg'])[1]
        tGr_pp = orientDataGr_pp[0]  # Tangential Vector to Grystal surface
        nGr_pp = orientDataGr_pp[2]  # Normal Vector to Grystal surface
        model['outoptvx'] = nGr_pp[0]
        model['outoptvy'] = nGr_pp[1]
        model['outoptvz'] = nGr_pp[2]
        model['outframevx'] = tGr_pp[0]
        model['outframevy'] = tGr_pp[1]

    except Exception:
        pkdlog('\n{}', traceback.format_exc())
        for key in parms_list:
            model[key] = None
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
        if model['diffractionAngle'] == '-1.57079632' or model['diffractionAngle'] == '1.57079632':
            model['orientation'] = 'x'
        else: model['orientation'] = 'y'
    except Exception:
        pkdlog('{https://github.com/ochubar/SRW/blob/master/env/work/srw_python/srwlib.py}: error: {}', material_raw)
        for key in parms_list:
            model[key] = None
    return model

def _compute_crystal_orientation(model):
    if not model['dSpacing']:
        return model
    parms_list = ['nvx', 'nvy', 'nvz', 'tvx', 'tvy', 'outoptvx', 'outoptvy', 'outoptvz', 'outframevx', 'outframevy']
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
            _uc=float(model['useCase']),
            _ang_as=model['asymmetryAngle'],
            _e_avg=model['energy'],
            _ang_roll=float(model['diffractionAngle']),
        )
        model['nvx'] = opCr.nvx
        model['nvy'] = opCr.nvy
        model['nvz'] = opCr.nvz
        model['tvx'] = opCr.tvx
        model['tvy'] = opCr.tvy
        orientDataCr_pp = opCr.get_orient(_e=model['energy'])[1]
        tCr_pp = orientDataCr_pp[0]  # Tangential Vector to Crystal surface
        nCr_pp = orientDataCr_pp[2]  # Normal Vector to Crystal surface
        model['outoptvx'] = nCr_pp[0]
        model['outoptvy'] = nCr_pp[1]
        model['outoptvz'] = nCr_pp[2]
        model['outframevx'] = tCr_pp[0]
        model['outframevy'] = tCr_pp[1]
        _SIM_DATA.srw_compute_crystal_grazing_angle(model)
    except Exception:
        pkdlog('\n{}', traceback.format_exc())
        for key in parms_list:
            model[key] = None
    return model

def _compute_grazing_orientation(model):
    def preserve_sign(item, field, new_value):
        old_value = item[field] if field in item else 0
        was_negative = float(old_value) < 0
        item[field] = float(new_value)
        if (was_negative and item[field] > 0) or item[field] < 0:
            item[field] = - item[field]

    grazing_angle = float(model.grazingAngle) / 1000.0
    # z is always negative
    model.normalVectorZ = - abs(math.sin(grazing_angle))
    if model.autocomputeVectors == 'horizontal':
        preserve_sign(model, 'normalVectorX', math.cos(grazing_angle))
        preserve_sign(model, 'tangentialVectorX', math.sin(grazing_angle))
        model.normalVectorY = 0
        model.tangentialVectorY = 0
    elif model.autocomputeVectors == 'vertical':
        preserve_sign(model, 'normalVectorY', math.cos(grazing_angle))
        preserve_sign(model, 'tangentialVectorY', math.sin(grazing_angle))
        model.normalVectorX = 0
        model.tangentialVectorX = 0
    return model


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
    return PKDict()


def _extract_beamline_orientation(filename):
    return {
        #TODO(pjm): x_range is needed for sirepo-plotting.js, need a better valid-data check
        'x_range': [],
        'cols': uti_io.read_ascii_data_cols(filename, '\t', _i_col_start=1, _n_line_skip=1),
    }


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
    available_axes = PKDict()
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
            plots.append(PKDict(
                points=points,
                label=available_axes[model[f]],
                #TODO(pjm): refactor with template_common.compute_plot_color_and_range()
                color='#ff7f0e' if len(plots) else '#1f77b4',
            ))
    return PKDict(
        title='Electron Trajectory',
        x_range=[min(x_points), max(x_points)],
        x_points=x_points,
        y_label='[{}]'.format(data[model['plotAxisY']]['units']),
        x_label=available_axes[model['plotAxisX']] + ' [' + data[model['plotAxisX']]['units'] + ']',
        y_range=y_range,
        plots=plots,
    )

def _fix_file_header(filename):
    # fixes file header for coherenceXAnimation and coherenceYAnimation reports
    rows = []
    pkdc('fix header filename: {}', filename)
    with pkio.open_text(filename) as f:
        for line in f:
            rows.append(line)
            if len(rows) == 11:
                pkdc('before header changed rows4: {}',rows[4])
                pkdc('before header changed rows5: {}',rows[5])
                pkdc('before header changed rows6: {}',rows[6])
                pkdc('before header changed rows7: {}',rows[7])
                pkdc('before header changed rows8: {}',rows[8])
                pkdc('before header changed rows9: {}',rows[9])
                #if rows[4] == rows[7]:
                if rows[6].split()[0] == rows[9].split()[0] and rows[6].split()[0] != 1:
                    # already fixed up
                    return
                col4 = rows[4].split()
                col5 = rows[5].split()
                col6 = rows[6].split()
                col7 = rows[7].split()
                col8 = rows[8].split()
                col9 = rows[9].split()
                #if re.search(r'^\#0 ', rows[4]):
                if re.search(r'^\#1 ', rows[6]):
                    col4[0] = col7[0]
                    rows[4] = ' '.join(col4)+'\n'
                    col5[0] = col8[0]
                    rows[5] = ' '.join(col5)+'\n'
                    col6[0] = col9[0]
                    rows[6] = ' '.join(col6)+'\n'
                else:
                    col7[0] = col4[0]
                    rows[7] = ' '.join(col7)+'\n'
                    col8[0] = col5[0]
                    rows[8] = ' '.join(col8)+'\n'
                    col9[0] = col6[0]
                    rows[9] = ' '.join(col9)+'\n'
                Vmin = float(rows[7].split()[0][1:])
                Vmax = float(rows[8].split()[0][1:])
                rows[7] = '#'+str((Vmin-Vmax)/2)+' '+' '.join(rows[7].split()[1:])+'\n'
                rows[8] = '#'+str((Vmax-Vmin)/2)+' '+' '.join(rows[8].split()[1:])+'\n'
                pkdc('after header changed rows4:{}',rows[4])
                pkdc('after header changed rows5:{}',rows[5])
                pkdc('after header changed rows6:{}',rows[6])
                pkdc('after header changed rows7:{}',rows[7])
                pkdc('after header changed rows8:{}',rows[8])
                pkdc('after header changed rows9:{}',rows[9])
    pkio.write_text(filename, ''.join(rows))


def _generate_beamline_optics(report, data, last_id):
    models = data['models']
    if not _SIM_DATA.srw_is_beamline_report(report):
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
                items.append(PKDict(
                    name=drift_name,
                    type='drift',
                    position=prev.position,
                    propagation=prev.drift_propagation,
                    length=size,
                ))
        pp = propagation[str(item.id)]
        item.propagation = pp[0]
        item.drift_propagation = pp[1]
        item.name = name
        if not is_disabled:
            if item.type == 'watch' and not len(items):
                # first item is a watch, insert a 0 length drift in front
                items.append(PKDict(
                    name='zero_drift',
                    type='drift',
                    position=item.position,
                    propagation=item.propagation,
                    length=0,
                ))
                names.append(items[-1].name)
            if 'heightProfileFile' in item:
                item.heightProfileDimension = _height_profile_dimension(item, data)
            items.append(item)
            names.append(name)
        if int(last_id) == int(item.id):
            break
        prev = item
    args = PKDict(
        items=items,
        names=names,
        postPropagation=models.postPropagation,
        wantPostPropagation=has_beamline_elements and (int(last_id) == int(models.beamline[-1].id)),
        maxNameSize=max_name_size,
        nameMap=PKDict(
            apertureShape='ap_shape',
            asymmetryAngle='ang_as',
            attenuationLength='atten_len',
            complementaryAttenuationLength='atLen2',
            complementaryRefractiveIndex='delta2',
            coreAttenuationLength='atten_len_core',
            coreDiameter='diam_core',
            coreRefractiveIndex='delta_core',
            crystalThickness='tc',
            dSpacing='d_sp',
            diffractionOrder='m',
            externalAttenuationLength='atten_len_ext',
            externalRefractiveIndex='delta_ext',
            energyAvg='e_avg',
            firstFocusLength='p',
            focalLength='q',
            focalPlane='foc_plane',
            grazingAngle='ang',
            gridShape='grid_sh',
            grooveDensity0='grDen',
            grooveDensity1='grDen1',
            grooveDensity2='grDen2',
            grooveDensity3='grDen3',
            grooveDensity4='grDen4',
            heightAmplification='amp_coef',
            heightProfileFile='hfn',
            horizontalApertureSize='apert_h',
            horizontalCenterPosition='xc',
            horizontalFocalLength='Fx',
            horizontalGridDimension='grid_dx',
            horizontalGridPitch='pitch_x',
            horizontalGridsNumber='grid_nx',
            horizontalMaskCoordinate='mask_x0',
            horizontalOffset='x',
            horizontalPixelsNumber='mask_Nx',
            horizontalSamplingInterval='hx',
            horizontalSize='Dx',
            horizontalTransverseSize='size_x',
            imageFile='file_path',
            length='L',
            mainAttenuationLength='atLen1',
            mainRefractiveIndex='delta1',
            maskThickness='thick',
            normalVectorX='nvx',
            normalVectorY='nvy',
            normalVectorZ='nvz',
            numberOfLenses='n',
            numberOfZones='nZones',
            orientation='dim',
            outerRadius='rn',
            radius='r',
            refractiveIndex='delta',
            sagittalRadius='rs',
            sagittalSize='size_sag',
            tangentialRadius='rt',
            tangentialSize='size_tang',
            tangentialVectorX='tvx',
            tangentialVectorY='tvy',
            thickness='thick',
            tipRadius='r_min',
            tipWallThickness='wall_thick',
            transmissionImage='extTransm',
            useCase='uc',
            verticalApertureSize='apert_v',
            verticalCenterPosition='yc',
            verticalFocalLength='Fy',
            verticalGridDimension='grid_dy',
            verticalGridPitch='pitch_y',
            verticalGridsNumber='grid_ny',
            verticalMaskCoordinate='mask_y0',
            verticalOffset='y',
            verticalPixelsNumber='mask_Ny',
            verticalSamplingInterval='hy',
            verticalSize='Dy',
            verticalTransverseSize='size_y',
        ),
    )
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
        if _SIM_DATA.srw_is_idealized_undulator(source_type, undulator_type) and int(data['models']['fluxReport']['magneticField']) == 2:
            data['models']['fluxReport']['magneticField'] = 1
    elif _SIM_DATA.is_watchpoint(report) or report == 'sourceIntensityReport':
        # render the watchpoint report settings in the initialIntensityReport template slot
        data['models']['initialIntensityReport'] = data['models'][report].copy()
    if report == 'sourceIntensityReport':
        for k in ['photonEnergy', 'horizontalPointCount', 'horizontalPosition', 'horizontalRange',
                  'sampleFactor', 'samplingMethod', 'verticalPointCount', 'verticalPosition', 'verticalRange']:
            data['models']['simulation'][k] = data['models']['sourceIntensityReport'][k]

    if _SIM_DATA.srw_is_tabulated_undulator_source(data['models']['simulation']):
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
    if _SIM_DATA.is_watchpoint(report):
        last_id = _SIM_DATA.watchpoint_id(report)
    if report == 'multiElectronAnimation':
        last_id = data['models']['multiElectronAnimation']['watchpointId']
    if int(data['models']['simulation']['samplingMethod']) == 2:
        data['models']['simulation']['sampleFactor'] = 0
    res, v = template_common.generate_parameters_file(data)

    v['rs_type'] = source_type
    if _SIM_DATA.srw_is_idealized_undulator(source_type, undulator_type):
        v['rs_type'] = 'u'

    if report == 'mirrorReport':
        v['mirrorOutputFilename'] = _MIRROR_OUTPUT_FILE
        return template_common.render_jinja(SIM_TYPE, v, 'mirror.py')
    if report == 'brillianceReport':
        v['brillianceOutputFilename'] = _BRILLIANCE_OUTPUT_FILE
        return template_common.render_jinja(SIM_TYPE, v, 'brilliance.py')
    if report == 'backgroundImport':
        v.tmp_dir = str(run_dir)
        v.python_file = run_dir.join('user_python.py')
        v.python_file.write(data.models.backgroundImport.python)
        return template_common.render_jinja(SIM_TYPE, v, 'import.py')
    v['beamlineOptics'], v['beamlineOpticsParameters'] = _generate_beamline_optics(report, data, last_id)

    # und_g and und_ph API units are mm rather than m
    v['tabulatedUndulator_gap'] *= 1000
    v['tabulatedUndulator_phase'] *= 1000

    if report in data['models'] and 'distanceFromSource' in data['models'][report]:
        position = data['models'][report]['distanceFromSource']
    else:
        position = _get_first_element_position(data)
    v['beamlineFirstElementPosition'] = position

    # 1: auto-undulator 2: auto-wiggler
    v['energyCalculationMethod'] = 1 if _SIM_DATA.srw_is_undulator_source(data['models']['simulation']) else 2

    if data['models']['electronBeam']['beamDefinition'] == 'm':
        v['electronBeam_horizontalBeta'] = None
    v[report] = 1
    _add_report_filenames(v)
    v['setupMagneticMeasurementFiles'] = plot_reports and _SIM_DATA.srw_uses_tabulated_zipfile(data)
    v['srwMain'] = _generate_srw_main(data, plot_reports)

    if run_dir and _SIM_DATA.srw_uses_tabulated_zipfile(data):
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
    return _trim(res + template_common.render_jinja(SIM_TYPE, v))


def _generate_srw_main(data, plot_reports):
    report = data['report']
    source_type = data['models']['simulation']['sourceType']
    run_all = report == _SIM_DATA.SRW_RUN_ALL_MODEL
    content = [
        'v = srwl_bl.srwl_uti_parse_options(varParam, use_sys_argv={})'.format(plot_reports),
    ]
    if plot_reports and _SIM_DATA.srw_uses_tabulated_zipfile(data):
        content.append('setup_magnetic_measurement_files("{}", v)'.format(data['models']['tabulatedUndulator']['magneticFile']))
    if run_all or _SIM_DATA.srw_is_beamline_report(report):
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
    if run_all or _SIM_DATA.is_watchpoint(report) or report == 'beamline3DReport':
        content.append('v.ws = True')
        if plot_reports:
            content.append("v.ws_pl = 'xy'")
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
    if _SIM_DATA.srw_is_background_report(report):
        content.append(
            # Number of "iterations" per save is best set to num processes
            'v.wm_ns = v.sm_ns = {}'.format(sirepo.mpi.cfg.cores),
        )
    content.append('srwl_bl.SRWLBeamline(_name=v.name, _mag_approx=mag).calc_all(v, op)')
    return '\n'.join(['    {}'.format(x) for x in content] + ['', 'main()\n'])


def _get_first_element_position(data):
    beamline = data['models']['beamline']
    if len(beamline):
        return beamline[0]['position']
    if 'distanceFromSource' in data['models']['simulation']:
        return data['models']['simulation']['distanceFromSource']
    return template_common.DEFAULT_INTENSITY_DISTANCE


def _height_profile_dimension(item, data):
    """Find the dimension of the provided height profile .dat file.
    1D files have 2 columns, 2D - 8 columns.
    """
    dimension = 0
    if item['heightProfileFile'] and item['heightProfileFile'] != 'None':
        with _SIM_DATA.lib_file_abspath(item['heightProfileFile'], data=data).open('r') as f:
            header = f.readline().strip().split()
            dimension = 1 if len(header) == 2 else 2
    return dimension


def _intensity_units(is_gaussian, sim_in):
    if is_gaussian:
        if 'report' in sim_in and 'fieldUnits' in sim_in['models'][sim_in['report']]:
            i = sim_in['models'][sim_in['report']]['fieldUnits']
        else:
            i = sim_in['models']['initialIntensityReport']['fieldUnits']
        return _SCHEMA['enum']['FieldUnits'][int(i)][1]
    return 'ph/s/.1%bw/mm^2'


def _load_user_model_list(model_name):
    f = _SIM_DATA.lib_file_write_path(_USER_MODEL_LIST_FILENAME[model_name])
    try:
        if f.exists():
            return simulation_db.read_json(f)
    except Exception:
        pkdlog('user list read failed, resetting contents: {}', f)
    _save_user_model_list(model_name, [])
    return _load_user_model_list(model_name)


def _process_image(data, tmp_dir):
    """Process image and return

    Args:
        data (dict): description of simulation

    Returns:
        py.path.local: file to return
    """
    # This should just be a basename, but this ensures it.
    path = str(_SIM_DATA.lib_file_abspath(werkzeug.secure_filename(data.baseImage)))
    m = data['model']
    with pkio.save_chdir(tmp_dir):
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
            prefix=str(tmp_dir),
            output_image_format=m['outputImageFormat'],
        )
        return pkio.py_path(s.processed_image_name)


def _process_intensity_reports(source_type, undulator_type):
    # Magnetic field processing:
    return PKDict({
        'magneticField': 2 if source_type == 'a' or _SIM_DATA.srw_is_tabulated_undulator_with_magnetic_file(source_type, undulator_type) else 1,
    })


def _remap_3d(info, allrange, z_label, z_units, width_pixels, rotate_angle, rotate_reshape):
    x_range = [allrange[3], allrange[4], allrange[5]]
    y_range = [allrange[6], allrange[7], allrange[8]]
    ar2d = info['points']
    totLen = int(x_range[2] * y_range[2])
    n = len(ar2d) if totLen > len(ar2d) else totLen
    ar2d = np.reshape(ar2d[0:n], (y_range[2], x_range[2]))

    # rescale width and height to maximum of width_pixels
    if width_pixels and (width_pixels < x_range[2] or width_pixels < y_range[2]):
        x_resize = 1.0
        y_resize = 1.0
        if width_pixels < x_range[2]:
            x_resize = float(width_pixels) / float(x_range[2])
        if width_pixels < y_range[2]:
            y_resize = float(width_pixels) / float(y_range[2])
        pkdc('Size before: {}  Dimensions: {}, Resize: [{}, {}]', ar2d.size, ar2d.shape, y_resize, x_resize)
        try:
            from scipy import ndimage
            ar2d = ndimage.zoom(ar2d, [y_resize, x_resize], order=1)
            pkdc('Size after : {}  Dimensions: {}', ar2d.size, ar2d.shape)
            x_range[2] = ar2d.shape[1]
            y_range[2] = ar2d.shape[0]
        except Exception:
            pkdlog('Cannot resize the image - scipy.ndimage.zoom() cannot be imported.')
    # rotate 3D image
    if rotate_angle:
        rotate_reshape = (rotate_reshape == "1")
        try:
            from scipy import ndimage
            pkdc('Size before: {}  Dimensions: {}', ar2d.size, ar2d.shape)
            shape_before = list(ar2d.shape)
            ar2d = ndimage.rotate(ar2d, rotate_angle, reshape = rotate_reshape, mode='constant', order = 3)
            pkdc('Size after rotate: {}  Dimensions: {}', ar2d.size, ar2d.shape)
            shape_rotate = list(ar2d.shape)

            pkdc('x_range and y_range before rotate is [{},{}] and [{},{}]', x_range[0], x_range[1], y_range[0], y_range[1])
            x_range[0] = shape_rotate[0]/shape_before[0]*x_range[0]
            x_range[1] = shape_rotate[0]/shape_before[0]*x_range[1]
            y_range[0] = shape_rotate[1]/shape_before[1]*y_range[0]
            y_range[1] = shape_rotate[1]/shape_before[1]*y_range[1]
            pkdc('x_range and y_range after rotate is [{},{}] and [{},{}]', x_range[0], x_range[1], y_range[0], y_range[1])

            x_range[2] = ar2d.shape[1]
            y_range[2] = ar2d.shape[0]
            if info['title'] != 'Power Density': info['subtitle'] = info['subtitle'] + ' Image Rotate {}^0'.format(rotate_angle)
        except Exception:
            pkdlog('Cannot rotate the image - scipy.ndimage.rotate() cannot be imported.')

    if z_units:
        z_label = u'{} [{}]'.format(z_label, z_units)
    return PKDict({
        'x_range': x_range,
        'y_range': y_range,
        'x_label': info['x_label'],
        'y_label': info['y_label'],
        'z_label': _superscript(z_label),
        'title': info['title'],
        'subtitle': _superscript_2(info['subtitle']),
        'z_matrix': ar2d.tolist(),
    })


def _rotated_axis_range(x, y, theta):
    x_new = x*np.cos(theta) + y*np.sin(theta)
    return x_new


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
    simulation_db.write_json(
        _SIM_DATA.lib_file_write_path(_USER_MODEL_LIST_FILENAME[model_name]),
        beam_list,
    )


def _superscript(val):
    return re.sub(r'\^2', u'\u00B2', val)


def _superscript_2(val):
    return re.sub(r'\^0', u'\u00B0', val)


def _trim(v):
    res = ''
    for l in v.split('\n'):
        res += l.rstrip() + '\n'
    x = res.rstrip('\n') + '\n'
    return x


def _unique_name(items, field, template):
    #TODO(pjm): this is the same logic as sirepo.js uniqueName()
    values = PKDict()
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
    res = PKDict()
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
