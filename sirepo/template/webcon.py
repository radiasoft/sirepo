# -*- coding: utf-8 -*-
u"""Webcon execution template.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import StringIO
import copy
import csv
import math
import numpy as np
import os
import os.path
import re
import scipy.fftpack
import scipy.optimize
import sklearn.cluster
import sklearn.metrics.pairwise
import sklearn.mixture
import sklearn.preprocessing
import sympy

SIM_TYPE = 'webcon'

BPM_FIELDS = [
    'vagrant:bpm1:hpos',
    'vagrant:bpm1:vpos',
    'vagrant:bpm2:hpos',
    'vagrant:bpm2:vpos',
    'vagrant:bpm3:hpos',
    'vagrant:bpm3:vpos',
    'vagrant:bpm4:hpos',
    'vagrant:bpm4:vpos',
]

CURRENT_FIELDS = [
    'vagrant:corrector1:HCurrent',
    'vagrant:corrector1:VCurrent',
    'vagrant:corrector2:HCurrent',
    'vagrant:corrector2:VCurrent',
    'vagrant:corrector3:HCurrent',
    'vagrant:corrector3:VCurrent',
    'vagrant:corrector4:HCurrent',
    'vagrant:corrector4:VCurrent',
]

CURRENT_FILE = 'currents.npy'

MONITOR_LOGFILE = 'monitor.log'

OPTIMIZER_RESULT_FILE = 'opt.json'

STEERING_FILE = 'steering.json'

_SCHEMA = simulation_db.get_schema(SIM_TYPE)


def background_percent_complete(report, run_dir, is_running):
    if report == 'epicsServerAnimation' and is_running:
        monitor_file = run_dir.join(MONITOR_LOGFILE)
        if monitor_file.exists():
            values, count = _read_monitor_file(monitor_file)
            return {
                'percentComplete': 0,
                'frameCount': count,
                'summaryData': {
                    'monitorValues': values,
                    'optimizationValues': _optimization_values(run_dir),
                }
            }
    return {
        'percentComplete': 0,
        'frameCount': 0,
    }


def epics_env(server_address):
    env = os.environ.copy()
    env['EPICS_CA_AUTO_ADDR_LIST'] = 'NO'
    env['EPICS_CA_ADDR_LIST'] = server_address
    env['EPICS_CA_SERVER_PORT'] = server_address.split(':')[1]
    return env


def fixup_old_data(data):
    for m in _SCHEMA.model:
        # don't include beamline element models (all uppercase)
        if m != m.upper():
            if m not in data.models:
                data.models[m] = pkcollections.Dict({})
            template_common.update_model_defaults(data.models[m], m, _SCHEMA)
    for m in ('analysisAnimation', 'fitter', 'fitReport'):
        if m in data.models:
            del data.models[m]
    if 'history' not in data.models.analysisReport:
        data.models.analysisReport.history = []
    if 'subreports' not in data.models.hiddenReport:
        data.models.hiddenReport.subreports = []
    if 'beamlines' not in data.models:
        _init_default_beamline(data)
    template_common.organize_example(data)


def get_analysis_report(run_dir, data):
    report, col_info, plot_data = _report_info(run_dir, data)
    clusters = None
    if 'action' in report:
        if report.action == 'fit':
            return _get_fit_report(report, plot_data, col_info)
        elif report.action == 'cluster':
            clusters = _compute_clusters(report, plot_data, col_info)
    x_idx = _safe_index(col_info, report.x)
    x = (plot_data[:, x_idx] * col_info['scale'][x_idx]).tolist()
    plots = []
    for f in ('y1', 'y2', 'y3'):
        #TODO(pjm): determine if y2 or y3 will get used
        if f != 'y1':
            continue
        if f not in report or report[f] == 'none':
            continue
        y_idx = _safe_index(col_info, report[f])
        y = plot_data[:, y_idx]
        if len(y) <= 0 or math.isnan(y[0]):
            continue
        plots.append({
            'points': (y * col_info['scale'][y_idx]).tolist(),
            'label': _label(col_info, y_idx),
            'style': 'line' if 'action' in report and report.action == 'fft' else 'scatter',
        })
    return template_common.parameter_plot(x, plots, {}, {
        'title': '',
        'y_label': '',
        'x_label': _label(col_info, x_idx),
        'clusters': clusters,
        'summaryData': {},
    })


def get_application_data(data):
    if data['method'] == 'column_info':
        data = pkcollections.Dict({
            'models': pkcollections.Dict({
                'analysisData': data['analysisData'],
            }),
        })
        return {
            'columnInfo': _column_info(
                _analysis_data_path(simulation_db.simulation_lib_dir(SIM_TYPE), data)),
        }
    if data['method'] == 'update_kicker':
        return _update_epics_kicker(data)
    if data['method'] == 'read_kickers':
        return _read_epics_kickers(data)
    if data['method'] == 'enable_steering':
        return _enable_steering(data)
    assert False, 'unknown application_data method: {}'.format(data['method'])


def get_data_file(run_dir, model, frame, options=None):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    report = data.models[data.report]
    path = _analysis_data_path(run_dir, data)
    col_info = _column_info(path)
    plot_data = _load_file_with_history(report, path, col_info)
    buf = StringIO.StringIO()
    buf.write(','.join(col_info['names']) + '\n')
    np.savetxt(buf, plot_data, delimiter=',')
    return '{}.csv'.format(model), buf.getvalue(), 'text/csv'


def get_fft(run_dir, data):
    data.report = _analysis_report_name_for_fft_report(data.report, data)
    report, col_info, plot_data = _report_info(run_dir, data)
    col1 = _safe_index(col_info, report.x)
    col2 = _safe_index(col_info, report.y1)
    t_vals = plot_data[:, col1] * col_info['scale'][col1]
    y_vals = plot_data[:, col2] * col_info['scale'][col2]

    # fft takes the y data only and assumes it corresponds to equally-spaced x values.
    fft_out = scipy.fftpack.fft(y_vals)

    num_samples = len(y_vals)
    half_num_samples = num_samples // 2

    # should all be the same - this will normalize the frequencies
    sample_period = abs(t_vals[1] - t_vals[0])
    if sample_period == 0:
        assert False, 'FFT sample period could not be determined from data. Ensure x has equally spaced values'
    #sample_period = np.mean(np.diff(t_vals))

    # the first half of the fft data (taking abs() folds in the imaginary part)
    y = 2.0 / num_samples * np.abs(fft_out[0:half_num_samples])

    # get the frequencies found
    # fftfreq just generates an array of equally-spaced values that represent the x-axis
    # of the fft of data of a given length.  It includes negative values
    freqs = scipy.fftpack.fftfreq(len(fft_out)) / sample_period
    w = freqs[0:half_num_samples]
    found_freqs = []

    # is signal to noise useful?
    m = y.mean()
    sd = y.std()
    s2n = np.where(sd == 0, 0, m / sd)

    # We'll say we found a frequency peak when the size of the coefficient divided by the average is
    # greather than this.  A crude indicator - one presumes better methods exist
    found_sn_thresh = 10

    ci = 0
    max_bin = -1
    min_bin = half_num_samples
    bin_spread = 10
    for coef, freq in zip(fft_out[0:half_num_samples], freqs[0:half_num_samples]):
        #pkdp('{c:>6} * exp(2 pi i t * {f}) : vs thresh {t}', c=(2.0 / N) * np.abs(coef), f=freq, t=(2.0 / N) * np.abs(coef) / m)
        if (2.0 / num_samples) * np.abs(coef) / m > found_sn_thresh:
            found_freqs.append((ci, freq))
            max_bin = ci
            if ci < min_bin:
                min_bin = ci
        ci += 1
    #pkdp('!FOUND FREQS {}, MIN {}, MAX {}, P2P {}, S2N {}, MEAN {}', found_freqs, min_coef, max_coef, p2p, s2n, m)

    # focus in on the peaks?
    min_bin = max(0, min_bin - bin_spread)
    max_bin = min(half_num_samples, max_bin + bin_spread)
    yy = 2.0 / num_samples * np.abs(fft_out[min_bin:max_bin])
    ww = freqs[min_bin:max_bin]

    max_y = np.max(y)
    y_norm = y / (max_y if max_y != 0 else 1)
    plots = [
        {
            'points': y_norm.tolist(),
            'label': 'fft',
        },
    ]

    #TODO(mvk): figure out appropriate labels from input
    return template_common.parameter_plot(w.tolist(), plots, {}, {
        'title': '',
        'y_label': _label(col_info, 1),
        'x_label': 'f[1/s]',
        'preserve_units': True,
        #'x_label': _label(col_info, 0) + '^-1',
        'summaryData': {
            'freqs': found_freqs,
        },
        #'latex_label': latex_label
    })
    #return {
    #    'title': '',
    #    'x_points': w.tolist(),
    #    'points': (y * col_info['scale'][1]).tolist(),
    #    'y_label': _label(col_info, 1),
    #    'x_label': 'ω[s-1]',
    #}


def lib_files(data, source_lib):
    res = []
    report = data.report if 'report' in data else None
    if report == 'epicsServerAnimation':
        res += [
	    'beam_line_readings.db',
            'beam_line_example.dbd',
            'beam_line_exampleVersion.db',
            'beam_line_settings.db',
            'epics-boot.cmd',
            'user.substitutions',
        ]
    elif data.models.analysisData.file:
        res.append(_analysis_data_file(data))
    return template_common.filename_to_path(res, source_lib)


def models_related_to_report(data):
    r = data['report']
    if r == 'epicsServerAnimation':
        return []
    res = [r, 'analysisData']
    if 'fftReport' in r:
        name = _analysis_report_name_for_fft_report(r, data)
        res += ['{}.{}'.format(name, v) for v in ('x', 'y1', 'history')]
    return res


def python_source_for_model(data, model):
    return _generate_parameters_file(None, data)


def read_epics_values(server_address, fields):
    assert server_address, 'missing remote server address'
    output = run_epics_command(server_address, ['caget', '-w', '5'] + fields)
    if not output:
        return None
    res = np.array(re.split(r'\s+', output)[1::2]).astype('float').tolist()
    #pkdp(' got result: {}', res)
    return res


def run_epics_command(server_address, cmd):
    return template_common.subprocess_output(cmd, epics_env(server_address))


def update_epics_kickers(epics_settings, sim_dir, fields, values):
    if epics_settings.serverType == 'remote':
        assert epics_settings.serverAddress, 'missing remote server address'
        write_epics_values(epics_settings.serverAddress, fields, values)
    else:
        if not sim_dir.exists():
            return {}
        #TODO(pjm): use save to tmp followed by mv for atomicity
        np.save(str(sim_dir.join(CURRENT_FILE)), np.array([fields, values]))


def validate_file(file_type, path):
    #TODO(pjm): accept CSV or SDDS files
    try:
        if not _column_info(path):
            return 'Invalid CSV header row'
    except Exception as e:
        return 'Error reading file. Ensure the file is in CSV or SDDS format.'
    return None


def validate_sympy(str):
    try:
        sympy.sympify(str)
        return True
    except:
        return False


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(run_dir, data),
    )


def write_epics_values(server_address, fields, values):
    for idx in range(len(fields)):
        if run_epics_command(
                server_address,
                ['caput', '-w', '10', fields[idx], str(values[idx])],
        ) is None:
            return False
    return True


def _analysis_data_file(data):
    return template_common.lib_file_name('analysisData', 'file', data.models.analysisData.file)


def _analysis_data_path(run_dir, data):
    return str(run_dir.join(_analysis_data_file(data)))


def _analysis_report_name_for_fft_report(report, data):
    return data.models[report].get('analysisReport', 'analysisReport')


def _column_info(path):
    # parse label/units from the csv header
    header = None
    with open(str(path)) as f:
        reader = csv.reader(f)
        for row in reader:
            header = row
            break
    if not header or len(header) < 2:
        return None
    header_row_count = 1
    if re.search(r'^[\-|\+0-9eE\.]+$', header[0]):
        header = ['column {}'.format(idx + 1) for idx in range(len(header))]
        header_row_count = 0
    res = {
        'header_row_count': header_row_count,
        'names': [],
        'units': [],
        'scale': [],
    }
    for h in header:
        name = h
        units = ''
        scale = 1
        match = re.search(r'^(.*?)\s*(\(|\[)(.*?)(\)|\])\s*$', h)
        if match:
            name = match.group(1)
            units = match.group(3)
            #TODO(pjm): convert units to base for other cases
            match = re.search(r'^k(\w)', units)
            if match:
                units = match.group(1)
                scale = 1e3
        res['names'].append(name)
        res['units'].append(units)
        res['scale'].append(scale)
    return res


def _compute_clusters(report, plot_data, col_info):
    cols = []
    if 'clusterFields' not in report:
        assert len(cols) > 1, 'At least two cluster fields must be selected'
    for idx in range(len(report.clusterFields)):
        if report.clusterFields[idx] and idx < len(col_info['names']):
            cols.append(idx)
    assert len(cols) > 1, 'At least two cluster fields must be selected'
    plot_data = plot_data[:, cols]
    min_max_scaler = sklearn.preprocessing.MinMaxScaler(
        feature_range=[
            report.clusterScaleMin,
            report.clusterScaleMax,
        ])
    x_scale = min_max_scaler.fit_transform(plot_data)
    group = None
    count = report.clusterCount
    if report.clusterMethod == 'kmeans':
        k_means = sklearn.cluster.KMeans(init='k-means++', n_clusters=count, n_init=report.clusterKmeansInit, random_state=report.clusterRandomSeed)
        k_means.fit(x_scale)
        k_means_cluster_centers = np.sort(k_means.cluster_centers_, axis=0)
        k_means_labels = sklearn.metrics.pairwise.pairwise_distances_argmin(x_scale, k_means_cluster_centers)
        group = k_means_labels
    elif report.clusterMethod == 'gmix':
        gmm = sklearn.mixture.GaussianMixture(n_components=count, random_state=report.clusterRandomSeed)
        gmm.fit(x_scale)
        group = gmm.predict(x_scale)
    elif report.clusterMethod == 'dbscan':
        db = sklearn.cluster.DBSCAN(eps=report.clusterDbscanEps, min_samples=3).fit(x_scale)
        group = db.fit_predict(x_scale) + 1.
        count = len(set(group))
    elif report.clusterMethod == 'agglomerative':
        agg_clst = sklearn.cluster.AgglomerativeClustering(n_clusters=count, linkage='complete', affinity='euclidean')
        agg_clst.fit(x_scale)
        group = agg_clst.labels_
    else:
        assert False, 'unknown clusterMethod: {}'.format(report.clusterMethod)
    return {
        'group': group.tolist(),
        'count': count,
    }


def _enable_steering(data):
    sim_dir = _epics_dir(data['simulationId'])
    if sim_dir.exists():
        #TODO(pjm): use save to tmp followed by mv for atomicity
        simulation_db.write_json(sim_dir.join(STEERING_FILE), data['beamSteering'])
    return {}


def _epics_dir(sim_id):
    return simulation_db.simulation_dir(SIM_TYPE, sim_id).join('epicsServerAnimation')


def _fit_to_equation(x, y, equation, var, params):
    # TODO: must sanitize input - sympy uses eval
    sym_curve = sympy.sympify(equation)
    sym_str = var + ' ' + ' '.join(params)

    syms = sympy.symbols(sym_str)
    sym_curve_l = sympy.lambdify(syms, sym_curve, 'numpy')

    # feed a uniform x distribution to the function?  or sort?
    #x_uniform = np.linspace(np.min(x), np.max(x), 100)

    p_vals, pcov = scipy.optimize.curve_fit(sym_curve_l, x, y, maxfev=500000)
    sigma = np.sqrt(np.diagonal(pcov))

    p_subs = []
    p_subs_min = []
    p_subs_max = []

    # exclude the symbol of the variable when subbing
    for sidx, p in enumerate(p_vals, 1):
        sig = sigma[sidx - 1]
        p_min = p - 2 * sig
        p_max = p + 2 * sig
        s = syms[sidx]
        p_subs.append((s, p))
        p_subs_min.append((s, p_min))
        p_subs_max.append((s, p_max))
    y_fit = sym_curve.subs(p_subs)
    y_fit_min = sym_curve.subs(p_subs_min)
    y_fit_max = sym_curve.subs(p_subs_max)

    # used for the laTeX label - rounding should take size of uncertainty into account
    y_fit_rounded = sym_curve.subs(p_subs)

    y_fit_l = sympy.lambdify(var, y_fit, 'numpy')
    y_fit_min_l = sympy.lambdify(var, y_fit_min, 'numpy')
    y_fit_max_l = sympy.lambdify(var, y_fit_max, 'numpy')

    latex_label = sympy.latex(y_fit_rounded, mode='inline')
    #TODO(pjm): round rather than truncate?
    latex_label = re.sub(r'(\.\d{4})\d+', r'\1', latex_label)
    y_fit_l(x)
    y_fit_min_l(x)
    y_fit_max_l(x)
    return y_fit_l(x), y_fit_min_l(x), y_fit_max_l(x), p_vals, sigma, latex_label


def _generate_parameters_file(run_dir, data):
    report = data['report'] if 'report' in data else None
    if report and report != 'epicsServerAnimation':
        return ''
    #template_common.validate_models(data, simulation_db.get_schema(SIM_TYPE))

    # copy model values into beamline elements
    kicker_values = []
    count = 0
    for idx in range(len(data.models.elements)):
        el = data.models.elements[idx]
        key = '{}{}'.format(el.type, el._id)
        if key in data.models:
            data.models.elements[idx] = data.models[key]
            el = data.models.elements[idx]
        if el.type == 'KICKER':
            kicker_values += [el.hkick, el.vkick]
            count += 1
            el.hkick = '{' + 'vagrant_corrector{}_HCurrent'.format(count) + '}'
            el.vkick = '{' + 'vagrant_corrector{}_VCurrent'.format(count) + '}'
    if run_dir:
        np.save(str(run_dir.join(CURRENT_FILE)), np.array([CURRENT_FIELDS, kicker_values]))
    v = template_common.flatten_data(data['models'], {})
    from sirepo.template import elegant
    #TODO(pjm): calling private template.elegant._build_beamline_map()
    data.models.commands = []
    v['currentFile'] = CURRENT_FILE
    v['fodoLattice'] = elegant.generate_lattice(data, elegant._build_filename_map(data), elegant._build_beamline_map(data), v)
    v['BPM_FIELDS'] = BPM_FIELDS
    v['CURRENT_FIELDS'] = CURRENT_FIELDS
    return template_common.render_jinja(SIM_TYPE, v)


def _get_fit_report(report, plot_data, col_info):
    col1 = _safe_index(col_info, report.x)
    col2 = _safe_index(col_info, report.y1)
    x_vals = plot_data[:, col1] * col_info['scale'][col1]
    y_vals = plot_data[:, col2] * col_info['scale'][col2]
    fit_y, fit_y_min, fit_y_max, param_vals, param_sigmas, latex_label = _fit_to_equation(
        x_vals,
        y_vals,
        report.fitEquation,
        report.fitVariable,
        report.fitParameters,
    )
    plots = [
        {
            'points': y_vals.tolist(),
            'label': 'data',
            'style': 'scatter',
        },
        {
            'points': fit_y.tolist(),
            'label': 'fit',
        },
        {
            'points': fit_y_min.tolist(),
            'label': 'confidence',
            '_parent': 'confidence'
        },
        {
            'points': fit_y_max.tolist(),
            'label': '',
            '_parent': 'confidence'
        }
    ]
    return template_common.parameter_plot(x_vals.tolist(), plots, {}, {
        'title': '',
        'x_label': _label(col_info, col1),
        'y_label': _label(col_info, col2),
        'summaryData': {
            'p_vals': param_vals.tolist(),
            'p_errs': param_sigmas.tolist(),
        },
        'latex_label': latex_label
    })


def _init_default_beamline(data):
    #TODO(pjm): hard-coded beamline for now, using elegant format
    data.models.elements = [
            {
                '_id': 8,
                'l': 0.1,
                'name': 'drift',
                'type': 'DRIF'
            },
            {
                '_id': 10,
                'hkick': 0,
                'name': 'HV_KICKER_1',
                'type': 'KICKER',
                'vkick': 0
            },
            {
                '_id': 12,
                'hkick': 0,
                'name': 'HV_KICKER_2',
                'type': 'KICKER',
                'vkick': 0
            },
            {
                '_id': 13,
                'hkick': 0,
                'name': 'HV_KICKER_3',
                'type': 'KICKER',
                'vkick': 0
            },
            {
                '_id': 14,
                'hkick': 0,
                'name': 'HV_KICKER_4',
                'type': 'KICKER',
                'vkick': 0
            },
            {
                '_id': 24,
                'k1': -5,
                'l': 0.05,
                'name': 'F_QUAD_1',
                'type': 'QUAD',
            },
            {
                '_id': 25,
                'k1': 5,
                'l': 0.05,
                'name': 'D_QUAD_1',
                'type': 'QUAD',
            },
            {
                '_id': 30,
                'k1': -5,
                'l': 0.05,
                'name': 'F_QUAD_2',
                'type': 'QUAD',
            },
            {
                '_id': 31,
                'k1': 5,
                'l': 0.05,
                'name': 'D_QUAD_2',
                'type': 'QUAD',
            },
            {
                '_id': 9,
                'name': 'BPM_1',
                'type': 'WATCH',
                'filename': '1',
            },
            {
                '_id': 27,
                'name': 'BPM_2',
                'type': 'WATCH',
                'filename': '1',
            },
            {
                '_id': 28,
                'name': 'BPM_3',
                'type': 'WATCH',
                'filename': '1',
            },
            {
                '_id': 29,
                'name': 'BPM_4',
                'type': 'WATCH',
                'filename': '1',
            }
    ]
    data.models.beamlines = [
        {
            'id': 1,
            'items': [
                8, 8, 10, 8, 8, 9, 8, 8,
                8, 8, 12, 8, 8, 27, 8, 8,
                8, 24, 8, 8, 25, 8,
                8, 8, 13, 8, 8, 28, 8, 8,
                8, 8, 14, 8, 8, 29, 8, 8,
                8, 30, 8, 8, 31, 8,
            ],
            'name': 'beamline',
        },
    ]


def _label(col_info, idx):
    name = col_info['names'][idx]
    units = col_info['units'][idx]
    if units:
        return '{} [{}]'.format(name, units)
    return name


def _load_file_with_history(report, path, col_info):
    res = np.genfromtxt(path, delimiter=',', skip_header=col_info['header_row_count'])
    if 'history' in report:
        for action in report.history:
            if action.action == 'trim':
                idx = _safe_index(col_info, action.trimField)
                scale = col_info['scale'][idx]
                res = res[(res[:,idx] * scale >= action.trimMin) & (res[:, idx] * scale <= action.trimMax)]
            elif action.action == 'cluster':
                report2 = copy.deepcopy(report)
                report2.update(action)
                clusters = _compute_clusters(report2, res, col_info)
                labels = np.array(clusters['group'])
                res = res[labels == action.clusterIndex,:]
    return res


def _optimization_values(run_dir):
    opt_file = run_dir.join(OPTIMIZER_RESULT_FILE)
    res = None
    if opt_file.exists():
        res = simulation_db.read_json(opt_file)
        os.remove(str(opt_file))
    return res



def _read_monitor_file(monitor_path):
    monitor_values = {}
    count = 0
    #TODO(pjm): currently reading entire file to get list of current values (most recent at bottom)
    for line in pkio.read_text(str(monitor_path)).split("\n"):
        m = re.match(r'(\S+).*?\s([\d\.\e\-\+]+)\s*$', line)
        if not m:
            continue
        var_name = m.group(1)
        var_value = m.group(2)
        var_name = re.sub(r'^vagrant:', '', var_name)
        var_name = re.sub(r':', '_', var_name)
        monitor_values[var_name] = float(var_value)
        count += 1
    return monitor_values, count


def _read_epics_kickers(data):
    epics_settings = data.epicsServerAnimation
    return {
        'kickers': read_epics_values(epics_settings.serverAddress, CURRENT_FIELDS),
    }


def _report_info(run_dir, data):
    report = data.models[data.report]
    path = _analysis_data_path(run_dir, data)
    col_info = _column_info(path)
    plot_data = _load_file_with_history(report, path, col_info)
    return report, col_info, plot_data


def _safe_index(col_info, idx):
    idx = int(idx or 0)
    if idx >= len(col_info['names']):
        idx = 1
    return idx


def _update_epics_kicker(data):
    epics_settings = data.epicsServerAnimation
    # data validation is done by casting values to int() or float()
    prefix = 'vagrant:corrector{}:'.format(int(data['epics_field']))
    fields = []
    values = []
    for f in 'h', 'v':
        field = '{}{}Current'.format(prefix, f.upper())
        fields.append(field)
        values.append(float(data['kicker']['{}kick'.format(f)]))
    update_epics_kickers(epics_settings, _epics_dir(data.simulationId), fields, values)
    return {}
