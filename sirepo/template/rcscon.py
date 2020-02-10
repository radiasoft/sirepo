# -*- coding: utf-8 -*-
u"""RCSCON execution template.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import csv
import numpy as np
import os
import re
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()
_OUTPUT_FILE = PKDict(
    fitOutputFile='fit.csv',
    predictOutputFile='predict.csv',
    testOutputFile='test.csv',
)

def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    csv_file = run_dir.join(_OUTPUT_FILE.fitOutputFile)
    if csv_file.exists():
        line = _read_last_line(csv_file)
        m = re.search(r'^(\d+)', line)
        if m and int(m.group(1)) > 0:
            data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
            max_frame = data.models.neuralNet.epochs
            res.frameCount = int(m.group(1)) + 1
            res.percentComplete = float(res.frameCount) * 100 / max_frame
    return res


def extract_report_data(run_dir, sim_in):
    if 'mlModelGraph' in sim_in.report:
        svg = pkio.read_text('modelGraph.svg')
        simulation_db.write_result(PKDict(svg=svg), run_dir=run_dir)
        return
    idx = sim_in.models[sim_in.report].columnNumber
    x, y, col_name, source_name = _extract_column(run_dir, sim_in, idx)
    simulation_db.write_result(
        _plot_info(
            x,
            [
                PKDict(
                    points=y.tolist(),
                    label=col_name,
                ),
            ],
        ),
        run_dir=run_dir,
    )


def get_application_data(data):
    if data.method == 'compute_column_count':
        return _compute_column_count(data)
    assert False, 'unknown get_application_data: {}'.format(data)


def prepare_output_file(run_dir, sim_in):
    if 'fileColumnReport' not in sim_in.report:
        return
    fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
    if fn.exists():
        fn.remove()
        extract_report_data(run_dir, sim_in)


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def sim_frame(frame_args):
    if frame_args.frameReport == 'epochAnimation':
        return _epoch_animation(frame_args)
    return _fit_animation(frame_args)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _compute_column_count(data):
    lib_dir = simulation_db.simulation_lib_dir(SIM_TYPE)
    count = 0
    for field in ('inputs', 'outputs'):
        filename = _SIM_DATA.lib_file_name('files', field, data.files[field])
        header = _read_csv_header_columns(lib_dir.join(filename))
        count += len(header)
        data.files['{}Count'.format(field)] = len(header)
    data.files.columnCount = count
    return data.files


def _extract_column(run_dir, sim_in, idx):
    source = 'inputs'
    if idx >= sim_in.models.files.inputsCount:
        source = 'outputs'
        idx -= sim_in.models.files.inputsCount
    header, v = _read_file(run_dir, _SIM_DATA.rcscon_filename(sim_in, 'files', source))
    y = v[:, idx]
    x = np.arange(0, len(y))
    return x, y, header[idx], source


def _epoch_animation(frame_args):
    header, v = _read_file(frame_args.run_dir, _OUTPUT_FILE.fitOutputFile)
    return _plot_info(
        v[:, 0],
        map(lambda i: PKDict(
            points=v[:, i].tolist(),
            label=header[i],
        ), (1, 2)),
    ).update(PKDict(
        x_label=header[0],
    ))


def _fit_animation(frame_args):
    idx = int(frame_args.columnNumber)
    header, v = _read_file(frame_args.run_dir, _OUTPUT_FILE.predictOutputFile)
    _, y = _read_file(frame_args.run_dir, _OUTPUT_FILE.testOutputFile)
    return _plot_info(
        y[:, idx],
        [
            PKDict(
                points=v[:, idx].tolist(),
                label=header[idx],
                style='scatter',
            ),
        ],
    ).update(PKDict(
        aspectRatio=1,
    ))


def _generate_parameters_file(data):
    report = data.get('report', '')
    res, v = template_common.generate_parameters_file(data)
    v.update(PKDict(
        inputsFileName=_SIM_DATA.rcscon_filename(data, 'files', 'inputs'),
        outputsFileName=_SIM_DATA.rcscon_filename(data, 'files', 'outputs'),
        layerImplementationNames=_layer_implementation_list(data),
        neuralNetLayers=data.models.neuralNet.layers,
        inputDim=data.models.files.inputsCount,
    ).update(_OUTPUT_FILE))
    res += template_common.render_jinja(SIM_TYPE, v, 'build-model.py')
    if 'mlModelGraph' in report:
        res += template_common.render_jinja(SIM_TYPE, v, 'graph.py')
        return res
    res += template_common.render_jinja(SIM_TYPE, v, 'scale.py')
    if 'fileColumnReport' in report:
        return res
    res += template_common.render_jinja(SIM_TYPE, v, 'partition.py') \
        + template_common.render_jinja(SIM_TYPE, v, 'train.py')
    return res


def _layer_implementation_list(data):
    res = {}
    for layer in data.models.neuralNet.layers:
        res[layer.layer] = 1
    return res.keys()


def _plot_info(x, plots):
    return PKDict(
        title='',
        x_range=[min(x), max(x)],
        y_label='',
        x_label='',
        x_points=x.tolist(),
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
    )


def _read_csv_header_columns(path):
    with open(str(path)) as f:
        for row in csv.reader(f):
            return row
    return None


def _read_file(run_dir, filename):
    path = str(run_dir.join(filename))
    v = np.genfromtxt(path, delimiter=',', skip_header=1)
    if len(v.shape) == 1:
        v.shape = (v.shape[0], 1)
    return _read_csv_header_columns(path), v



def _read_last_line(path):
    # for performance, don't read whole file if only last line is needed
    try:
        with open(str(path), 'rb') as f:
            f.readline()
            f.seek(-2, os.SEEK_END)
            while f.read(1) != b'\n':
                f.seek(-2, os.SEEK_CUR)
            return f.readline()
    except IOError:
        return ''
