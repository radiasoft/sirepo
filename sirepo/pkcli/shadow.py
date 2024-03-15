# -*- coding: utf-8 -*-
"""Wrapper to run shadow from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
from sirepo import simulation_db
from sirepo.template import template_common
import numpy
import py.path
import re
import sirepo.template.shadow as template

_MM_TO_CM = 0.1
_CM_TO_M = 0.01
_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)

_SCALE_COLUMNS = [1, 2, 3, 13, 20]
_PLOT_LABELS = {
    "1": ["X [m]"],
    "2": ["Y [m]"],
    "3": ["Z [m]"],
    "4": ["X' [rad]"],
    "5": ["Y' [rad]"],
    "6": ["Z' [rad]"],
    "11": ["Energy [eV]", "E [eV]"],
    "13": ["Optical Path [m]", "s"],
    "14": ["Phase s [rad]", "ϕ s [rad]"],
    "15": ["Phase p [rad]", "ϕ p [rad]"],
    "19": ["Wavelength [Å]", "λ [Å]"],
    "20": ["R = sqrt(X² + Y² + Z²) [m]", "R [m]"],
    "21": ["Theta (angle from Y axis) [rad]", "θ [rad]"],
    "22": ["Magnitude = |Es| + |Ep|", "|Es| + |Ep|"],
    "23": ["Total Intensity = |Es|² + |Ep|²", "|Es|² + |Ep|²"],
    "24": ["S Intensity = |Es|²", "|Es|²"],
    "25": ["P Intensity = |Ep|²", "|Ep|²"],
    "26": ["|K| [Å⁻¹]"],
    "27": ["K X [Å⁻¹]"],
    "28": ["K Y [Å⁻¹]"],
    "29": ["K Z [Å⁻¹]"],
    "30": ["S0-stokes = |Ep|² + |Es|²", "S0"],
    "31": ["S1-stokes = |Ep|² - |Es|²", "S1"],
    "32": ["S2-stokes = 2|Es||Ep|cos(Phase s-Phase p)", "S2"],
    "33": ["S3-stokes = 2|Es||Ep|sin(Phase s-Phase p)", "S3"],
}


def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data.report == "beamStatisticsReport":
        res = _run_beam_statistics(cfg_dir, data)
    else:
        res = _run_shadow(cfg_dir, data)
    template_common.write_sequential_result(res)


def run_background(cfg_dir):
    pass


def _label(column, values):
    for v in values:
        if column == v[0]:
            return v[1]
    raise RuntimeError("unknown column value: ", column)


def _label_for_weight(column, values):
    if column in _PLOT_LABELS:
        if len(_PLOT_LABELS[column]) > 1:
            return _PLOT_LABELS[column][1]
        return _PLOT_LABELS[column][0]
    return _label(column, values)


def _label_with_units(column, values):
    if column in _PLOT_LABELS:
        return _PLOT_LABELS[column][0]
    return _label(column, values)


def _run_beam_statistics(cfg_dir, data):
    template_common.exec_parameters()
    report = data.models.beamStatisticsReport
    d = pkjson.load_any(py.path.local(cfg_dir).join(template.BEAM_STATS_FILE))
    x = d.s
    plots = []
    labels = dict((e[0], e[1]) for e in _SCHEMA.enum.BeamStatisticsParameter)
    for y in ("y1", "y2", "y3"):
        if report[y] == "none":
            continue
        label = labels[report[y]]
        if report[y] in ("sigmax", "sigmaz"):
            label += " [m]"
        elif report[y] in ("sigdix", "sigdiz", "angxz", "angxpzp"):
            label += " [rad]"
        plots.append(
            PKDict(
                field=report[y],
                label=label,
                points=d[report[y]],
            )
        )
    return PKDict(
        aspectRatio=0.3,
        title="",
        x_range=[min(x), max(x)],
        y_label="",
        x_label="Longitudinal Position [m]",
        x_points=x,
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
    )


def _run_shadow(cfg_dir, data):
    beam = template_common.exec_parameters().beam
    model = data["models"][data["report"]]
    column_values = _SCHEMA["enum"]["ColumnValue"]

    if "y" in model:
        x_range = None
        y_range = None
        if model["overrideSize"] == "1":
            x_range = (
                numpy.array(
                    [
                        model["horizontalOffset"] - model["horizontalSize"] / 2,
                        model["horizontalOffset"] + model["horizontalSize"] / 2,
                    ]
                )
                * _MM_TO_CM
            ).tolist()
            y_range = (
                numpy.array(
                    [
                        model["verticalOffset"] - model["verticalSize"] / 2,
                        model["verticalOffset"] + model["verticalSize"] / 2,
                    ]
                )
                * _MM_TO_CM
            ).tolist()
        ticket = beam.histo2(
            int(model["x"]),
            int(model["y"]),
            nbins=template_common.histogram_bins(model["histogramBins"]),
            ref=int(model["weight"]),
            nolost=1,
            calculate_widths=0,
            xrange=x_range,
            yrange=y_range,
        )
        _scale_ticket(ticket)
        values = ticket["histogram"].T
        assert not numpy.isnan(values).any(), "nan values found"
        res = PKDict(
            x_range=[ticket["xrange"][0], ticket["xrange"][1], ticket["nbins_h"]],
            y_range=[ticket["yrange"][0], ticket["yrange"][1], ticket["nbins_v"]],
            x_label=_label_with_units(model["x"], column_values),
            y_label=_label_with_units(model["y"], column_values),
            z_label="Intensity" if int(model["weight"]) else "Rays",
            title="{}, {}".format(
                _label(model["x"], column_values), _label(model["y"], column_values)
            ),
            z_matrix=values.tolist(),
            frameCount=1,
        )
    else:
        weight = int(model["weight"])
        ticket = beam.histo1(
            int(model["column"]),
            nbins=template_common.histogram_bins(model["histogramBins"]),
            ref=weight,
            nolost=1,
            calculate_widths=0,
        )
        _scale_ticket(ticket)
        res = PKDict(
            title=_label(model["column"], column_values),
            x_range=[ticket["xrange"][0], ticket["xrange"][1], ticket["nbins"]],
            y_label="{}{}".format(
                "Number of Rays",
                (
                    " weighted by {}".format(
                        _label_for_weight(model["weight"], column_values)
                    )
                    if weight
                    else ""
                ),
            ),
            x_label=_label_with_units(model["column"], column_values),
            points=ticket["histogram"].T.tolist(),
            frameCount=1,
        )
        # pkdlog('range amount: {}', res['x_range'][1] - res['x_range'][0])
        # 1.55431223448e-15
        dist = res["x_range"][1] - res["x_range"][0]
        # TODO(pjm): only rebalance range if outside of 0
        if dist < 1e-14:
            # TODO(pjm): include offset range for client
            res["x_range"][0] = 0
            res["x_range"][1] = dist
    return res


def _scale_ticket(ticket):
    if "xrange" in ticket:
        col_h = ticket["col_h"] if "col_h" in ticket else ticket["col"]
        if col_h in _SCALE_COLUMNS:
            ticket["xrange"][0] *= _CM_TO_M
            ticket["xrange"][1] *= _CM_TO_M
    if "yrange" in ticket:
        if ticket["col_v"] in _SCALE_COLUMNS:
            ticket["yrange"][0] *= _CM_TO_M
            ticket["yrange"][1] *= _CM_TO_M
