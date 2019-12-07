# -*- coding: utf-8 -*-
u"""RCSCON execution template.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc, pkdlog
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import csv
import numpy as np
import re
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    return res


def extract_report_data(run_dir, sim_in):
    m = re.search(r'(\d+)$', sim_in.report)
    index = int(m.group(1))
    x, y, col_name, source_name = _extract_column(run_dir, sim_in, index)
    plots = [
        {
            'points': y.tolist(),
            'label': col_name,
        },
    ]
    simulation_db.write_result({
        'title': '',
        'x_range': [min(x), max(x)],
        'y_label': '',
        'x_label': '',
        'x_points': x.tolist(),
        'plots': plots,
        'y_range': template_common.compute_plot_color_and_range(plots),
    }, run_dir=run_dir)


def get_application_data(data):
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


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _extract_column(run_dir, sim_in, index):
    header, v = _read_file(run_dir, _SIM_DATA.rcscon_filename(sim_in, 'files', 'inputs'))
    source = 'inputs'
    if index >= len(header):
        index -= len(header)
        header, v = _read_file(run_dir, _SIM_DATA.rcscon_filename(sim_in, 'files', 'outputs'))
        source = 'outputs'
    y = v[:, index]
    x = np.arange(0, len(y))
    return x, y, header[index], source


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    v['inputsFileName'] = _SIM_DATA.lib_file_name('files', 'inputs', v['files_inputs'])
    v['outputsFileName'] = _SIM_DATA.lib_file_name('files', 'outputs', v['files_outputs'])
    return res \
        + template_common.render_jinja(SIM_TYPE, v, 'scale.py') \
        + template_common.render_jinja(SIM_TYPE, v, 'train.py')


def _read_file(run_dir, filename):
    path = str(run_dir.join(filename))
    with open(path) as f:
        reader = csv.reader(f)
        for row in reader:
            header = row
            break
    return header, np.genfromtxt(path, delimiter=',', skip_header=1)
