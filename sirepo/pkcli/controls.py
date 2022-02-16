# -*- coding: utf-8 -*-
"""Wrapper to run controls code from the command line.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio, pkjson
from pykern.pkdebug import pkdp
from pykern.pkcollections import PKDict
from sirepo.template import template_common
import sirepo.pkcli.madx
import sirepo.template.controls as template
from sirepo import simulation_db


def run(cfg_dir):
    template_common.exec_parameters()
    d = pkio.py_path(cfg_dir)
    template_common.write_sequential_result(
        PKDict(
            elementValues=template._read_summary_line(
                d,
                simulation_db.get_schema(template.SIM_TYPE).constants.maxBPMPoints,
            )
        ),
        run_dir=d,
    )


def run_background(cfg_dir):
    template_common.exec_parameters()


def particle_file_for_external_lattice():
    data = simulation_db.read_json(
        template_common.INPUT_BASE_NAME,
    )
    data.models.externalLattice.models.bunch.numberOfParticles = data.models.command_beam.particleCount
    pkdp('\n\n\n BEFORE data.models.externalLattice: {}', data.models.externalLattice.models)
    b = [k for k in data.models.command_twiss
        if k in data.models.externalLattice.models.bunch]
    for p in b:
        data.models.externalLattice.models.bunch[p] = data.models.command_twiss[p]
    beam = data.models.command_beam
    data = data.models.externalLattice
    data.models.command_beam = beam
    data.report = 'unused'
    data.models.bunch.matchTwissParameters = '0'
    pkdp('\n\n\n AFTER data.models.externalLattice: {}', data.models)
    pkdp('command_beam: {}', beam)
    sirepo.pkcli.madx.create_particle_file(pkio.py_path('.'), data)