# -*- coding: utf-8 -*-
u"""ML execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import csv
import numpy as np
import re
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

_CLASSIFIER_OUTPUT_FILE = PKDict(
    dtClassifierClassificationFile='dt-classifier-classification.json',
    dtClassifierConfusionFile='dt-classifier-confusion.json',
    knnClassificationFile='classification.json',
    knnConfusionFile='confusion.json',
    knnErrorFile='error.npy',
    linearSvcConfusionFile='linear-svc-confusion.json',
    linearSvcErrorFile='linear-svc-error.npy',
    logisticRegressionClassificationFile='logistic-regression-classification.json',
    logisticRegressionConfusionFile='logistic-regression-confusion.json',
    logisticRegressionErrorFile='logistic-regression-error.npy',
)

_OUTPUT_FILE = PKDict(
    classificationOutputColEncodingFile='classification-output-col-encoding.json',
    fitCSVFile='fit.csv',
    predictFile='predict.npy',
    scaledFile='scaled.npy',
    testFile='test.npy',
    trainFile='train.npy',
    validateFile='validate.npy',
    **_CLASSIFIER_OUTPUT_FILE
)

def background_percent_complete(report, run_dir, is_running):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    if report == 'classificationAnimation' and not is_running:
        s = list(filter(
            lambda path: path.basename in _CLASSIFIER_OUTPUT_FILE.values(),
            pkio.sorted_glob(run_dir.join('*')),
        ))
        return PKDict(
            framesForClassifier=data.models.classificationAnimation.classifier,
            frameCount=1 if s else 0,
            percentComplete=100,
        )
    line = template_common.read_last_csv_line(run_dir.join(_OUTPUT_FILE.fitCSVFile))
    m = re.search(r'^(\d+)', line)
    if m and int(m.group(1)) > 0:
        max_frame = data.models.neuralNet.epochs
        res.frameCount = int(m.group(1)) + 1
        res.percentComplete = float(res.frameCount) * 100 / max_frame
    return res


def get_application_data(data, **kwargs):
    if data.method == 'compute_column_info':
        return _compute_column_info(data.dataFile)
    raise AssertionError(f'unknown get_application_data: {data}')


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


def sim_frame(frame_args):
    return _fit_animation(frame_args)


def sim_frame_dtClassifierClassificationMetricsAnimation(frame_args):
    return _classification_metrics_report(
        frame_args,
        _OUTPUT_FILE.dtClassifierClassificationFile,
    )


def sim_frame_dtClassifierConfusionMatrixAnimation(frame_args):
    return _confusion_matrix_to_heatmap_report(
        frame_args,
        _OUTPUT_FILE.dtClassifierConfusionFile,
        'Decision Tree Confusion Matrix',
    )


def sim_frame_epochAnimation(frame_args):
    #TODO(pjm): improve heading text
    header = ['epoch', 'loss', 'val_loss']
    path = str(frame_args.run_dir.join(_OUTPUT_FILE.fitCSVFile))
    v = np.genfromtxt(path, delimiter=',', skip_header=1)
    if len(v.shape) == 1:
        v.shape = (v.shape[0], 1)
    return _report_info(
        v[:, 0],
        [PKDict(
            points=v[:, i].tolist(),
            label=header[i],
        ) for i in (1, 2)],
    ).pkupdate(PKDict(
        x_label=header[0],
    ))

def sim_frame_knnClassificationMetricsAnimation(frame_args):
    return _classification_metrics_report(
        frame_args,
        _OUTPUT_FILE.knnClassificationFile,
    )


def sim_frame_knnConfusionMatrixAnimation(frame_args):
    return _confusion_matrix_to_heatmap_report(
        frame_args,
        _OUTPUT_FILE.knnConfusionFile,
        'K={k}',
    )

def sim_frame_knnErrorRateAnimation(frame_args):
    return _error_rate_report(
        frame_args,
        _OUTPUT_FILE.knnErrorFile,
        'K Value',
    )


def sim_frame_linearSvcConfusionMatrixAnimation(frame_args):
    return _confusion_matrix_to_heatmap_report(
        frame_args,
        _OUTPUT_FILE.linearSvcConfusionFile,
        'tolerance={tol_svc_best}',
    )


def sim_frame_linearSvcErrorRateAnimation(frame_args):
    v = np.load(str(frame_args.run_dir.join(_OUTPUT_FILE.linearSvcErrorFile)))
    return _report_info(
        v[:, 0],
        [PKDict(
            points=v[:, 1].tolist(),
            label='Mean Error',
        )],
    ).pkupdate(PKDict(
        x_label='Tolerance',
    ))


def sim_frame_logisticRegressionConfusionMatrixAnimation(frame_args):
    return _confusion_matrix_to_heatmap_report(
        frame_args,
        _OUTPUT_FILE.logisticRegressionConfusionFile,
        'C={c}',
    )


def sim_frame_logisticRegressionClassificationMetricsAnimation(frame_args):
    return _classification_metrics_report(
        frame_args,
        _OUTPUT_FILE.logisticRegressionClassificationFile,
    )


def sim_frame_logisticRegressionErrorRateAnimation(frame_args):
    return _error_rate_report(
        frame_args,
        _OUTPUT_FILE.logisticRegressionErrorFile,
        'C',
    )


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _classification_metrics_report(frame_args, filename):
    def _get_lables():
        l = []
        for k in d:
            if not isinstance(d[k], PKDict):
                continue
            for x in d[k]:
                if x not in l:
                    l.append(x)
        return l

    def _get_matrix():
        r = []
        for k in d:
            if not isinstance(d[k], PKDict):
                continue
            try:
                x = [e[k]]
            except KeyError:
                x = [k]
            x.extend(d[k].values())
            r.append(x)
        return r

    e = _get_classification_output_col_encoding(frame_args)
    d = pkjson.load_any(frame_args.run_dir.join(filename))
    return PKDict(
        labels=_get_lables(),
        matrix=_get_matrix(),
    )


def _compute_column_info(dataFile):
    f = dataFile.file
    if re.search(r'\.npy$', f):
        return _compute_numpy_info(f)
    return _compute_csv_info(f)


def _compute_csv_info(filename):
    res = PKDict(
        hasHeaderRow=True,
        rowCount=0,
    )
    row = None
    with open(_filepath(filename)) as f:
        for r in csv.reader(f):
            if not row:
                row = r
            res.rowCount += 1
    if not row or len(row) == 1:
        return PKDict(
            error='Invalid CSV file: no columns detected'
        )
    # csv file may or may not have column names
    # if any value in the first row is numeric, assume no headers
    if list(filter(lambda x: template_common.NUMERIC_RE.search(x), row)):
        row = ['column {}'.format(i + 1) for i in range(len(row))]
        res.hasHeaderRow = False
    res.colsWithNonUniqueValues = _cols_with_non_unique_values(
        filename,
        res.hasHeaderRow,
        row,
    )
    res.header = row
    res.inputOutput = ['none' for i in range(len(row))]
    return res


def _cols_with_non_unique_values(filename, has_header_row, header):
    # TODO(e-carlin): support npy
    assert not re.search(r'\.npy$', str(filename)), \
        f'numpy files are not supported path={filename}'
    v = np.genfromtxt(
        str(_filepath(filename)),
        delimiter=',',
        skip_header=True,
    )
    res = PKDict()
    for i, c in enumerate(np.all(v == v[0,:], axis = 0)):
        if not c:
            continue
        res[header[i]] = True
    return res


def _compute_numpy_info(filename):
    #TODO(pjm): compute column info from numpy file
    raise NotImplementedError()


def _confusion_matrix_to_heatmap_report(frame_args, filename, title):
    r = pkjson.load_any(frame_args.run_dir.join(filename))
    a = None
    for y, _ in enumerate(r.matrix):
        for x, v in enumerate(r.matrix[y]):
            t = np.repeat([[x, y]], v, axis=0)
            a = t if a is None else np.vstack([t, a])
    labels = _get_classification_output_col_encoding(frame_args)
    if labels:
        labels = list(labels.values())
    else:
        labels = r.labels
    return template_common.heatmap(
        a,
        PKDict(histogramBins=len(r.matrix)),
        plot_fields=PKDict(
            labels=labels,
            title=title.format(**r),
            x_label='Predicted',
            y_label='True',
        ),
    )


def _error_rate_report(frame_args, filename, x_label):
    v = np.load(str(frame_args.run_dir.join(filename)))
    return _report_info(
        v[:, 0],
        [PKDict(
            points=v[:, 1].tolist(),
            label='Mean Error',
        )],
    ).pkupdate(PKDict(
        x_label=x_label,
    ))


def _extract_column(run_dir, sim_in, idx):
    y = _read_file_column(run_dir, 'scaledFile', idx)
    return np.arange(0, len(y)), y


def _extract_file_column_report(run_dir, sim_in):
    m = sim_in.models[sim_in.report]
    idx = m.columnNumber
    x, y = _extract_column(run_dir, sim_in, idx)
    if np.isnan(y).any():
        template_common.write_sequential_result(PKDict(
            error='Column values are not numeric',
        ))
        return
    if 'x' in m and m.x is not None and m.x >= 0:
        _, x = _extract_column(run_dir, sim_in, m.x)
    _write_report(
        x,
        [_plot_info(y, style='scatter')],
        sim_in.models.columnInfo.header[idx],
    )


def _extract_partition_report(run_dir, sim_in):
    idx = sim_in.models[sim_in.report].columnNumber
    d = PKDict(
        train=_read_file_column(run_dir, 'trainFile', idx),
        test=_read_file_column(run_dir, 'testFile', idx),
    )
    if sim_in.models.dataFile.appMode == 'regression':
        d.validate = _read_file_column(run_dir, 'validateFile', idx)
    r = []
    for name in d:
        _update_range(r, d[name])
    plots = []
    for name in d:
        x, y = _histogram_plot(d[name], r)
        plots.append(_plot_info(y, name))
    _write_report(
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
    _write_report(
        x,
        [
            _plot_info(y, info.header[in_idx]),
            _plot_info(y2, info.header[out_idx]),
        ],
    )


def _filename(name):
    return _SIM_DATA.lib_file_name_with_model_field('dataFile', 'file', name)


def _filepath(name):
    return _SIM_DATA.lib_file_abspath(_filename(name))


def _fit_animation(frame_args):
    idx = int(frame_args.columnNumber)
    frame_args.histogramBins = 30
    info = frame_args.sim_in.models.columnInfo
    header = []
    for i in range(len(info.inputOutput)):
        if info.inputOutput[i] == 'output':
            header.append(info.header[i])
    return template_common.heatmap(
        [
            _read_file(frame_args.run_dir, _OUTPUT_FILE.predictFile)[:, idx],
            _read_file(frame_args.run_dir, _OUTPUT_FILE.testFile)[:, idx],
        ],
        frame_args,
        PKDict(
            x_label='',
            y_label='',
            title=header[idx],
            hideColorBar=True,
        ),
    )


def _generate_parameters_file(data):
    report = data.get('report', '')
    dm = data.models
    res, v = template_common.generate_parameters_file(data)
    v.dataFile = _filename(dm.dataFile.file)
    v.pkupdate(
        layerImplementationNames=_layer_implementation_list(data),
        neuralNetLayers=dm.neuralNet.layers,
        inputDim=dm.columnInfo.inputOutput.count('input'),
    ).pkupdate(_OUTPUT_FILE)
    v.columnTypes = '[' + ','.join([ "'" + v + "'" for v in dm.columnInfo.inputOutput]) + ']'
    res += template_common.render_jinja(SIM_TYPE, v, 'scale.py')
    if 'fileColumnReport' in report or report == 'partitionSelectionReport':
        return res
    v.hasTrainingAndTesting = v.partition_section0 == 'train_and_test' \
        or v.partition_section1 == 'train_and_test' \
        or v.partition_section2 == 'train_and_test'
    res += template_common.render_jinja(SIM_TYPE, v, 'partition.py')
    if 'partitionColumnReport' in report:
        res += template_common.render_jinja(SIM_TYPE, v, 'save-partition.py')
        return res
    if dm.dataFile.appMode == 'classification':
        res += template_common.render_jinja(SIM_TYPE, v, 'classification-base.py')
        d = PKDict(
            decisionTree='decision-tree',
            knn='knn',
            linearSvc='linear-svc',
            logisticRegression='logistic-regression',
        )
        return res + template_common.render_jinja(
            SIM_TYPE,
            v,
            f'{d[dm.classificationAnimation.classifier]}.py',
        )
    res += template_common.render_jinja(SIM_TYPE, v, 'build-model.py')
    res += template_common.render_jinja(SIM_TYPE, v, 'train.py')
    return res


def _get_classification_output_col_encoding(frame_args):
    try:
        return simulation_db.read_json(
            frame_args.run_dir.join(_OUTPUT_FILE.classificationOutputColEncodingFile),
        )
    except Exception as e:
        if pkio.exception_is_not_found(e):
            # no file exists, data may be only numeric values
            return PKDict()
        raise e


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


def _layer_implementation_list(data):
    res = {}
    for layer in data.models.neuralNet.layers:
        res[layer.layer] = 1
    return res.keys()


def _plot_info(y, label='', style=None):
    return PKDict(points=list(y), label=label, style=style)


def _read_file(run_dir, filename):
    res = np.load(str(run_dir.join(filename)))
    if len(res.shape) == 1:
        res.shape = (res.shape[0], 1)
    return res


def _read_file_column(run_dir, name, idx):
    return _read_file(run_dir, _OUTPUT_FILE[name])[:, idx]


def _report_info(x, plots, title=''):
    return PKDict(
        title=title,
        x_range=[float(min(x)), float(max(x))],
        y_label='',
        x_label='',
        x_points=list(x),
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
    )


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


def _write_report(x, plots, title=''):
    template_common.write_sequential_result(_report_info(x, plots, title))
