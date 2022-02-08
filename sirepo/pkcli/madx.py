# -*- coding: utf-8 -*-
"""Wrapper to run MAD-X from the command line.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import particle_beam
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
import glob
import numpy
import os
import re
import sirepo.template.madx as template


def particle_file_for_external_lattice():
    data = simulation_db.read_json(
        template_common.INPUT_BASE_NAME,
    ).models.externalLattice
    data.report = 'unused'
    data.models.bunch.matchTwissParameters = '0'
    _create_particle_file(pkio.py_path('.'), data)


def run(cfg_dir):
    _run_simulation(cfg_dir)
    template.save_sequential_report_data(
        simulation_db.read_json(template_common.INPUT_BASE_NAME),
        pkio.py_path(cfg_dir),
    )


def run_background(cfg_dir):
    _run_simulation(cfg_dir)


def _create_particle_file(cfg_dir, data):
    twiss = PKDict()
    if _is_matched_bunch(data):
        report = data.report
        # run twiss report and copy results into beam
        data.models.simulation.activeBeamlineId = data.models.simulation.visualizationBeamlineId
        data.report = 'twissReport'
        template.write_parameters(data, cfg_dir, False, 'matched-twiss.madx')
        _run_madx('matched-twiss.madx')
        twiss = template.extract_parameter_report(data, cfg_dir).initialTwissParameters
        data.models.bunch.update(twiss)
        # restore the original report and generate new source with the updated beam values
        data.report = report
        if data.report == 'animation':
            template.write_parameters(data, pkio.py_path(cfg_dir), False)
    _generate_ptc_particles_file(cfg_dir, data, twiss)


def _generate_ptc_particles_file(run_dir, data, twiss):
    bunch = data.models.bunch
    beam = LatticeUtil.find_first_command(data, 'beam')
    p = particle_beam.populate_uncoupled_beam(
        bunch.numberOfParticles,
        float(bunch.betx),
        float(bunch.alfx),
        float(bunch.ex),
        float(bunch.bety),
        float(bunch.alfy),
        bunch.ey,
        beam.sigt,
        beam.sige,
        iseed=bunch.randomSeed,
    )
    v = PKDict(
        x=template.to_floats(p[:,0] + float(bunch.x)),
        px=template.to_floats(p[:,1] + float(bunch.px)),
        y=template.to_floats(p[:,2] + float(bunch.y)),
        py=template.to_floats(p[:,3] + float(bunch.py)),
        t=template.to_floats(p[:,4]),
        pt=template.to_floats(p[:,5]),
    )
    if 'report' in data and 'bunchReport' in data.report:
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
    cfg_dir = pkio.py_path(cfg_dir)
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if _need_particle_file(data):
        _create_particle_file(cfg_dir, data)
    if cfg_dir.join(template.MADX_INPUT_FILE).exists():
        _run_madx()
