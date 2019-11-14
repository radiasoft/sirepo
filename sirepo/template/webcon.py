# -*- coding: utf-8 -*-
u"""Webcon execution template.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo import util
from sirepo.template import template_common
import StringIO
import copy
import csv
import math
import numpy as np
import os
import os.path
import random
import re
import scipy.fftpack
import scipy.optimize
import scipy.signal
import sirepo.sim_data
import sklearn.cluster
import sklearn.metrics.pairwise
import sklearn.mixture
import sklearn.preprocessing
import sympy

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

SIM_TYPE = 'webcon'

BPM_FIELDS = [
    'sr_epics:bpm1:hpos',
    'sr_epics:bpm1:vpos',
    'sr_epics:bpm2:hpos',
    'sr_epics:bpm2:vpos',
    'sr_epics:bpm3:hpos',
    'sr_epics:bpm3:vpos',
    'sr_epics:bpm4:hpos',
    'sr_epics:bpm4:vpos',
]

CURRENT_FIELDS = [
    'sr_epics:corrector1:HCurrent',
    'sr_epics:corrector1:VCurrent',
    'sr_epics:corrector2:HCurrent',
    'sr_epics:corrector2:VCurrent',
    'sr_epics:corrector3:HCurrent',
    'sr_epics:corrector3:VCurrent',
    'sr_epics:corrector4:HCurrent',
    'sr_epics:corrector4:VCurrent',
]


CURRENT_FILE = 'currents.npy'

MONITOR_LOGFILE = 'monitor.log'

OPTIMIZER_RESULT_FILE = 'opt.json'

STEERING_FILE = 'steering.json'

_DIM_PLOT_COLORS = [
    '#d0c383',
    '#9400d3'
]

_MONITOR_TO_MODEL_FIELDS = pkcollections.Dict()

_SCHEMA = simulation_db.get_schema(SIM_TYPE)

_SETTINGS_PLOT_COLORS = [
    '#ff0000',
    '#f4a442',
    '#e9ed2d',
    '#44c926',
    '#2656c9',
    '#3d25c4',
    '#7e23c4'
]

_SETTINGS_KICKER_SYMBOLS = PKDict(
    hkick='square',
    hpos='square',
    x='square',
    vkick='triangle-up',
    vpos='triangle-up',
    y='triangle-up'
)

def background_percent_complete(report, run_dir, is_running):
    if report == 'epicsServerAnimation' and is_running:
        monitor_file = run_dir.join(MONITOR_LOGFILE)
        if monitor_file.exists():
            values, count, start_time = _read_monitor_file(monitor_file)
            return PKDict(
                percentComplete=0,
                frameCount=count,
                summaryData=PKDict(
                    monitorValues=values,
                    optimizationValues=_optimization_values(run_dir),
                ),
            )
    if report == 'correctorSettingAnimation':
        #pkdp('background_percent_complete for correctorSettingAnimation')
        monitor_file = run_dir.join(MONITOR_LOGFILE)
        if monitor_file.exists():
            values, count, start_time = _read_monitor_file(monitor_file, True)
            return PKDict(
                percentComplete=0,
                frameCount=count,
                summaryData=PKDict(
                    monitorValues=values,
                ),
            )
    return PKDict(
        percentComplete=0,
        frameCount=0,
    )


def epics_env(server_address):
    env = os.environ.copy()
    env['EPICS_CA_AUTO_ADDR_LIST'] = 'NO'
    env['EPICS_CA_ADDR_LIST'] = server_address
    env['EPICS_CA_SERVER_PORT'] = server_address.split(':')[1]
    return env


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
        plots.append(PKDict(
            points=(y * col_info['scale'][y_idx]).tolist(),
            label=_label(col_info, y_idx),
            style='line' if 'action' in report and report.action == 'fft' else 'scatter',
        ))
    return template_common.parameter_plot(
        x,
        plots,
        PKDict(),
        PKDict(
            title='',
            y_label='',
            x_label=_label(col_info, x_idx),
            clusters=clusters,
            summaryData=PKDict(),
        ),
    )


def get_application_data(data):
    if data['method'] == 'column_info':
        data = PKDict(
            models=PKDict(
                analysisData=data['analysisData'],
            ),
        )
        return PKDict(
            columnInfo=_column_info(
                str(_SIM_DATA.lib_file_abspath(_analysis_data_path(data))),
            ),
        )
    if data['method'] == 'update_kicker':
        return _update_epics_kicker(data)
    if data['method'] == 'read_kickers':
        return _read_epics_kickers(data)
    if data['method'] == 'enable_steering':
        return _enable_steering(data)
    assert False, 'unknown application_data method: {}'.format(data['method'])


def get_beam_pos_report(run_dir, data):
    monitor_file = run_dir.join('../epicsServerAnimation/').join(MONITOR_LOGFILE)
    assert monitor_file.exists(), 'no beam position history'
    history, num_records, start_time = _read_monitor_file(monitor_file, True)
    assert len(history) > 0, 'no beam position history'
    x_label = 'z [m]'
    x, plots, colors = _beam_pos_plots(data, history, start_time)
    assert len(plots), 'no beam position history'
    return template_common.parameter_plot(
        x.tolist(),
        plots,
        PKDict(),
        PKDict(
            title='',
            y_label='[m]',
            x_label=x_label,
            summaryData={},
        ),
        colors,
    )


def get_data_file(run_dir, model, frame, options=None):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    report = data.models[data.report]
    path = str(run_dir.join(_analysis_data_path(data)))
    col_info = _column_info(path)
    plot_data = _load_file_with_history(report, path, col_info)
    buf = StringIO.StringIO()
    buf.write(','.join(col_info['names']) + '\n')
    np.savetxt(buf, plot_data, delimiter=',')
    return '{}.csv'.format(model), buf.getvalue(), 'text/csv'


def get_fft(run_dir, data):
    data.report = _SIM_DATA.webcon_analysis_report_name_for_fft(data)
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
    freqs = scipy.fftpack.fftfreq(len(fft_out), d=sample_period) #/ sample_period
    w = 2. * np.pi * freqs[0:half_num_samples]

    # is signal to noise useful?
    m = y.mean()
    sd = y.std()
    s2n = np.where(sd == 0, 0, m / sd)

    coefs = (2.0 / num_samples) * np.abs(fft_out[0:half_num_samples])
    peaks, props = scipy.signal.find_peaks(coefs)
    found_freqs = zip(peaks, np.around(w[peaks], 3))
    #pkdp('!FOUND {} FREQS {}, S2N {}, MEAN {}', len(found_freqs), found_freqs, s2n, m)

    # focus in on the peaks?
    # maybe better in browser
    bin_spread = 10
    min_bin = max(0, peaks[0] - bin_spread)
    max_bin = min(half_num_samples, peaks[-1] + bin_spread)
    yy = 2.0 / num_samples * np.abs(fft_out[min_bin:max_bin])
    max_yy = np.max(yy)
    yy_norm = yy / (max_yy if max_yy != 0 else 1)
    ww = 2. * np.pi * freqs[min_bin:max_bin]
    #plots = [
    #    {
    #        'points': yy_norm.tolist(),
    #        'label': 'fft',
    #    },
    #]

    max_y = np.max(y)
    y_norm = y / (max_y if max_y != 0 else 1)
    plots = [PKDict(points=y_norm.tolist(), label='fft')]

    #TODO(mvk): figure out appropriate labels from input
    w_list = w.tolist()
    return template_common.parameter_plot(
        w_list,
        plots,
        PKDict(),
        PKDict(
            title='',
            y_label=_label(col_info, 1),
            x_label='f[Hz]',
            preserve_units=False,
            #'x_label': _label(col_info, 0) + '^-1',
            summaryData=PKDict(
                freqs=found_freqs,
                minFreq=w_list[0],
                maxFreq=w_list[-1]
            ),
            #'latex_label': latex_label
        ),
    )


def get_settings_report(run_dir, data):
    monitor_file = run_dir.join('../epicsServerAnimation/').join(MONITOR_LOGFILE)
    assert monitor_file.exists(), 'no settings history'
    history, num_records, start_time = _read_monitor_file(monitor_file, True)
    o = data.models.correctorSettingReport.plotOrder
    plot_order = o if o is not None else 'time'
    if plot_order == 'time':
        x, plots, colors = _setting_plots_by_time(data, history, start_time)
        x_label = 't [s]'
    else:
        x, plots, colors = _setting_plots_by_position(data, history, start_time)
        x_label = 'z [m]'
    assert len(plots), 'no settings history'
    return template_common.parameter_plot(
        x.tolist(),
        plots,
        PKDict(),
        PKDict(
            title='',
            y_label='[rad]',
            x_label=x_label,
            summaryData=PKDict(),
            ),
        colors,
    )


#TODO(robnagler) not supported
#def get_simulation_frame(run_dir, data, model_data):
#    frame_index = int(data['frameIndex'])
#    if data['modelName'] == 'correctorSettingAnimation':
#        #data_file = open_data_file(run_dir, data['modelName'], frame_index)
#        return get_settings_report(run_dir, data)
#    raise RuntimeError('{}: unknown simulation frame model'.format(data['modelName']))


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
            return PKDict()
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


def _analysis_data_path(data):
    return _SIM_DATA.webcon_analysis_data_file(data)


def _beam_pos_plots(data, history, start_time):
    plots = []
    c = []

    bpms = _bpm_readings_for_plots(data, history, start_time)
    for t_idx, t in enumerate(bpms['t']):
        for d_idx, dim in enumerate(['x', 'y']):
            c.append(_DIM_PLOT_COLORS[d_idx % len(_DIM_PLOT_COLORS)])
            # same color, fade to alpha 0.2
            c_mod = _hex_color_to_rgb(c[-1])
            c_mod[3] = 0.2
            plot = PKDict(
                points=bpms[dim][t_idx],
                x_points=bpms['z'],
                style='line',
                symbol=_SETTINGS_KICKER_SYMBOLS[dim],
                colorModulation=c_mod,
                modDirection=-1
            )
            if t_idx < len(bpms['t']) - 1:
                plot['_parent'] = dim
                plot['label'] = ''
            else:
                plot['label'] = dim
            plots.append(plot)
    return np.array(bpms['z']), plots, c


# arrange historical data for ease of plotting
def _bpm_readings_for_plots(data, history, start_time):

    bpms = _monitor_data_for_plots(data, history, start_time, 'WATCH')
    all_times = np.array([])
    z = np.array([])
    bpm_sorted = []
    for element_name in sorted([b for b in bpms]):
        if element_name not in [bpm[0] for bpm in bpm_sorted]:
            bpm_sorted.append((element_name, []))
        b_readings = bpms[element_name]
        for reading_name in sorted([r for r in b_readings]):
            pos = b_readings[reading_name]['position'][0]
            if pos not in z:
                z = np.append(z, pos)
            bpm_sorted[-1][1].append(
                PKDict(
                    reading=reading_name,
                    vals=b_readings[reading_name]['vals'],
                    times=b_readings[reading_name]['times']
                ),
            )
            all_times = np.append(all_times, b_readings[reading_name]['times'])

    all_times = np.sort(np.unique(all_times))

    for bpm in bpm_sorted:
        for reading in bpm[1]:
            # fill in missing times - use previous monitor values
            v = np.array(reading['vals'])
            t = np.array(reading['times'])
            for a_t_idx, a_t in enumerate(all_times):
                if a_t in t:
                    continue
                d_ts = a_t - t
                deltas = [dt for dt in (a_t - t) if dt > 0]
                if not len(deltas):
                    return None
                prev_dt = min(deltas)
                dt_idx = np.where(d_ts == prev_dt)[0][0] + 1
                if dt_idx < np.alen(t):
                    t = np.insert(t, dt_idx, a_t)
                    v = np.insert(v, dt_idx, v[dt_idx - 1])
                else:
                    t = np.append(t, a_t)
                    v = np.append(v, v[dt_idx - 1])
            reading['vals'] = v.tolist()

    x = []
    y = []
    t = []
    time_window = data.models.beamPositionReport.numHistory
    period = data.models.beamPositionReport.samplePeriod
    current_time = all_times[-1]

    t_indexes = np.where(
        ((all_times > current_time - time_window) if time_window > 0 else (all_times >= 0)) &
        (all_times % period == 0)
    )
    for t_idx in t_indexes[0]:
        time = all_times[t_idx]
        t.append(time)
        xt = []
        yt = []
        for z_idx, zz in enumerate(z):
            readings = bpm_sorted[z_idx][1]
            xt.append(readings[0]['vals'][t_idx])
            yt.append(readings[1]['vals'][t_idx])
        x.append(xt)
        y.append(yt)
    return PKDict(
        x=x,
        y=y,
        z=z.tolist(),
        t=t
    )


def _build_monitor_to_model_fields(data):
    if _MONITOR_TO_MODEL_FIELDS:
        return
    watch_count = 0
    kicker_count = 0
    for el_idx in range(0, len(data.models.elements)):
        el = data.models.elements[el_idx]
        t = el.type
        if t not in ['WATCH', 'KICKER']:
            continue
        if t == 'WATCH':
            watch_count += 1
            for setting in ['hpos', 'vpos']:
                mon_setting = 'bpm{}_{}'.format(watch_count, setting)
                _MONITOR_TO_MODEL_FIELDS[mon_setting] = PKDict(
                    element=el.name,
                    setting=setting
                )
        elif t == 'KICKER':
            kicker_count += 1
            for setting in ['hkick', 'vkick']:
                mon_setting = 'corrector{}_{}'.format(kicker_count, 'HCurrent' if setting == 'hkick' else 'VCurrent')
                _MONITOR_TO_MODEL_FIELDS[mon_setting] = PKDict(
                    element=el.name,
                    setting=setting
                )


def _centroid_ranges(history):
    r = [
        [np.finfo('d').max, np.finfo('d').min],
        [np.finfo('d').max, np.finfo('d').min]
    ]
    for ch in history:
        for cz in ch:
            for i in range(0, 2):
                r[i][0] = min(r[i][0], cz[i])
                r[i][1] = max(r[i][1], cz[i])
    return r


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
    res = PKDict(
        header_row_count=header_row_count,
        names=[],
        units=[],
        scale=[],
    )
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
    return PKDict(
        group=group.tolist(),
        count=count,
    )


def _element_by_name(data, e_name):
    return [el for el in data.models.elements if el['name'] == e_name][0]


def _element_positions(data):
    bl = data.models.beamlines[0]
    e_ids = bl['items']
    els_with_length = _elements_of_types(data, ['DRIF', 'QUAD'])
    d_ids = set([])
    for d in els_with_length:
        d_ids.add(d['_id'])
    positions = np.array([])
    for e_idx, e_id in enumerate(e_ids):
        z = 0
        for e_jdx in range(0, e_idx):
            elj = [el for el in data.models.elements if el['_id'] == e_ids[e_jdx]][0]
            z += (elj['l'] if 'l' in elj else 0)
        positions = np.append(positions, z)
    return positions


def _elements_of_types(data, types):
    return [
        m for m in data.models.elements if 'type' in m and m.type in types
    ]


def _enable_steering(data):
    sim_dir = _epics_dir(data['simulationId'])
    if sim_dir.exists():
        #TODO(pjm): use save to tmp followed by mv for atomicity
        simulation_db.write_json(sim_dir.join(STEERING_FILE), data['beamSteering'])
    return PKDict()


def _epics_dir(sim_id):
    return simulation_db.simulation_dir(SIM_TYPE, sim_id).join('epicsServerAnimation')


def _fit_to_equation(x, y, equation, var, params):
    # TODO: must sanitize input - sympy uses eval

    # These security measures taken so far:
    #     Whitelist of allowed functions and other symbols as defined in the schema
    #     Variable and parameters must be 1 alphabetic character

    eq_ops = [t for t in _tokenize_equation(equation) if t != var and t not in params]
    eq_ops_rejected = [op for op in eq_ops if op not in _SCHEMA.constants.allowedEquationOps]
    assert len(eq_ops_rejected) == 0, util.err(eq_ops_rejected, 'operation fobidden')
    assert _validate_eq_var(var), util.err(var, 'invalid variable name')
    assert all([_validate_eq_var(p) for p in re.split(r'\s*,\s*', params)]),\
        util.err(params, 'invalid parameter name(s)')

    sym_curve = sympy.sympify(equation)
    sym_str = var + ' ' + ' '.join(params)

    syms = sympy.symbols(sym_str)
    sym_curve_l = sympy.lambdify(syms, sym_curve, 'numpy')

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
    x_uniform = np.linspace(np.min(x), np.max(x), 100)
    return x_uniform, y_fit_l(x_uniform), y_fit_min_l(x_uniform), y_fit_max_l(x_uniform), p_vals, sigma, latex_label


def _generate_parameters_file(run_dir, data):
    report = data.get('report', None)
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
            el.hkick = '{' + 'sr_epics_corrector{}_HCurrent'.format(count) + '}'
            el.vkick = '{' + 'sr_epics_corrector{}_VCurrent'.format(count) + '}'
    if run_dir:
        np.save(str(run_dir.join(CURRENT_FILE)), np.array([CURRENT_FIELDS, kicker_values]))
    res, v = template_common.generate_parameters_file(data)
    from sirepo.template import elegant
    #TODO(pjm): calling private template.elegant._build_beamline_map()
    data.models.commands = []
    v['currentFile'] = CURRENT_FILE
    v['fodoLattice'] = elegant.webcon_generate_lattice(data)
    v['BPM_FIELDS'] = BPM_FIELDS
    v['CURRENT_FIELDS'] = CURRENT_FIELDS
    return res + template_common.render_jinja(SIM_TYPE, v)


def _get_fit_report(report, plot_data, col_info):
    col1 = _safe_index(col_info, report.x)
    col2 = _safe_index(col_info, report.y1)
    x_vals = plot_data[:, col1] * col_info['scale'][col1]
    y_vals = plot_data[:, col2] * col_info['scale'][col2]
    fit_x, fit_y, fit_y_min, fit_y_max, param_vals, param_sigmas, latex_label = _fit_to_equation(
        x_vals,
        y_vals,
        report.fitEquation,
        report.fitVariable,
        report.fitParameters,
    )
    plots = [
        PKDict(
            points=y_vals.tolist(),
            label='data',
            style='scatter',
        ),
        PKDict(
            points=fit_y.tolist(),
            x_points=fit_x.tolist(),
            label='fit',
        ),
        PKDict(
            points=fit_y_min.tolist(),
            x_points=fit_x.tolist(),
            label='confidence',
            _parent='confidence'
        ),
        PKDict(
            points=fit_y_max.tolist(),
            x_points=fit_x.tolist(),
            label='',
            _parent='confidence'
        ),
    ]
    return template_common.parameter_plot(
        x_vals.tolist(),
        plots,
        PKDict(),
        PKDict(
            title='',
            x_label=_label(col_info, col1),
            y_label=_label(col_info, col2),
            summaryData=PKDict(
                p_vals=param_vals.tolist(),
                p_errs=param_sigmas.tolist(),
            ),
            latex_label=latex_label
        ),
    )


def _hex_color_to_rgb(color):
    rgb = [float(int(color.lstrip('#')[i:i + 2], 16)) for i in [0, 2, 4]]
    rgb.append(1.0)
    return rgb


# arrange historical data for ease of plotting
def _kicker_settings_for_plots(data, history, start_time):
    return _monitor_data_for_plots(data, history, start_time, 'KICKER')


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


def _monitor_data_for_plots(data, history, start_time, type):
    m_data = PKDict()
    _build_monitor_to_model_fields(data)
    for mon_setting in history:
        s_map = _MONITOR_TO_MODEL_FIELDS[mon_setting]
        el_name = s_map.element
        el = _element_by_name(data, el_name)
        if el.type != type:
            continue
        if el_name not in m_data:
            m_data[el_name] = PKDict()
        el_setting = s_map.setting
        h = history[mon_setting]
        t_deltas = [
            round(((dt.days * 86400) + dt.seconds + (dt.microseconds / 1000000))) for dt in
            [t - start_time for t in h.times]
        ]
        pos = np.full(len(t_deltas), _position_of_element(data, el['_id']))
        m_data[el_name][el_setting] = PKDict(
            vals=h.vals,
            times=t_deltas,
            position=pos.tolist()
        )
    return m_data


def _optimization_values(run_dir):
    opt_file = run_dir.join(OPTIMIZER_RESULT_FILE)
    res = None
    if opt_file.exists():
        res = simulation_db.read_json(opt_file)
        os.remove(str(opt_file))
    return res


# only works for unique ids (so not drifts)
def _position_of_element(data, id):
    p = _element_positions(data)
    bl = data.models.beamlines[0]
    items = bl['items']
    i = items.index(id)
    return p[i]


def _read_epics_kickers(data):
    epics_settings = data.epicsServerAnimation
    return PKDict(
        kickers=read_epics_values(epics_settings.serverAddress, CURRENT_FIELDS),
    )


def _read_monitor_file(monitor_path, history=False):
    from datetime import datetime
    monitor_values = PKDict()
    count = 0
    min_time = datetime.max
    #TODO(pjm): currently reading entire file to get list of current values (most recent at bottom)
    for line in pkio.read_text(str(monitor_path)).split("\n"):
        m = re.match(r'(\S+)(.*?)\s([\d\.\e\-\+]+)\s*$', line)
        if not m:
            continue
        var_name = m.group(1)
        timestamp = m.group(2)
        t = datetime.strptime(timestamp.strip(), '%Y-%m-%d %H:%M:%S.%f')
        min_time = min(min_time, t)
        var_value = m.group(3)
        var_name = re.sub(r'^sr_epics:', '', var_name)
        var_name = re.sub(r':', '_', var_name)
        if not history:
            monitor_values[var_name] = float(var_value)
        else:
            if var_name not in monitor_values:
                monitor_values[var_name] = PKDict(
                    vals=[],
                    times=[]
                )
            monitor_values[var_name].vals.append(float(var_value))
            monitor_values[var_name].times.append(t)
        count += 1
    return monitor_values, count, min_time


def _report_info(run_dir, data):
    report = data.models[data.report]
    path = str(run_dir.join(_analysis_data_path(data)))
    col_info = _column_info(path)
    plot_data = _load_file_with_history(report, path, col_info)
    return report, col_info, plot_data


def _safe_index(col_info, idx):
    idx = int(idx or 0)
    if idx >= len(col_info['names']):
        idx = 1
    return idx


def _setting_plots_by_position(data, history, start_time):
    plots = []
    all_z = np.array([0.0])
    c = []
    kickers = _kicker_settings_for_plots(data, history, start_time)
    k_sorted = []
    for k_name in sorted([k for k in kickers]):
        if k_name not in [kk[0] for kk in k_sorted]:
            k_sorted.append((k_name, []))
        k_s = kickers[k_name]
        for s in sorted([s for s in k_s]):
            k_sorted[-1][1].append(
                PKDict(
                    setting=s,
                    vals=k_s[s]['vals'],
                    position=k_s[s]['position'],
                    times=k_s[s]['times']
                )
            )
            all_z = np.append(all_z, k_s[s]['position'])
    time_window = data.models.correctorSettingReport.numHistory
    period = data.models.correctorSettingReport.samplePeriod
    for k_idx, k in enumerate(k_sorted):
        for s in k[1]:
            times = np.array(s['times'])
            current_time = times[-1]
            t_indexes = np.where(
                ((times > current_time - time_window) if time_window > 0 else (times >= 0)) &
                (times % period == 0)
            )[0]
            if len(t_indexes) == 0:
                continue
            c.append(_SETTINGS_PLOT_COLORS[k_idx % len(_SETTINGS_PLOT_COLORS)])
            # same color, fade to alpha 0.2
            c_mod = _hex_color_to_rgb(c[-1])
            c_mod[3] = 0.2
            plots.append(PKDict(
                points=np.array(s['vals'])[t_indexes].tolist(),
                x_points=np.array(s['position'])[t_indexes].tolist(),
                label='{} {}'.format(k[0], s['setting']),
                style='scatter',
                symbol=_SETTINGS_KICKER_SYMBOLS[s['setting']],
                colorModulation=c_mod,
                modDirection=-1
            ))
    np.append(all_z, _element_positions(data)[-1])
    return np.array([0.0, _element_positions(data)[-1]]), plots, c


def _setting_plots_by_time(data, history, start_time):
    plots = []
    current_time = 0
    c = []
    kickers = _kicker_settings_for_plots(data, history, start_time)
    k_sorted = []
    for k_name in sorted([k for k in kickers]):
        if k_name not in [kk[0] for kk in k_sorted]:
            k_sorted.append((k_name, []))
        k_s = kickers[k_name]
        for s in sorted([s for s in k_s]):
            current_time = max(current_time, np.max(k_s[s]['times']))
            k_sorted[-1][1].append(
                PKDict(
                    setting=s,
                    vals=k_s[s]['vals'],
                    times=k_s[s]['times']
                ),
            )

    time_window = data.models.correctorSettingReport.numHistory
    period = data.models.correctorSettingReport.samplePeriod

    for k_idx, k in enumerate(k_sorted):
        for s in k[1]:
            times = np.array(s['times'])
            t_indexes = np.where(
                ((times > current_time - time_window) if time_window > 0 else (times >= 0)) &
                (times % period == 0)
            )[0]
            if len(t_indexes) == 0:
                continue
            c.append(_SETTINGS_PLOT_COLORS[k_idx % len(_SETTINGS_PLOT_COLORS)])
            plots.append(PKDict(
                points=np.array(s['vals'])[t_indexes].tolist(),
                x_points=times[t_indexes].tolist(),
                label='{} {}'.format(k[0], s['setting']),
                style='line',
                symbol=_SETTINGS_KICKER_SYMBOLS[s['setting']]
            ))
    return np.array([current_time - time_window, current_time]), plots, c


def _tokenize_equation(eq):
    return [t for t in re.split(r'[-+*/^|%().0-9\s]', (eq if eq is not None else '')) if len(t) > 0]


def _update_epics_kicker(data):
    epics_settings = data.epicsServerAnimation
    # data validation is done by casting values to int() or float()
    prefix = 'sr_epics:corrector{}:'.format(int(data['epics_field']))
    fields = []
    values = []
    for f in 'h', 'v':
        field = '{}{}Current'.format(prefix, f.upper())
        fields.append(field)
        values.append(float(data['kicker']['{}kick'.format(f)]))
    update_epics_kickers(epics_settings, _epics_dir(data.simulationId), fields, values)
    return PKDict()


def _validate_eq_var(val):
    return len(val) == 1 and re.match(r'^[a-zA-Z]+$', val)
