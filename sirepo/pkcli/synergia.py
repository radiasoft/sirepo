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
    with pkio.save_chdir(cfg_dir):
        exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data['report'] == 'bunchReport':
        res = _run_bunch_report(data)
    else:
        raise RuntimeError('unknown report: {}'.format(data['report']))
    simulation_db.write_result(res)


def run_background(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
        simulation_db.write_result({})


def _run_bunch_report(data):
    report = data.models[data['report']]
    from synergia.bunch import Bunch, populate_6d
    from synergia.foundation import Four_momentum, Reference_particle, Random_distribution, pconstants
    from synergia.utils import Commxx
    import numpy as np

    fm = Four_momentum(pconstants.mp)
    fm.set_momentum(0.0685)
    ref = Reference_particle(pconstants.proton_charge, fm)
    comm = Commxx()
    bunch = Bunch(ref, 50000, 1.5e+8, comm)
    bunch.set_z_period_length(0.0673)
    means = np.array([0, 0, 0, 0, 0, 0])
    covariance_matrix = np.array([
        [3.33389840e-06, 1.98159549e-19, 0, 0, 0, 0],
        [1.98159549e-19, 4.56222662e-06, 0, 0, 0, 0],
        [0, 0, 4.33096069e-06, -6.34828466e-20, 0, 0],
        [0, 0, -6.34828466e-20, 3.51192289e-06, 0, 0],
        [0, 0, 0, 0, 2.44449997e-03, 0],
        [0, 0, 0, 0, 0, 1.00000000e-06],
    ])
    dist = Random_distribution(1415926, comm)
    populate_6d(dist, bunch, means, covariance_matrix)
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
