# -*- coding: utf-8 -*-
"""Wrapper to run myapp from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import csv
import sirepo.template.myapp as template
import sys


_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)


def run(cfg_dir):
    pksubprocess.check_call_with_signals(
        [sys.executable, template_common.PARAMETERS_PYTHON_FILE],
    )
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data.report == "heightWeightReport":
        res = _report(
            "Dog Height and Weight Over Time",
            ("height", "weight"),
            data,
        )
    else:
        raise AssertionError("unknown report: {}".format(data.report))
    template_common.write_sequential_result(res)


def _csv_to_cols():
    with open(template.OUTPUT_NAME, "r") as f:
        rows = csv.reader(f)
        headers = next(rows)
        cols = [[] for _ in headers]
        for row in rows:
            for i, c in enumerate(row):
                cols[i].append(float(c))
    return dict((k.lower(), cols[i]) for i, k in enumerate(headers))


def _label(field):
    return _SCHEMA.model.dog[field][0]


def _plot(dog, field, cols):
    return {
        "name": field,
        "label": _label(field),
        "points": cols[field],
    }


def _report(title, fields, data):
    dog = data.models.dog
    cols = _csv_to_cols()
    x_points = cols["year"]
    plots = [_plot(dog, f, cols) for f in fields]
    return {
        "title": title,
        "x_range": [x_points[0], x_points[-1]],
        "y_label": _label(fields[0]) if len(fields) == 1 else "",
        "x_label": "Age (years)",
        "x_points": x_points,
        "plots": plots,
        "y_range": template_common.compute_plot_color_and_range(plots),
    }
