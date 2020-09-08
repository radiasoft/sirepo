# -*- coding: utf-8 -*-
u"""RCSCON execution template.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import numpy
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
    if report == 'partitionAnimation':
        if not is_running and run_dir.join('x-train.csv').exists():
            res.percentComplete = 100
            res.frameCount = 1;
        return res
    if report == 'elegantAnimation':
        if not is_running and run_dir.join('inputs.csv').exists():
            _compute_elegant_result_columns(run_dir, res)
        return res
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
        template_common.write_sequential_result(
            PKDict(svg=svg),
            run_dir=run_dir,
        )
        return
    if sim_in.report == 'partitionSelectionReport':
        template_common.write_sequential_result(
            _extract_partition_selection(run_dir, sim_in),
            run_dir=run_dir,
        )
        return
    assert 'fileColumnReport' in sim_in.report
    idx = sim_in.models[sim_in.report].columnNumber
    x, y, col_name, source_name = _extract_column(run_dir, sim_in, idx)
    template_common.write_sequential_result(
        _plot_info(
            x,
            [
                PKDict(
                    points=y.tolist(),
                    label='',
                ),
            ],
            col_name,
        ),
        run_dir=run_dir,
    )


def get_application_data(data, **kwargs):
    if data.method == 'compute_column_count':
        return _compute_file_column_count(data.files)
    assert False, 'unknown get_application_data: {}'.format(data)


def get_data_file(run_dir, model, frame, options=None, **kwargs):
    sim_in = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    f = sim_in.models.files
    if 'fileColumnReport' in model:
        source = _input_or_output(
            sim_in,
            int(re.search(r'(\d+)$', model).group(1)),
            'inputs',
            'outputs',
        )[0]
        return _SIM_DATA.lib_file_name_with_model_field(
            'files',
            source,
            sim_in.models.files[source],
        )
    if model == 'partitionSelectionReport' or 'partitionAnimation' in model:
        return _SIM_DATA.lib_file_name_with_model_field(
            'files',
            'inputs',
            sim_in.models.files.inputs,
        )
    if model == 'epochAnimation':
        return _OUTPUT_FILE.fitOutputFile
    if 'fitAnimation' in model:
        return PKDict(
            content=run_dir.join(_OUTPUT_FILE.testOutputFile).read_text() \
                + run_dir.join(_OUTPUT_FILE.predictOutputFile).read_text(),
            uri='test-and-predict.csv',
        )
    raise AssertionError('unknown model: {}'.format(model))


def prepare_sequential_output_file(run_dir, sim_in):
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
    if 'partitionAnimation' in frame_args.frameReport:
        return _partition_animation(frame_args)
    return _fit_animation(frame_args)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _compute_column_count(file_dir, input_filename, output_filename, res):
    count = 0
    for info in (['inputs', input_filename], ['outputs', output_filename]):
        header = _read_csv_header_columns(file_dir.join(info[1]))
        count += len(header)
        res['{}Count'.format(info[0])] = len(header)
    res.columnCount = count
    return res


def _compute_elegant_result_columns(run_dir, res):
    return _compute_column_count(run_dir, 'inputs.csv', 'outputs.csv', res)


def _compute_file_column_count(files):
    return _compute_column_count(
        simulation_db.simulation_lib_dir(SIM_TYPE),
        _SIM_DATA.lib_file_name_with_model_field('files', 'inputs', files.inputs),
        _SIM_DATA.lib_file_name_with_model_field('files', 'outputs', files.outputs),
        files,
    )


def _epoch_animation(frame_args):
    header, v = _read_file(frame_args.run_dir, _OUTPUT_FILE.fitOutputFile)
    return _plot_info(
        v[:, 0],
        [PKDict(
            points=v[:, i].tolist(),
            label=header[i],
        ) for i in (1, 2)],
    ).pkupdate(x_label=header[0])


def _extract_column(run_dir, sim_in, idx):
    source, idx = _input_or_output(sim_in, idx, 'inputs', 'outputs')
    header, v = _read_file(run_dir, _SIM_DATA.rcscon_filename(sim_in, 'files', source))
    y = v[:, idx]
    x = numpy.arange(0, len(y))
    return x, y, header[idx], source


def _extract_partition_selection(run_dir, sim_in):
    # return report with input0 and output0
    x, in0, in_col, _ = _extract_column(run_dir, sim_in, 0)
    _, out0, out_col, _ = _extract_column(run_dir, sim_in, sim_in.models.files.inputsCount)
    return _plot_info(
        x,
        [
            PKDict(
                points=in0.tolist(),
                label=in_col,
            ),
            PKDict(
                points=out0.tolist(),
                label=out_col,
            ),
        ],
    )


def _fit_animation(frame_args):
    idx = int(frame_args.columnNumber)
    header, v = _read_file(frame_args.run_dir, _OUTPUT_FILE.predictOutputFile)
    _, y = _read_file(frame_args.run_dir, _OUTPUT_FILE.testOutputFile)
    frame_args.histogramBins = 30
    return template_common.heatmap(
        [v[:, idx], y[:, idx]],
        frame_args,
        PKDict(
            x_label='',
            y_label='',
            title=header[idx],
            hideColorBar=True,
        ),
    )


def _generate_elegant_simulation(data):
    vars_by_name = PKDict({x.name : x.value for x in data.models.rpnVariables})
    for m in ('elegantAnimation', 'latticeSettings', 'rfcSettings'):
        for f in data.models[m]:
            vars_by_name[f] = data.models[m][f]
    data.models.rpnVariables = [PKDict(name=n, value=v) for n,v in vars_by_name.items()]
    data.models.simulation.update(
        backtracking='0',
        simulationMode='serial',
    )
    from sirepo.template import elegant
    return elegant.rcscon_generate_lattice(data)


def _generate_parameters_file(data):
    report = data.get('report', '')
    if report == 'elegantAnimation':
        return _generate_elegant_simulation(data)
    res, v = template_common.generate_parameters_file(data)
    res += 'from __future__ import absolute_import, division, print_function\n'
    infile = _SIM_DATA.rcscon_filename(data, 'files', 'inputs')
    outfile = _SIM_DATA.rcscon_filename(data, 'files', 'outputs')
    v.pkupdate(
        inputsFileName=infile,
        outputsFileName=outfile,
        layerImplementationNames=_layer_implementation_list(data),
        neuralNetLayers=data.models.neuralNet.layers,
        inputDim=data.models.files.inputsCount,
    ).pkupdate(_OUTPUT_FILE)
    if 'mlModelGraph' in report:
        res += template_common.render_jinja(SIM_TYPE, v, 'build-model.py')
        res += template_common.render_jinja(SIM_TYPE, v, 'graph.py')
        return res
    res += template_common.render_jinja(SIM_TYPE, v, 'scale.py')
    if 'fileColumnReport' in report or report == 'partitionSelectionReport':
        return res
    v.hasTrainingAndTesting = v.partition_section0 == 'train_and_test' \
        or v.partition_section1 == 'train_and_test' \
        or v.partition_section2 == 'train_and_test'
    res += template_common.render_jinja(SIM_TYPE, v, 'partition.py')
    if 'partitionAnimation' in report:
        res += template_common.render_jinja(SIM_TYPE, v, 'save-partition.py')
        return res
    res += template_common.render_jinja(SIM_TYPE, v, 'build-model.py')
    res += template_common.render_jinja(SIM_TYPE, v, 'train.py')
    return res


def _input_or_output(sim_in, idx, input_field, output_field):
    res = input_field
    if idx >= sim_in.models.files.inputsCount:
        res = output_field
        idx -= sim_in.models.files.inputsCount
    return res, idx


def _layer_implementation_list(data):
    res = {}
    for layer in data.models.neuralNet.layers:
        res[layer.layer] = 1
    return res.keys()


def _histogram_plot(values, vrange):
    hist = numpy.histogram(values, bins=20, range=vrange)
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


def _update_range(vrange, values):
    minv = min(values)
    maxv = max(values)
    if not vrange:
        vrange.append(minv)
        vrange.append(maxv)
        return
    if vrange[0] > minv:
        vrange[0] = minv
    if vrange[1] < maxv:
        vrange[1] = maxv


def _partition_animation(frame_args):
    sim_in = frame_args.sim_in
    idx = int(frame_args.columnNumber)
    source, idx = _input_or_output(sim_in, idx, 'x', 'y')
    header, train = _read_file(frame_args.run_dir, '{}-train.csv'.format(source))
    _, test = _read_file(frame_args.run_dir, '{}-test.csv'.format(source))
    _, validate = _read_file(frame_args.run_dir, '{}-validate.csv'.format(source))
    d = PKDict(
        train=train[:, idx],
        test=test[:, idx],
        validate=validate[:, idx],
    )
    plots = []
    r = []
    for name in ('train', 'test', 'validate'):
        _update_range(r, d[name])
    for name in ('train', 'test', 'validate'):
        x, y = _histogram_plot(d[name], r)
        plots.append(
            PKDict(
                points=y,
                label=name,
            ),
        )
    return _plot_info(numpy.array(x), plots, title=header[idx])


def _plot_info(x, plots, title=''):
    return PKDict(
        title=title,
        x_range=[float(min(x)), float(max(x))],
        y_label='',
        x_label='',
        x_points=x.tolist(),
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
    )


def _read_csv_header_columns(path):
    import csv

    with open(str(path)) as f:
        for row in csv.reader(f):
            return row
    return None


def _read_file(run_dir, filename):
    path = str(run_dir.join(filename))
    v = numpy.genfromtxt(path, delimiter=',', skip_header=1)
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
            return pkcompat.from_bytes(f.readline())
    except IOError:
        return ''
