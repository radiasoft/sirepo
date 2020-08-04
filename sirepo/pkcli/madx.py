# -*- coding: utf-8 -*-
"""Wrapper to run MAD-X from the command line.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
import glob
import numpy as np
import os
import py.path
import re
import sirepo.template.madx as template


def run(cfg_dir):
    _run_simulation(cfg_dir)
    template.save_sequential_report_data(
        simulation_db.read_json(template_common.INPUT_BASE_NAME),
        py.path.local(cfg_dir),
    )


def run_background(cfg_dir):
    _run_simulation(cfg_dir)


def _bunch_twiss(bunch, dim):
    res = PKDict(
        alpha=float(bunch[f'alf{dim}']),
        beta=float(bunch[f'bet{dim}']),
        emittance=float(bunch[f'e{dim}']),
    )
    res.gamma = (1 + res.alpha ** 2) / res.beta
    return res


def _generate_ptc_particles_file(run_dir, data, twiss):
    bunch = data.models.bunch
    p = _ptc_particles(
        PKDict(
            x=_bunch_twiss(bunch, 'x'),
            y=_bunch_twiss(bunch, 'y'),
        ),
        bunch.numberOfParticles,
        bunch.randomSeed,
    )
    v = PKDict(
        x=template.to_floats(p.x.pos),
        px=template.to_floats(p.x.p),
        y=template.to_floats(p.y.pos),
        py=template.to_floats(p.y.p),
        t=template.to_floats(p.t.pos),
        pt=template.to_floats(p.t.p),
    )
    if 'bunchReport' in data.report:
        v.summaryData = twiss
        simulation_db.write_json(run_dir.join(template.BUNCH_PARTICLES_FILE), v)
    r = ''
    for i in range(len(v.x)):
        r += 'ptc_start'
        for f in ('x', 'px', 'y', 'py', 't', 'pt'):
           r += f', {f}={v[f][i]}'
        r +=';\n'
    pkio.write_text(run_dir.join(template.PTC_PARTICLES_FILE), r)


def _is_matched_bunch(data):
    return data.models.bunch.matchTwissParameters == '1'


def _need_particle_file(data):
    if 'bunchReport' in data.report \
       or (data.report == 'animation' and LatticeUtil.find_first_command(data, template.PTC_LAYOUT_COMMAND)):
        return True
    return False


# condensed version of https://github.com/radiasoft/rscon/blob/d3abdaf5c1c6d41797a4c96317e3c644b871d5dd/webcon/madx_examples/FODO_example_PTC.ipynb
def _ptc_particles(twiss_params, num_particles, seed):
    mean = [0, 0, 0, 0]
    cov = []
    for dim in twiss_params:
        m1 = 1 if dim == 'x' else 0
        m2 = 1 - m1
        tp = PKDict(twiss_params[dim])
        dd = tp.beta * tp.emittance
        ddp = -tp.alpha * tp.emittance
        dpdp = tp.emittance * tp.gamma
        cov.append([m1 * dd, m1 * ddp, m2 * dd, m2 * ddp])
        cov.append([m1 * ddp, m1 * dpdp, m2 * ddp, m2 * dpdp])

    rnd = np.random.default_rng(seed)
    transverse = rnd.multivariate_normal(mean, cov, num_particles)
    x = transverse[:, 0]
    xp = transverse[:, 1]
    y = transverse[:, 2]
    yp = transverse[:, 3]

    # for now the longitudional coordinates are set to zero. This just means there
    # is no longitudinal distribuion. We can change this soon.
    long_part = rnd.multivariate_normal([0, 0], [[0, 0], [0, 0]], num_particles)

    particles = np.column_stack([x, xp, y, yp, long_part[:, 0], long_part[:, 1]])
    return PKDict(
        x=PKDict(pos=particles[:,0], p=particles[:,1]),
        y=PKDict(pos=particles[:,2], p=particles[:,3]),
        t=PKDict(pos=particles[:,4], p=particles[:,5]),
    )


def _run_madx(filename=template.MADX_INPUT_FILE):
    pksubprocess.check_call_with_signals(
        ['madx', filename],
        msg=pkdlog,
        output=template.MADX_LOG_FILE,
    )
    # fixup madx munged file names
    for f in glob.glob('*.tfsone'):
        n = re.sub(r'tfsone$', 'tfs', f)
        os.rename(f, n)


def _run_simulation(cfg_dir):
    cfg_dir = py.path.local(cfg_dir)
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if _need_particle_file(data):
        twiss = PKDict()
        if _is_matched_bunch(data):
            report = data.report
            # run twiss report and copy results into beam
            data.models.simulation.activeBeamlineId = data.models.simulation.visualizationBeamlineId
            data.report = 'twissReport'
            template.write_parameters(data, cfg_dir, False, 'matched-twiss.madx')
            _run_madx('matched-twiss.madx')
            twiss = template.extract_report_twissReport(data, cfg_dir).initialTwissParameters
            data.models.bunch.update(twiss)
            # restore the original report and generate new source with the updated beam values
            data.report = report
            if data.report == 'animation':
                template.write_parameters(data, py.path.local(cfg_dir), False)
        _generate_ptc_particles_file(cfg_dir, data, twiss)
    if cfg_dir.join(template.MADX_INPUT_FILE).exists():
        _run_madx()
