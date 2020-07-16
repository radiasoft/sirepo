# -*- coding: utf-8 -*-
u"""ML execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkcollections import PKDict
from sirepo import simulation_db
from sirepo.template import template_common
import csv
import re
import sirepo.sim_data
import numpy as np

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

_TRAIN_FILE = 'train.csv'
_TEST_FILE = 'test.csv'
_VALIDATE_FILE = 'validate.csv'


def get_application_data(data, **kwargs):
    if data.method == 'compute_column_info':
        return _compute_column_info(data.dataFile)
    assert False, 'unknown get_application_data: {}'.format(data)


def prepare_sequential_output_file(run_dir, data):
    report = data['report']
    if 'fileColumnReport' in report or 'partitionColumnReport':
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            try:
                save_sequential_report_data(run_dir, data)
            except IOError:
                # the output file isn't readable
                pass


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def save_sequential_report_data(run_dir, sim_in):
    if 'fileColumnReport' in sim_in.report:
        _extract_file_column_report(run_dir, sim_in)
    elif 'partitionColumnReport' in sim_in.report:
        _extract_partition_report(run_dir, sim_in)
    elif sim_in.report == 'partitionSelectionReport':
        _extract_partition_selection(run_dir, sim_in)
    else:
        assert False, 'unknown report: {}'.format(sim_in.report)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _compute_column_info(dataFile):
    path = str(simulation_db.simulation_lib_dir(SIM_TYPE).join(_filename(dataFile.file)))
    if re.search(r'\.npy$', path):
        return _compute_numpy_info(path)
    return _compute_csv_info(path)


def _compute_csv_info(path):
    res = PKDict(
        hasHeaderRow=True,
        rowCount=0,
    )
    row = None
    with open(str(path)) as f:
        for r in csv.reader(f):
            if not row:
                row = r
            res.rowCount += 1
    if not row:
        return PKDict(
            error='Invalid CSV file: no columns detected'
        )
    # csv file may or may not have column names
    # if any value in the first row is numeric, assume no headers
    if len(list(filter(lambda x: template_common.NUMERIC_RE.search(x), row))):
        row = ['column {}'.format(i + 1) for i in range(len(row))]
        res.hasHeaderRow = False
    res.header = row
    res.inputOutput = ['none' for i in range(len(row))]
    return res


def _compute_numpy_info(path):
    assert False, 'not implemented yet'


def _extract_column(run_dir, sim_in, idx):
    y = _read_file_column(
        run_dir,
        _filename(sim_in.models.dataFile.file),
        idx,
        sim_in.models.columnInfo.hasHeaderRow,
    )
    return np.arange(0, len(y)), y


def _extract_file_column_report(run_dir, sim_in):
    idx = sim_in.models[sim_in.report].columnNumber
    x, y = _extract_column(run_dir, sim_in, idx)
    _write_plot(
        x,
        [_plot_info(y)],
        sim_in.models.columnInfo.header[idx],
    )


def _extract_partition_report(run_dir, sim_in):
    idx = sim_in.models[sim_in.report].columnNumber
    d = PKDict(
        train=_read_file_column(run_dir, _TRAIN_FILE, idx),
        test=_read_file_column(run_dir, _TEST_FILE, idx),
        validate=_read_file_column(run_dir, _VALIDATE_FILE, idx),
    )
    r = []
    for name in d:
        _update_range(r, d[name])
    plots = []
    for name in d:
        x, y = _histogram_plot(d[name], r)
        plots.append(_plot_info(y, name))
    _write_plot(
        x,
        plots,
        title=sim_in.models.columnInfo.header[idx],
    )


def _extract_partition_selection(run_dir, sim_in):
    # return report with input0 and output0
    info = sim_in.models.columnInfo
    in_idx = info.inputOutput.index('input')
    out_idx = info.inputOutput.index('output')
    x, y = _extract_column(run_dir, sim_in, in_idx)
    _, y2 = _extract_column(run_dir, sim_in, out_idx)
    _write_plot(
        x,
        [
            _plot_info(y, info.header[in_idx]),
            _plot_info(y2, info.header[out_idx]),
        ],
    )


def _filename(name):
    return _SIM_DATA.lib_file_name_with_model_field('dataFile', 'file', name)


def _generate_parameters_file(data):
    report = data.get('report', '')
    res, v = template_common.generate_parameters_file(data)
    v.dataFileName = _filename(data.models.dataFile.file)
    v.columnTypes = '[' + ','.join([ "'" + v + "'" for v in data.models.columnInfo.inputOutput]) + ']'
    res += template_common.render_jinja(SIM_TYPE, v, 'scale.py')
    if 'fileColumnReport' in report or report == 'partitionSelectionReport':
        return res
    v.hasTrainingAndTesting = v.partition_section0 == 'train_and_test' \
        or v.partition_section1 == 'train_and_test' \
        or v.partition_section2 == 'train_and_test'
    res += template_common.render_jinja(SIM_TYPE, v, 'partition.py')
    if 'partitionColumnReport' in report:
        v.trainFile = _TRAIN_FILE
        v.testFile = _TEST_FILE
        v.validateFile = _VALIDATE_FILE
        res += template_common.render_jinja(SIM_TYPE, v, 'save-partition.py')
        return res
    return res


def _histogram_plot(values, vrange):
    hist = np.histogram(values, bins=20, range=vrange)
    x = []
    y = []
    for i in range(len(hist[0])):
        x.append(hist[1][i])
        x.append(hist[1][i + 1])
        y.append(hist[0][i])
        y.append(hist[0][i])
    x.insert(0, x[0])
    y.insert(0, 0)
    return x, y


def _plot_info(y, label=''):
    return PKDict(points=list(y), label=label)


def _read_file(run_dir, filename, has_header=False):
    res = np.genfromtxt(
        str(run_dir.join(filename)),
        delimiter=',',
        skip_header=1 if has_header else 0,
    )
    if len(res.shape) == 1:
        res.shape = (res.shape[0], 1)
    return res


def _read_file_column(run_dir, filename, idx, has_header=False):
    return _read_file(run_dir, filename, has_header)[:, idx]


def _update_range(vrange, values):
    minv = min(values)
    maxv = max(values)
    if not len(vrange):
        vrange.append(minv)
        vrange.append(maxv)
        return
    if vrange[0] > minv:
        vrange[0] = minv
    if vrange[1] < maxv:
        vrange[1] = maxv


def _write_plot(x, plots, title=''):
    template_common.write_sequential_result(
        PKDict(
            title=title,
            x_range=[float(min(x)), float(max(x))],
            y_label='',
            x_label='',
            x_points=list(x),
            plots=plots,
            y_range=template_common.compute_plot_color_and_range(plots),
        ),
    )
