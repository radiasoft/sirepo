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
    from pykern.pkunit import pkeq, file_eq
    from sirepo.template import elegant
    from sirepo.template.elegant import ElegantMadxConverter

    with pkunit.save_chdir_work() as d:
        for name in ('SPEAR3', 'Compact Storage Ring', 'Los Alamos Proton Storage Ring'):
            data = _example_data(name)
            actual = ElegantMadxConverter().to_madx_text(data)
            file_eq(
                name.lower().replace(' ', '-') + '.madx',
                actual=actual,
            )
            file_eq(
                name.lower().replace(' ', '-') + '.lte',
                actual=elegant.python_source_for_model(
                    ElegantMadxConverter().from_madx_text(actual),
                    None,
                ),
            )

def test_import_elegant_export_madx(import_req):
    from pykern.pkunit import pkeq, file_eq
    from sirepo.template import elegant
    from sirepo.template.elegant import ElegantMadxConverter
    data = elegant.import_file(import_req(pkunit.data_dir().join('test1.ele')))
    data = elegant.import_file(import_req(pkunit.data_dir().join('test1.lte')), test_data=data)
    # this is updated from javascript unfortunately
    data.models.bunch.longitudinalMethod = '3'
    actual = ElegantMadxConverter().to_madx_text(data)
    file_eq(
        'test1.madx',
        actual=actual,
    )

def test_elegant_from_madx():
    from pykern.pkunit import pkeq, file_eq
    from sirepo.template import elegant
    from sirepo.template.elegant import ElegantMadxConverter
    from sirepo.template import madx_parser
    # this is updated from javascript unfortunately
    data = madx_parser.parse_file(pkio.read_text(
                pkunit.data_dir().join('test1.madx')))
    actual = ElegantMadxConverter().from_madx(data)
    file_eq(
        'test_ele_from_madx.txt',
        actual=elegant.python_source_for_model(actual, None),
    )


def test_import_opal_export_madx(import_req):
    _opal_to_madx(import_req, 'test2')


def test_import_opal_export_madx02(import_req):
    _opal_to_madx(import_req, 'test4')


def test_import_opal_export_madx_pow(import_req):
    _opal_to_madx(import_req, 'test3')


def _example_data(simulation_name):
    from sirepo import simulation_db
    from sirepo.template import elegant
    for data in simulation_db.examples(elegant.SIM_TYPE):
        if data.models.simulation.name == simulation_name:
            return simulation_db.fixup_old_data(data)[0]
    raise AssertionError(f'failed to find example={simulation_name}')


def _opal_to_madx(import_req, basename):
    from pykern.pkunit import pkeq, file_eq
    from sirepo.template import opal
    from sirepo.template.opal import OpalMadxConverter
    file_eq(
        f'{basename}.madx',
        actual=OpalMadxConverter().to_madx_text(
            opal.import_file(import_req(pkunit.data_dir().join(f'{basename}.in')))
        ),
    )
