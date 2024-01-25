# -*- coding: utf-8 -*-
"""Activait execution template.

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
from base64 import b64encode
import csv
import h5py
import numpy
import os
import re
import pandas
import sirepo.analysis
import sirepo.numpy
import sirepo.sim_data
import sirepo.util

_LOG_FILE = "run.log"

_SEGMENT_ROWS = 3

_SEGMENT_PAGES = 5

_IMG_ROWS = 5

_IMG_COLS = 5

_POST_TRAINING_PLOTS = ("segmentViewer", "bestLosses", "worstLosses")

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_SIM_REPORTS = [
    "analysisReport",
    "fftReport",
]

_CLASSIFIER_OUTPUT_FILE = PKDict(
    dtClassifierClassificationFile="dt-classifier-classification.json",
    dtClassifierConfusionFile="dt-classifier-confusion.json",
    knnClassificationFile="classification.json",
    knnConfusionFile="confusion.json",
    knnErrorFile="error.npy",
    linearSvcConfusionFile="linear-svc-confusion.json",
    linearSvcErrorFile="linear-svc-error.npy",
    logisticRegressionClassificationFile="logistic-regression-classification.json",
    logisticRegressionConfusionFile="logistic-regression-confusion.json",
    logisticRegressionErrorFile="logistic-regression-error.npy",
)

_OUTPUT_FILE = PKDict(
    classificationOutputColEncodingFile="classification-output-col-encoding.json",
    bestFile="bestFile.npy",
    originalImageInFile="originalImageInFile.npy",
    worstFile="worstFile.npy",
    fitCSVFile="fit.csv",
    predictFile="predict.npy",
    scaledFile="scaled.npy",
    mlModel="weighted.h5",
    neuralNetLayer="unweighted.h5",
    testFile="test.npy",
    trainFile="train.npy",
    validateFile="validate.npy",
    **_CLASSIFIER_OUTPUT_FILE,
)

_REPORTS = [
    "fileColumnReport",
    "partitionColumnReport",
    "partitionSelectionReport",
] + _SIM_REPORTS


def background_percent_complete(report, run_dir, is_running):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    if report == "classificationAnimation" and not is_running:
        s = list(
            filter(
                lambda path: path.basename in _CLASSIFIER_OUTPUT_FILE.values(),
                pkio.sorted_glob(run_dir.join("*")),
            )
        )
        return PKDict(
            framesForClassifier=data.models.classificationAnimation.classifier,
            frameCount=1 if s else 0,
            percentComplete=100,
        )
    line = template_common.read_last_csv_line(run_dir.join(_OUTPUT_FILE.fitCSVFile))
    m = re.search(r"^(\d+)", line)
    if m and int(m.group(1)) > 0:
        max_frame = data.models.neuralNet.epochs
        res.frameCount = int(m.group(1)) + 1
        res.percentComplete = float(res.frameCount) * 100 / max_frame
    error = _range_error(
        template_common.LogParser(
            run_dir,
            log_filename=_LOG_FILE,
            error_patterns=(r"AssertionError: (Model training failed due to .*)",),
            default_msg="",
        ).parse_for_errors()
    )
    if error:
        res.error = error
    return res


def _range_error(error):
    e = re.search(re.compile("Received a label value of (.*?) (is .*?[\]\)])"), error)
    if e:
        return f"Output scaling result {e.groups()[1]}"
    return error


def get_analysis_report(run_dir, data):
    report = data.models[data.report]
    info = data.models.columnInfo
    x_idx = int(report.x)
    y_idx = int(report.y1)
    x_label = f"{info.header[x_idx]}"
    y_label = f"{info.header[y_idx]}"

    plot_data = _read_file_with_history(run_dir, _OUTPUT_FILE.scaledFile, report)
    x = plot_data[:, x_idx]
    y = plot_data[:, y_idx]
    plots = [
        PKDict(
            points=y.tolist(),
            label=y_label,
            style="scatter",
        )
    ]
    fields = PKDict()
    summary_data = PKDict()
    if "action" in report:
        if report.action == "fit":
            p_vals, p_errs, fit_plots = _get_fit_report(report, x, y)
            summary_data.p_vals = p_vals.tolist()
            summary_data.p_errs = p_errs.tolist()
            plots.extend(fit_plots)
        elif report.action == "cluster":
            fields.clusters = _compute_clusters(report, plot_data)
    return x, plots, f"{x_label} vs {y_label}", fields, summary_data


def get_data_file(run_dir, model, frame, options):
    if _numbered_model_file(model):
        return model + ".csv"
    if model == "epochAnimation":
        return _OUTPUT_FILE.fitCSVFile
    if model == "animation":
        return _OUTPUT_FILE[options.suffix]
    raise AssertionError(f"model={model} is unknown")


# TODO(MVK): 2d fft (?)
def get_fft_report(run_dir, data):
    info = data.models.columnInfo
    col = data.models.fftReport.column
    idx = int(col)
    label = f"{info.header[idx]}"

    t, y = _extract_column(run_dir, idx)
    w, n = sirepo.analysis.get_fft(t, y)

    plots = [
        PKDict(
            points=n,
            label=f"{label}",
        ),
    ]

    summaryData = PKDict(freqs=[], minFreq=w[0], maxFreq=w[-1])

    return w, plots, f"FFT", summaryData


def new_simulation(data, new_sim_data, qcall, **kwargs):
    if "sourceSimType" not in new_sim_data:
        return
    t_basename = f"{new_sim_data.sourceSimType}-{new_sim_data.sourceSimId}-{new_sim_data.sourceSimFile}"
    data.models.dataFile.dataOrigin = "file"
    data.models.dataFile.file = t_basename
    t = simulation_db.simulation_lib_dir(_SIM_DATA.sim_type(), qcall=qcall).join(
        _SIM_DATA.lib_file_name_with_model_field("dataFile", "file", t_basename)
    )
    if t.exists():
        return
    s = simulation_db.simulation_dir(
        new_sim_data.sourceSimType, sid=new_sim_data.sourceSimId, qcall=qcall
    ).join(new_sim_data.sourceSimFile)
    t.mksymlinkto(s, absolute=False)


def prepare_sequential_output_file(run_dir, data):
    report = data["report"]
    if "fileColumnReport" in report or "partitionColumnReport":
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            try:
                save_sequential_report_data(run_dir, data)
            except IOError:
                # the output file isn't readable
                pass


def stateless_compute_load_keras_model(data, **kwargs):
    import keras.models

    l = _SIM_DATA.lib_file_abspath(
        _SIM_DATA.lib_file_name_with_model_field("mlModel", "modelFile", data.args.file)
    )
    return _build_ui_nn(keras.models.load_model(l))


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def save_sequential_report_data(run_dir, sim_in):
    if "fileColumnReport" in sim_in.report:
        _extract_file_column_report(run_dir, sim_in)
    elif "partitionColumnReport" in sim_in.report:
        _extract_partition_report(run_dir, sim_in)
    elif sim_in.report == "partitionSelectionReport":
        _extract_partition_selection(run_dir, sim_in)
    elif "analysisReport" in sim_in.report:
        _extract_analysis_report(run_dir, sim_in)
    elif "fftReport" in sim_in.report:
        _extract_fft_report(run_dir, sim_in)
    else:
        raise AssertionError("unknown report: {}".format(sim_in.report))


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
        "Decision Tree Confusion Matrix",
    )


def sim_frame_epochAnimation(frame_args):
    # TODO(pjm): improve heading text
    d = pandas.read_csv(str(frame_args.run_dir.join(_OUTPUT_FILE.fitCSVFile)))
    return _report_info(
        list(d.index),
        [
            PKDict(
                points=list(d[l]),
                label=l,
            )
            for l in ("loss", "val_loss")
        ],
    ).pkupdate(
        PKDict(
            x_label="epoch",
        )
    )


def sim_frame_knnClassificationMetricsAnimation(frame_args):
    return _classification_metrics_report(
        frame_args,
        _OUTPUT_FILE.knnClassificationFile,
    )


def sim_frame_knnConfusionMatrixAnimation(frame_args):
    return _confusion_matrix_to_heatmap_report(
        frame_args,
        _OUTPUT_FILE.knnConfusionFile,
        "K={k}",
    )


def sim_frame_knnErrorRateAnimation(frame_args):
    return _error_rate_report(
        frame_args,
        _OUTPUT_FILE.knnErrorFile,
        "K Value",
    )


def sim_frame_linearSvcConfusionMatrixAnimation(frame_args):
    return _confusion_matrix_to_heatmap_report(
        frame_args,
        _OUTPUT_FILE.linearSvcConfusionFile,
        "tolerance={tol_svc_best}",
    )


def sim_frame_linearSvcErrorRateAnimation(frame_args):
    v = numpy.load(str(frame_args.run_dir.join(_OUTPUT_FILE.linearSvcErrorFile)))
    return _report_info(
        v[:, 0],
        [
            PKDict(
                points=v[:, 1].tolist(),
                label="Mean Error",
            )
        ],
    ).pkupdate(
        PKDict(
            x_label="Tolerance",
        )
    )


def sim_frame_logisticRegressionConfusionMatrixAnimation(frame_args):
    return _confusion_matrix_to_heatmap_report(
        frame_args,
        _OUTPUT_FILE.logisticRegressionConfusionFile,
        "C={c}",
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
        "C",
    )


def stateful_compute_column_info(data, **kwargs):
    f = data.args.dataFile.file
    if pkio.has_file_extension(f, "csv"):
        return _compute_csv_info(f)
    elif pkio.has_file_extension(f, "h5"):
        return _compute_h5_info(f)
    raise AssertionError("Unsupported file type: {}".format(f))


def analysis_job_sample_images(data, run_dir, **kwargs):
    return _ImagePreview(data, run_dir).images()


def analysis_job_dice_coefficient(data, run_dir, **kwargs):
    return _ImagePreview(data, run_dir).dice_coefficient_plot()


def stateful_compute_sample_images(data, **kwargs):
    return _ImagePreview(data).images()


def stateless_compute_get_remote_data(data, **kwargs):
    return template_common.remote_file_to_simulation_lib(
        _SIM_DATA,
        data.args.url,
        data.args.headers_only,
        "dataFile",
        "file",
    )


def stateless_compute_remote_data_bytes_loaded(data, **kwargs):
    return _remote_data_bytes_loaded(data.args.filename)


def stateless_compute_get_archive_file_list(data, **kwargs):
    return _archive_file_list(data.args.filename, data.args.data_type)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _archive_file_list(filename, data_type):
    reader = sirepo.sim_data.activait.DataReaderFactory.build(_filepath(filename))

    def _filter(item):
        is_dir = reader.is_dir(item)
        return is_dir if data_type == "image" else not is_dir

    return PKDict(datalist=reader.get_data_list(_filter))


def _build_model_py(v):
    v.counter = 0

    def _new_name():
        v.counter += 1
        return "x_" + str(v.counter)

    def _branching(layer):
        return layer.layer == "Add" or layer.layer == "Concatenate"

    def _name_layer(layer_level, first_level, parent_level_name):
        if layer_level.layers == []:
            return parent_level_name
        if first_level:
            return "x"
        return _new_name()

    def _name_layers(layer_level, parent_level_name, first_level=False):
        layer_level.name = _name_layer(layer_level, first_level, parent_level_name)
        layer_level.parent_name = parent_level_name
        for i, l in enumerate(layer_level.layers):
            if _branching(l):
                for c in l.children:
                    l.parent_name = layer_level.name
                    _name_layers(c, parent_level_name if i == 0 else layer_level.name)

    def _import_layers(v):
        return "".join(", " + n for n in v.layerImplementationNames if n != "Dense")

    def _conv_args(layer):
        if layer.layer not in ("Conv2D", "Conv2DTranspose", "SeparableConv2D"):
            return
        return f"""{layer.dimensionality},
    activation="{layer.activation}",
    kernel_size=({layer.kernel}, {layer.kernel}),
    strides={layer.strides},
    padding="{layer.padding}"
    """

    def _pooling_args(layer):
        return f'''pool_size=({layer.size}, {layer.size}),
    strides={layer.strides},
    padding="{layer.padding}"'''

    def _dropout_args(layer):
        if layer.get("rate"):
            return layer.rate
        else:
            return layer.dropoutRate

    def _activation(layer):
        return f'"{layer.get("activation", "relu")}"'

    args_map = PKDict(
        Activation=lambda layer: _activation(layer),
        Add=lambda layer: _branch(layer, "Add"),
        AlphaDropout=lambda layer: _dropout_args(layer),
        AveragePooling2D=lambda layer: _pooling_args(layer),
        BatchNormalization=lambda layer: f"momentum={layer.momentum}",
        Concatenate=lambda layer: _branch(layer, "Concatenate"),
        Conv2D=lambda layer: _conv_args(layer),
        Dense=lambda layer: f'{layer.dimensionality}, activation="{layer.activation}"',
        Dropout=lambda layer: _dropout_args(layer),
        Flatten=lambda layer: "",
        GaussianDropout=lambda layer: _dropout_args(layer),
        GaussianNoise=lambda layer: layer.stddev,
        GlobalAveragePooling2D=lambda layer: "",
        MaxPooling2D=lambda layer: _pooling_args(layer),
        SeparableConv2D=lambda layer: _conv_args(layer),
        Conv2DTranspose=lambda layer: _conv_args(layer),
        Reshape=lambda layer: f"{layer.new_shape}",
        UpSampling2D=lambda layer: f'size={layer.size}, interpolation="{layer.interpolation}"',
        ZeroPadding2D=lambda layer: f"padding=({layer.padding}, {layer.padding})",
    )

    def _final_layer(v):
        if v.get("paramToImage", False):
            return ""
        return '\nx = Dense(output_shape, activation="linear")(x)'

    def _layer(layer):
        assert layer.layer in args_map, ValueError(f"invalid layer.layer={layer.layer}")
        return args_map[layer.layer](layer)

    def _branch_or_continue(layers, layer, layer_args):
        if layer.layer == "Add" or layer.layer == "Concatenate":
            return _layer(layer)
        return f"{layers.name} = {layer.layer}{layer_args}\n"

    def _build_layers(branch):
        res = ""
        for i, l in enumerate(branch.layers):
            if i == 0:
                c = f"({_layer(l)})({branch.parent_name})"
            else:
                c = f"({_layer(l)})({branch.name})"
            res += _branch_or_continue(branch, l, c)
        return res

    def _branch(layer, join_type):
        def _join(layer):
            c = ", ".join([l.name for l in layer.children])
            return f"{layer.parent_name} = {join_type}()([{c}])\n"

        res = ""
        for c in layer.children:
            res += _build_layers(c)
        res += _join(layer)
        return res

    net = PKDict(layers=v.neuralNetLayers)
    _name_layers(net, "input_args", first_level=True)

    return (
        f"""
