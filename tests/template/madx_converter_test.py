# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.madx_converter`

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
import pytest


def test_from_elegant_to_madx_and_back():
    from pykern import pkio
    from pykern.pkunit import pkeq
    from sirepo.template import elegant, madx, madx_converter, madx_parser

    with pkunit.save_chdir_work() as d:
        for name in ('SPEAR3', 'Compact Storage Ring', 'Los Alamos Proton Storage Ring'):
            data = _example_data(name)
            mad = madx_converter.to_madx(elegant.SIM_TYPE, data)
            outfile = name.lower().replace(' ', '-') + '.madx'
            actual = madx.python_source_for_model(mad, None)
            pkio.write_text(outfile, actual)
            e = pkunit.data_dir().join(outfile)
            expect = pkio.read_text(e)
            pkeq(expect, actual, 'diff {} {}', e, d.join(outfile))

            data = madx_parser.parse_file(actual)
            lattice = madx_converter.from_madx(elegant.SIM_TYPE, data)
            outfile = name.lower().replace(' ', '-') + '.lte'
            actual = elegant.python_source_for_model(lattice, None)
            pkio.write_text(outfile, actual)
            e = pkunit.data_dir().join(outfile)
            expect = pkio.read_text(e)
            pkeq(expect, actual, 'diff {} {}', e, d.join(outfile))


def _example_data(simulation_name):
    from sirepo import simulation_db
    from sirepo.template import elegant
    for data in simulation_db.examples(elegant.SIM_TYPE):
        if data.models.simulation.name == simulation_name:
            return simulation_db.fixup_old_data(data)[0]
    raise AssertionError(f'failed to find example={simulation_name}')
