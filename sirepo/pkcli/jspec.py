# -*- coding: utf-8 -*-
"""Wrapper to run JSPEC from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pksubprocess
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import sdds_util, template_common, madx_parser
import re
import shutil
import sirepo.sim_data
import sirepo.template.jspec as template

_SIM_DATA = sirepo.sim_data.get_class("jspec")


def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data["report"] == "twissReport":
        template_common.write_sequential_result(_extract_twiss_report(data))
    elif data["report"] == "rateCalculationReport":
        _run_jspec(data)
        template_common.write_sequential_result(template.get_rates(cfg_dir))
    else:
        raise AssertionError("unknown report: {}".format(data["report"]))


def run_background(cfg_dir):
    _run_jspec(simulation_db.read_json(template_common.INPUT_BASE_NAME))


def _elegant_to_madx(ring):
    # if the lattice source is an elegant twiss file, convert it to MAD-X format
    if ring["latticeSource"] == "madx":
        return _SIM_DATA.lib_file_name_with_model_field(
            "ring", "lattice", ring["lattice"]
        )
    if ring["latticeSource"] == "elegant":
        elegant_twiss_file = _SIM_DATA.lib_file_name_with_model_field(
            "ring", "elegantTwiss", ring["elegantTwiss"]
        )
    else:  # elegant-sirepo
        if "elegantSirepo" not in ring or not ring["elegantSirepo"]:
            raise RuntimeError("elegant simulation not selected")
        tf = _SIM_DATA.jspec_elegant_dir().join(
            ring.elegantSirepo, _SIM_DATA.jspec_elegant_twiss_path()
        )
        if not tf.exists():
            raise RuntimeError(
                "elegant twiss output unavailable. Run elegant simulation."
            )
        shutil.copyfile(str(tf), _SIM_DATA.JSPEC_ELEGANT_TWISS_FILENAME)
        elegant_twiss_file = _SIM_DATA.JSPEC_ELEGANT_TWISS_FILENAME
    sdds_util.twiss_to_madx(elegant_twiss_file, template.JSPEC_TWISS_FILENAME)
    return template.JSPEC_TWISS_FILENAME


_X_FIELD = "s"

_FIELD_UNITS = {
    "betx": "m",
    #'alfx': '',
    "mux": "rad/2π",
    "dx": "m",
    #'dpx': '',
    "bety": "m",
    #'alfy': '',
    "muy": "rad/2π",
    "dx": "m",
    #'dpx': '',
}


def _extract_twiss_report(data):
    report = data["models"][data["report"]]
    report["x"] = _X_FIELD
    values = madx_parser.parse_tfs_file(_elegant_to_madx(data["models"]["ring"]))
    # special case if dy and/or dpy are missing, default to 0s
    for opt_col in ("dy", "dpy"):
        if opt_col not in values and "dx" in values:
            values[opt_col] = ["0"] * len(values["dx"])
    x = _float_list(values[report["x"]])
    y_range = None
    plots = []
    for f in ("y1", "y2", "y3"):
        if report[f] == "none":
            continue
        plots.append(
            {
                "points": _float_list(values[report[f]]),
                "label": (
                    "{} [{}]".format(report[f], _FIELD_UNITS[report[f]])
                    if report[f] in _FIELD_UNITS
                    else report[f]
                ),
            }
        )
    return {
        "title": "",
        "x_range": [min(x), max(x)],
        "y_label": "",
        "x_label": "{} [{}]".format(report["x"], "m"),
        "x_points": x,
        "plots": plots,
        "y_range": template_common.compute_plot_color_and_range(plots),
    }


def _float_from_str(v):
    # handle misformatted floats, ex. -9.29135e-00E-25
    v = re.sub(r"(e[+\-]\d+)(e[+\-]\d+)", r"\1", v, flags=re.IGNORECASE)
    return float(v)


def _float_list(ar):
    return [_float_from_str(x) for x in ar]


def _run_jspec(data):
    _elegant_to_madx(data["models"]["ring"])
    r = template_common.exec_parameters()
    f = template.JSPEC_INPUT_FILENAME
    pkio.write_text(f, r.jspec_file)
    pksubprocess.check_call_with_signals(
        ["jspec", f], msg=pkdlog, output=template.JSPEC_LOG_FILE
    )


def _parse_madx(tfs_file):
    text = pkio.read_text(tfs_file)
    mode = "header"
    col_names = []
    rows = []
    for line in text.split("\n"):
        if mode == "header":
            # header row starts with *
            if re.search(r"^\*\s", line):
                col_names = re.split(r"\s+", line)
                col_names = col_names[1:]
                mode = "data"
        elif mode == "data":
            # data rows after header, start with blank
            if re.search(r"^\s+\S", line):
                data = re.split(r"\s+", line)
                rows.append(data[1:])
    res = dict(map(lambda x: (x.lower(), []), col_names))
    for i in range(len(col_names)):
        name = col_names[i].lower()
        if name:
            for row in rows:
                res[name].append(row[i])
    # special case if dy and/or dpy are missing, default to 0s
    for opt_col in ("dy", "dpy"):
        if opt_col not in res:
            res[opt_col] = ["0"] * len(res["dx"])
    return res
