# -*- coding: utf-8 -*-
"""Wrapper to run myapp from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import simulation_db
from sirepo.template import template_common
import numpy as np
import sirepo.template.synergia as template

_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)


def run(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data['report'] == 'bunchReport':
        try:
            with pkio.save_chdir(cfg_dir):
                exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
                # bunch variable comes from parameter file exec() above
            res = _run_bunch_report(data, bunch)
        except Exception as e:
            res = {
                'error': str(e),
            }
        simulation_db.write_result(res)
    else:
        raise RuntimeError('unknown report: {}'.format(data['report']))


def run_background(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
        simulation_db.write_result({})


def _run_bunch_report(data, bunch):
    report = data.models[data['report']]
    particles = bunch.get_local_particles()
    x = particles[:, getattr(bunch, report['x'])]
    y = particles[:, getattr(bunch, report['y'])]
    hist, edges = np.histogramdd([x, y], template_common.histogram_bins(200))
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': _label(report['x']),
        'y_label': _label(report['y']),
        'title': '{}-{}'.format(report['x'], report['y']),
        'z_matrix': hist.T.tolist(),
    }


def _label(v):
    return '{} [m]'.format(v)