from keras.models import Model, Sequential
from keras.layers import Input, Dense{_import_layers(v)}
input_args = Input(shape=input_shape)
{_build_layers(net)}"""
        + _final_layer(v)
        + f"""\nmodel = Model(input_args, x)
model.save('{_OUTPUT_FILE.neuralNetLayer}')
"""
    )


def _build_ui_nn(model):
    return _set_children(_set_outbound(_set_inbound(model, _make_layers(model))))


def _children(cur_node, neural_net):
    c = []
    t = 0
    for i in cur_node.inbound:
        child_node = _get_layer_by_name(neural_net, i.name)
        p, s, l = _levels_with_children(child_node, neural_net)
        t += s
        c.append(l)
    return PKDict(
        parent_sum=t,
        children=c,
        parent_node=p,
    )


def _classification_metrics_report(frame_args, filename):
    def _get_labels():
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
        labels=_get_labels(),
        matrix=_get_matrix(),
    )


def _clean_layer(l):
    for k in ("obj", "inbound", "outbound", "name"):
        if l.get(k):
            l.pop(k)
    return l


def _close_completed_branch(level, cur_node, neural_net):
    if not _is_merge_node(cur_node):
        level.insert(0, cur_node)
        return PKDict(
            cur_node=_get_next_node(cur_node, neural_net),
            merge_continue=False,
        )
    return PKDict(
        cur_node=cur_node,
        merge_continue=True,
    )


def _cols_with_non_unique_values(filename, has_header_row, header):
    v = sirepo.numpy.ndarray_from_csv(_filepath(filename), has_header_row)
    res = PKDict()
    for i, c in enumerate(numpy.all(v == v[0, :], axis=0)):
        if c:
            res[header[i]] = True
    return res


def _compute_h5_info(filename):
    res = PKDict(
        colsWithNonUniqueValues=PKDict(),
        header=[],
        shape=[],
        inputOutput=[],
        outputShape=[],
        dtypeKind=[],
    )

    def _visit(name, node):
        if isinstance(node, h5py.Dataset):
            res.header.append(name)
            res.shape.append([*node.shape])
            res.inputOutput.append("none")
            res.dtypeKind.append(node.dtype.kind)
            n = 0
            if len(node.shape) == 1:
                if node.dtype.kind == "f":
                    n = 1
                else:
                    n = len(numpy.unique(node))
            elif len(node.shape) == 2:
                n = node.shape[1]
            res.outputShape.append(n)

    with h5py.File(_filepath(filename), "r") as f:
        f.visititems(_visit)
    return res


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
        return PKDict(error="Invalid CSV file: no columns detected")
    # csv file may or may not have column names
    # if any value in the first row is numeric, assume no headers
    if list(filter(lambda x: template_common.NUMERIC_RE.search(x), row)):
        row = ["column {}".format(i + 1) for i in range(len(row))]
        res.hasHeaderRow = False
    res.colsWithNonUniqueValues = _cols_with_non_unique_values(
        filename,
        res.hasHeaderRow,
        row,
    )
    res.header = row
    res.inputOutput = ["none" for i in range(len(row))]
    return res


def _compute_clusters(report, plot_data):
    from sirepo.analysis import ml

    method_params = PKDict(
        agglomerative=PKDict(
            count=report.clusterCount,
        ),
        dbscan=PKDict(
            eps=report.clusterDbscanEps,
        ),
        gmix=PKDict(
            count=report.clusterCount,
            seed=report.clusterRandomSeed,
        ),
        kmeans=PKDict(
            count=report.clusterCount,
            seed=report.clusterRandomSeed,
            kmeans_init=report.clusterKmeansInit,
        ),
    )

    cols = []
    if "clusterFields" not in report:
        if len(cols) <= 1:
            raise sirepo.util.UserAlert(
                "At least two cluster fields must be selected", "only one cols"
            )
    for idx in range(len(report.clusterFields)):
        if report.clusterFields[idx]:
            cols.append(idx)
    if len(cols) <= 1:
        raise sirepo.util.UserAlert(
            "At least two cluster fields must be selected", "only one cols"
        )
    x_scale = sirepo.analysis.ml.scale_data(
        plot_data[:, cols],
        [
            report.clusterScaleMin,
            report.clusterScaleMax,
        ],
    )
    group = sirepo.analysis.ml.METHODS[report.clusterMethod](
        x_scale, method_params[report.clusterMethod]
    )
    count = len(set(group)) if report.clusterMethod == "dbscan" else report.clusterCount
    return PKDict(
        group=group.tolist(),
        count=count,
    )


def _confusion_matrix_to_heatmap_report(frame_args, filename, title):
    r = pkjson.load_any(frame_args.run_dir.join(filename))
    a = None
    for y, _ in enumerate(r.matrix):
        for x, v in enumerate(r.matrix[y]):
            t = numpy.repeat([[x, y]], v, axis=0)
            a = t if a is None else numpy.vstack([t, a])
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
            x_label="Predicted",
            y_label="True",
        ),
    )


def _continue_building_level(cur_node, merge_continue):
    if "input" in cur_node.name or _is_branching(cur_node):
        return False or merge_continue
    return True


def _error_rate_report(frame_args, filename, x_label):
    v = numpy.load(str(frame_args.run_dir.join(filename)))
    return _report_info(
        v[:, 0],
        [
            PKDict(
                points=v[:, 1].tolist(),
                label="Mean Error",
            )
        ],
    ).pkupdate(
        PKDict(
            x_label=x_label,
        )
    )


def _extract_analysis_report(run_dir, sim_in):
    x, plots, title, fields, summary_data = get_analysis_report(run_dir, sim_in)
    _write_report(x, plots, title, fields=fields, summary_data=summary_data)


def _extract_column(run_dir, idx):
    y = _read_file_column(run_dir, "scaledFile", idx)
    return numpy.arange(0, len(y)), y


def _extract_file_column_report(run_dir, sim_in):
    m = sim_in.models[sim_in.report]
    idx = m.columnNumber
    x, y = _extract_column(run_dir, idx)
    if numpy.isnan(y).any():
        template_common.write_sequential_result(
            PKDict(
                error="Column values are not numeric",
            )
        )
        return
    if "x" in m and m.x is not None and m.x >= 0:
        _, x = _extract_column(run_dir, m.x)
    _write_csv_for_download(
        PKDict(x=x, y=y),
        f"fileColumnReport{idx}.csv",
    )
    _write_report(
        x,
        [_plot_info(y, style="scatter")],
        sim_in.models.columnInfo.header[idx],
    )


def _write_csv_for_download(columns_dict, csv_name):
    pandas.DataFrame(columns_dict).to_csv(csv_name, index=False)


def _discrete_out(column_info):
    if not column_info.get("dtypeKind"):
        return False
    return column_info.dtypeKind[column_info.inputOutput.index("output")] == "u"


def _extract_fft_report(run_dir, sim_in):
    x, plots, title, summary_data = get_fft_report(run_dir, sim_in)
    _write_report(
        x, plots, title, fields=PKDict(x_label="f [Hz]"), summary_data=summary_data
    )


def _extract_partition_report(run_dir, sim_in):
    idx = sim_in.models[sim_in.report].columnNumber
    d = PKDict(
        train=_read_file_column(run_dir, "trainFile", idx),
        test=_read_file_column(run_dir, "testFile", idx),
    )
    if sim_in.models.dataFile.appMode == "regression":
        d.validate = _read_file_column(run_dir, "validateFile", idx)
    r = []
    for name in d:
        _update_range(r, d[name])
    plots = []
    c = PKDict()
    for name in d:
        x, y = _histogram_plot(d[name], r)
        c[name] = y
        plots.append(_plot_info(y, name))
    _write_csv_for_download(
        PKDict(x=x, **c),
        f"partitionColumnReport{idx}.csv",
    )
    _write_report(
        x,
        plots,
        title=sim_in.models.columnInfo.header[idx],
    )


def _extract_partition_selection(run_dir, sim_in):
    # return report with input0 and output0
    info = sim_in.models.columnInfo
    in_idx = info.inputOutput.index("input")
    out_idx = info.inputOutput.index("output")
    x, y = _extract_column(run_dir, in_idx)
    _, y2 = _extract_column(run_dir, out_idx)
    _write_report(
        x,
        [
            _plot_info(y, info.header[in_idx]),
            _plot_info(y2, info.header[out_idx]),
        ],
    )


def _filename(name):
    return _SIM_DATA.lib_file_name_with_model_field("dataFile", "file", name)


def _filepath(name):
    return _SIM_DATA.lib_file_abspath(_filename(name))


def _fit_animation(frame_args):
    idx = int(frame_args.columnNumber)
    frame_args.histogramBins = 30
    info = frame_args.sim_in.models.columnInfo
    header = []
    for i in range(len(info.inputOutput)):
        if info.inputOutput[i] == "output":
            if "outputShape" in info:
                header += [info.header[i] for _ in range(info.outputShape[i])]
            else:
                header.append(info.header[i])
    x = _read_file(frame_args.run_dir, _OUTPUT_FILE.predictFile)[:, idx]
    y = _read_file(frame_args.run_dir, _OUTPUT_FILE.testFile)[:, idx]
    _write_csv_for_download(
        PKDict(predict=x, test=y),
        f"fitAnimation{idx}.csv",
    )

    # TODO(pjm): for a classification-like regression, set heatmap resolution to domain size
    return template_common.heatmap(
        [x, y],
        frame_args,
        PKDict(
            x_label="Prediction",
            y_label="Ground Truth",
            title=header[idx] if header else "Fit",
            hideColorBar=True,
        ),
    )


def _image_out(info):
    if not info.get("shape"):
        return False
    idx = info.inputOutput.index("output")
    return len(info.shape[idx][1:]) > 1


def _param_to_image(info):
    if not info.get("shape"):
        return False
    o = info.inputOutput.index("output")
    i = info.inputOutput.index("input")
    return len(info.shape[o][1:]) > 1 and len(info.shape[i][1:]) == 1


def _generate_parameters_file(data):
    report = data.get("report", "")
    dm = data.models
    res, v = template_common.generate_parameters_file(data)
    v.imageOut = _image_out(dm.columnInfo)
    v.shuffleEachEpoch = True if dm.neuralNet.shuffle == "1" else False
    v.dataFile = _filename(dm.dataFile.file)
    v.weightedFile = _OUTPUT_FILE.mlModel
    v.bestFile = _OUTPUT_FILE.bestFile
    v.originalImageInFile = _OUTPUT_FILE.originalImageInFile
    v.worstFile = _OUTPUT_FILE.worstFile
    v.neuralNet_losses = _loss_function(v.neuralNet_losses)
    v.pkupdate(
        layerImplementationNames=_layer_implementation_list(data),
        neuralNetLayers=dm.neuralNet.layers,
    ).pkupdate(_OUTPUT_FILE)
    v.columnTypes = (
        "[" + ",".join(["'" + v + "'" for v in dm.columnInfo.inputOutput]) + "]"
    )
    v.image_data = pkio.has_file_extension(v.dataFile, "h5")
    v.inputsScaler = dm.dataFile.inputsScaler
    v.outputsScaler = dm.dataFile.outputsScaler
    v.feature_min = dm.dataFile.featureRangeMin
    v.feature_max = dm.dataFile.featureRangeMax
    v.discreteOutputs = _discrete_out(dm.columnInfo)
    v.paramToImage = _param_to_image(dm.columnInfo)
    if v.image_data:
        v.inPath = None
        v.outPath = None
        for idx in range(len(dm.columnInfo.header)):
            if dm.columnInfo.inputOutput[idx] == "input":
                assert not v.inPath, "Only one input allow for h5 data"
                v.inPath = dm.columnInfo.header[idx]
                v.inScaling = dm.columnInfo.dtypeKind[idx] == "f"
            elif dm.columnInfo.inputOutput[idx] == "output":
                assert not v.outPath, "Only one output allow for h5 data"
                v.outPath = dm.columnInfo.header[idx]
                v.outputShape = 1 if v.imageOut else dm.columnInfo.outputShape[idx]
                v.outScaling = dm.columnInfo.dtypeKind[idx] == "f"
        assert v.inPath, "Missing input data path"
        assert v.outPath, "Missing output data path"
        res += template_common.render_jinja(SIM_TYPE, v, "loadImages.py")
    else:
        res += template_common.render_jinja(SIM_TYPE, v, "scale.py")
    if "fileColumnReport" in report or report == "partitionSelectionReport":
        return res
    if _is_sim_report(report):
        return res
    v.hasTrainingAndTesting = (
        v.partition_section0 == "train_and_test"
        or v.partition_section1 == "train_and_test"
        or v.partition_section2 == "train_and_test"
    )
    if not v.image_data:
        res += template_common.render_jinja(SIM_TYPE, v, "partition.py")
    if "partitionColumnReport" in report:
        res += template_common.render_jinja(SIM_TYPE, v, "save-partition.py")
        return res
    if dm.dataFile.appMode == "classification":
        res += template_common.render_jinja(SIM_TYPE, v, "classification-base.py")
        d = PKDict(
            decisionTree="decision-tree",
            knn="knn",
            linearSvc="linear-svc",
            logisticRegression="logistic-regression",
        )
        return res + template_common.render_jinja(
            SIM_TYPE,
            v,
            f"{d[dm.classificationAnimation.classifier]}.py",
        )
    res += _build_model_py(v)
    res += template_common.render_jinja(SIM_TYPE, v, "train.py")
    return res


def _get_children_from_list(node, neural_net, index):
    if _is_merge_node(node) and type(neural_net[index - 1]) == list:
        for c in neural_net[index - 1]:
            node.children.append(_move_children_in_add(c))


def _get_layer_by_name(neural_net, name):
    for l in neural_net.layers:
        if l.name == name:
            return l
    raise AssertionError(f"could not find layer with name={name}")


def _get_layer_type(layer):
    return type(layer).__name__


def _get_next_node(node, neural_net):
    if _is_merge_node(node):
        return node
    assert (
        len(node.inbound) == 1
    ), f"get next should have one inbound node={node.name}, node.indbound={[n.name for n in node.inbound]}"
    return _get_layer_by_name(neural_net, node.inbound[0].name)


def _get_relevant_nodes(model):
    r = []
    for v in model._nodes_by_depth.values():
        r += v
    return r


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


def _get_fit_report(report, x_vals, y_vals):
    (
        fit_x,
        fit_y,
        fit_y_min,
        fit_y_max,
        param_vals,
        param_sigmas,
    ) = sirepo.analysis.fit_to_equation(
        x_vals,
        y_vals,
        report.fitEquation,
        report.fitVariable,
        report.fitParameters,
    )
    plots = [
        PKDict(
            points=fit_y.tolist(),
            x_points=fit_x.tolist(),
            label="fit",
        ),
        PKDict(
            points=fit_y_min.tolist(),
            x_points=fit_x.tolist(),
            label="confidence",
            _parent="confidence",
        ),
        PKDict(
            points=fit_y_max.tolist(),
            x_points=fit_x.tolist(),
            label="",
            _parent="confidence",
        ),
    ]
    return param_vals, param_sigmas, plots


# if this conversion is not done, the header gets returned as a newline-delimited string
# EmailMessage headers pseduo-dicts and can have duplicated keys, which we ignore
def _header_str_to_dict(h):
    return {k: v for k, v in h.items()}


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


class _ImagePreview:
    def __init__(self, data, run_dir=None):
        self.data = data
        self.run_dir = run_dir
        self.original = None
        self._io()

    def _io(self):
        # go through columnInfo, find first multidimensional col
        # take first dimension size and look for other columns with that single dimension
        io = PKDict()
        info = self.data.args.columnInfo
        for idx in range(len(info.header)):
            if len(info.shape[idx]) >= 3:
                io.input = PKDict(
                    path=info.header[idx],
                    kind=info.dtypeKind[idx],
                    count=info.shape[idx][0],
                )
                break
        if "input" not in io:
            raise AssertionError("No multidimensional data found in dataset")
        io.output = self._output(info, io)

        # look for a string column for labels
        for idx in range(len(info.header)):
            if info.dtypeKind[idx] in {"U", "S"}:
                io.output.label_path = info.header[idx]
                break
        if _param_to_image(info):
            io.input = PKDict(
                path="metadata/control_settings",
                kind="f",
            )
        self.info = info
        self.io = io

    def _data_url(self, filename):
        with open(filename, "rb") as f:
            r = "data:image/jpeg;base64," + pkcompat.from_bytes(b64encode(f.read()))
        return r

    def _image_grid(self, num_images):
        num_pages = min(5, 1 + (num_images - 1) // 25)
        return [min(25, num_images - 25 * i) for i in range(num_pages)]

    def _masks(self, out_width, out_height, method):
        x = _read_file(self.run_dir, _OUTPUT_FILE.testFile)
        y = _read_file(self.run_dir, _OUTPUT_FILE.predictFile)
        x, y = self._shape_images(x, y, out_width, out_height)
        return x, y, self._original_images(method)

    def _shape_images(self, x, y, width, height):
        s = width * height
        return x.reshape(len(x) // s, height, width), y.reshape(
            len(y) // s, height, width
        )

    def _original_images(self, method):
        if method == "segmentViewer" and not _param_to_image(self.info):
            return _read_file(self.run_dir, _OUTPUT_FILE.originalImageInFile)
        return None

    def dice_coefficient_plot(self):
        import matplotlib.pyplot as plt

        s = self.data.args.columnInfo.shape[
            self.data.args.columnInfo.inputOutput.index("output")
        ][1:]

        def _dice():
            def _dice_coefficient(mask1, mask2):
                return round(
                    (2 * numpy.sum(mask1 * mask2))
                    / (numpy.sum(mask1) + numpy.sum(mask2)),
                    3,
                )

            d = []
            x, y, _ = self._masks(s[0], s[1], self.data.method)
            for pair in zip(x, y):
                d.append(_dice_coefficient(pair[0], pair[1]))
            return d

        plt.figure(figsize=[10, 10])
        plt.hist(_dice())
        plt.xlabel("Dice Scores", fontsize=20)
        plt.ylabel("Counts", fontsize=20)
        plt.xticks(fontsize=14)
        plt.yticks(fontsize=14)
        p = _SIM_DATA.lib_file_write_path(self.data.args.imageFilename) + ".png"
        plt.tight_layout()
        plt.savefig(p)
        return PKDict(
            uris=[self._data_url(p)],
        )

    def _output(self, info, io):
        if "output" in info.inputOutput:
            return PKDict(path=info.header[info.inputOutput.index("output")])
        for idx in range(len(info.header)):
            if len(info.shape[idx]) <= 2 and info.shape[idx][0] == io.input.count:
                return PKDict(path=info.header[idx])
        raise AssertionError(
            f"No matching dimension found output size: {io.output.size}"
        )

    def _by_indices(self, method, y_shape):
        i = PKDict(
            bestLosses=_read_file(self.run_dir, _OUTPUT_FILE.bestFile),
            worstLosses=_read_file(self.run_dir, _OUTPUT_FILE.worstFile),
        )[method].flatten()
        i.sort()
        x, y = self._shape_images(
            _read_file(self.run_dir, _OUTPUT_FILE.testFile),
            _read_file(self.run_dir, _OUTPUT_FILE.predictFile),
            y_shape[1],
            y_shape[0],
        )
        x = x[i]
        y = y[i]
        if _param_to_image(self.info):
            return x, y, None
        return (
            x,
            y,
            _read_file(self.run_dir, _OUTPUT_FILE.originalImageInFile)[i],
        )

    def _x_y(self, run_dir=None):
        o = self.file[self.io.output.path]
        if self.data.args.method == "segmentViewer":
            w = numpy.array(o).shape[-1]
            h = numpy.array(o).shape[-2]
            return self._masks(w, h, self.data.args.method)
        if self.data.args.method in ("bestLosses", "worstLosses"):
            i = self.data.args.columnInfo.inputOutput.index("output")
            return self._by_indices(
                self.data.args.method, self.data.args.columnInfo.shape[i][1:]
            )
        return self.file[self.io.input.path], o, None

    def _grid(self, x):
        if _image_out(self.info):
            return [_SEGMENT_ROWS] * _SEGMENT_PAGES
        return self._image_grid(len(x))

    def _set_image_to_image_plt(self, plt):
        if self.data.args.method in _POST_TRAINING_PLOTS and not _param_to_image(
            self.info
        ):
            _, a = plt.subplots(3, 3)
            a[0, 0].set_title("image")
            a[0, 1].set_title("original contour")
            a[0, 2].set_title("predicted contour")
            plt.setp(a, xticks=[], yticks=[])
            return a
        _, a = plt.subplots(3, 2)
        if _param_to_image(self.info) and self.data.args.method != "imagePreview":
            a[0, 0].set_title("actual")
            a[0, 1].set_title("predicted")
        plt.setp(a, xticks=[], yticks=[])
        return a

    def _gen_image(self):
        if (
            _param_to_image(self.info)
            and not self.data.args.method in _POST_TRAINING_PLOTS
        ):
            for section in ("top", "right", "bottom", "left"):
                self.axes[self.row, 0].spines[section].set_visible(False)
            self.axes[self.row, 0].text(
                0.2,
                0.2,
                "Params:\n" + ", ".join([str(round(n, 3)) for n in self.input]),
                style="italic",
                fontsize=10,
            )
            self.axes[self.row, 1].imshow(self.output)
            return
        if _image_out(self.info):
            c = [self.input, self.output]
            if self.original is not None:
                c.insert(0, self.original)
            for i, column in enumerate(c):
                self.axes[self.row, i].imshow(column)
            return
        self.plt.subplot(_IMG_ROWS, _IMG_COLS, self.row + 1)
        self.plt.xticks([])
        self.plt.yticks([])
        self.plt.imshow(self.input)
        if len(self.file[self.io.output.path].shape) == 1:
            if "label_path" in self.io.output:
                self.plt.xlabel(
                    pkcompat.from_bytes(
                        self.file[self.io.output.label_path][self.output]
                    )
                )
            else:
                self.plt.xlabel(self.output)
        else:
            self.plt.xlabel("\n".join([str(l) for l in self.output]))

    def images(self):
        import matplotlib.pyplot as plt

        with h5py.File(_filepath(self.data.args.dataFile.file), "r") as f:
            self.file = f
            x, y, o = self._x_y()
            u = []
            k = 0
            g = (
                self._grid(x)
                if self.data.args.method not in ("bestLosses", "worstLosses")
                else [_SEGMENT_ROWS]
            )
            for i in g:
                plt.figure(figsize=[10, 10])
                self.axes = (
                    self._set_image_to_image_plt(plt) if _image_out(self.info) else None
                )
                for j in range(i):
                    self.row = j
                    self.original = o[k + j] if o is not None else None
                    self.input = x[k + j]
                    if self.io.input.kind == "f":
                        self.input = self.input.astype(float)
                    self.output = y[k + j]
                    self.plt = plt
                    self._gen_image()
                p = (
                    _SIM_DATA.lib_file_write_path(self.data.args.imageFilename)
                    + f"_{int(k/25)}.png"
                )
                plt.tight_layout()
                plt.savefig(p)
                u.append(self._data_url(p))
                k += i
            return PKDict(
                numPages=len(g),
                uris=u,
            )


def _is_branching(node):
    return len(node.outbound) > 1


def _is_merge_node(node):
    return node.layer in ("Add", "Concatenate")


def _is_sim_report(report):
    # return 'analysisReport' in report or report in _SIM_REPORTS
    return any([r in report for r in _SIM_REPORTS])


def _layer_implementation_list(data):
    res = {}
    nn = data.models.neuralNet.layers

    def _helper(nn):
        for layer in nn:
            if layer.layer == "Add" or layer.layer == "Concatenate":
                for c in layer.children:
                    _helper(c.layers)
            res[layer.layer] = 1

    _helper(nn)
    return res.keys()


def _levels_with_children(cur_node, neural_net):
    l = []
    m = False
    while _continue_building_level(cur_node, m):
        m = False
        l.insert(0, cur_node)
        if _is_merge_node(cur_node):
            r = _children(cur_node, neural_net)
            l.insert(0, r.children)
            cur_node = r.parent_node
            if not _parent_is_complete(cur_node, r.parent_sum):
                return cur_node, r.parent_sum, l
            b = _close_completed_branch(l, cur_node, neural_net)
            m = b.merge_continue
            cur_node = b.cur_node
            continue
        cur_node = _get_next_node(cur_node, neural_net)
    return cur_node, 1, l


def _loss_function(loss_fn):
    l = "".join(w.title() for w in loss_fn.split("_"))
    if loss_fn == "sparse_categorical_crossentropy":
        return "keras.losses." + l + "(from_logits=True)"
    return "keras.losses." + l + "()"


def _make_layers(model):
    neural_net = []
    for l in model.layers:
        neural_net.append(
            _set_fields_by_layer_type(
                l, PKDict(obj=l, layer=_get_layer_type(l), name=l.name)
            )
        )
    return PKDict(layers=neural_net)


def _move_children_in_add(neural_net):
    n = PKDict(layers=[])
    for i, l in enumerate(neural_net):
        if not type(l) == list:
            l["children"] = []
            _get_children_from_list(l, neural_net, i)
            n.layers.append(_clean_layer(l))
    return n


def _numbered_model_file(model):
    for m in ("fitAnimation", "fileColumnReport", "partitionColumnReport"):
        if m in model:
            return True
    return False


def _parent_is_complete(node, parent_sum):
    return len(node.outbound) == parent_sum


def _plot_info(y, label="", style=None):
    return PKDict(points=list(y), label=label, style=style)


def _read_file(run_dir, filename):
    res = numpy.load(str(run_dir.join(filename)))
    if len(res.shape) == 1:
        res.shape = (res.shape[0], 1)
    return res


def _read_file_column(run_dir, name, idx):
    return _read_file(run_dir, _OUTPUT_FILE[name])[:, idx]


def _read_file_with_history(run_dir, filename, report=None):
    import copy

    res = _read_file(run_dir, filename)
    if not report:
        return res
    if "history" in report:
        for action in report.history:
            if action.action == "trim":
                idx = int(action.trimField)
                res = res[
                    (res[:, idx] >= action.trimMin) & (res[:, idx] <= action.trimMax)
                ]
            elif action.action == "cluster":
                report2 = copy.deepcopy(report)
                report2.update(action)
                clusters = _compute_clusters(report2, res)
                labels = numpy.array(clusters.group)
                res = res[labels == action.clusterIndex, :]
    return res


def _remote_data_bytes_loaded(filename):
    try:
        return PKDict(
            bytesLoaded=os.path.getsize(
                _SIM_DATA.lib_file_abspath(
                    _SIM_DATA.lib_file_name_with_model_field(
                        "dataFile", "file", filename
                    )
                )
            )
        )
    except Exception as e:
        return PKDict(error=e)


def _report_info(x, plots, title="", fields=PKDict(), summary_data=PKDict()):
    res = PKDict(
        title=title,
        x_range=[float(min(x)), float(max(x))],
        y_label="",
        x_label="",
        x_points=list(x),
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
        summaryData=summary_data,
    )
    res.update(fields)
    return res


def _set_children(neural_net):
    c = neural_net.layers[-1]
    return _move_children_in_add(_levels_with_children(c, neural_net)[2])


def _set_fields_by_layer_type(l, new_layer):
    def _conv(l):
        return PKDict(
            strides=l.strides[0],
            padding=l.padding,
            kernel=l.kernel_size[0],
            dimensionality=l._trainable_weights[0].shape[-1],
            activation=l.activation.__name__,
        )

    def _dropout(layer):
        return PKDict(dropoutRate=layer.rate)

    def _pool(layer):
        return PKDict(
            strides=layer.strides[0],
            padding=layer.padding,
            size=layer.pool_size[0],
        )

    if "input" not in l.name:
        d = PKDict(
            Activation=lambda l: PKDict(activation=l.activation.__name__),
            Add=lambda l: PKDict(),
            BatchNormalization=lambda l: PKDict(momentum=l.momentum),
            Concatenate=lambda l: PKDict(),
            Conv2D=lambda l: _conv(l),
            Dense=lambda l: PKDict(
                dimensionality=l.units,
                activation=l.activation.__name__,
            ),
            GlobalAveragePooling2D=lambda l: PKDict(),
            GaussianNoise=lambda l: PKDict(stddev=l.stddev),
            GaussianDropout=lambda l: _dropout(l),
            AlphaDropout=lambda l: _dropout(l),
            Dropout=lambda l: _dropout(l),
            Flatten=lambda l: PKDict(),
            Reshape=lambda l: PKDict(new_shape=str(l.target_shape)),
            SeparableConv2D=lambda l: _conv(l),
            MaxPooling2D=lambda l: _pool(l),
            AveragePooling2D=lambda l: _pool(l),
            Conv2DTranspose=lambda l: _conv(l),
            UpSampling2D=lambda l: PKDict(
                size=l.size[0], interpolation=l.interpolation
            ),
            ZeroPadding2D=lambda l: PKDict(padding=l.padding[0][0]),
        )
        if not d.get(new_layer.layer):
            raise sirepo.util.UserAlert(
                f"No support for importing {l.name.title()} layer"
            )
        return new_layer.pkmerge(d[new_layer.layer](l))
    return new_layer


def _set_inbound(model, neural_net):
    r = _get_relevant_nodes(model)
    for l in neural_net.layers:
        i = []
        for n in l.obj._inbound_nodes:
            if r and n not in r:
                continue
            for (
                inbound_layer,
                node_index,
                tensor_index,
                _,
            ) in n.iterate_inbound():
                i.append(inbound_layer)
            l["inbound"] = i
    return neural_net


def _set_outbound(neural_net):
    for l in neural_net.layers:
        l["outbound"] = []
    for l in neural_net.layers:
        for i in l.inbound:
            c = _get_layer_by_name(neural_net, i.name)
            if "outbound" in c:
                c.outbound.append(l.obj)
    return neural_net


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


def _write_report(x, plots, title="", fields=PKDict(), summary_data=PKDict()):
    template_common.write_sequential_result(
        _report_info(x, plots, title, fields=fields, summary_data=summary_data)
    )
