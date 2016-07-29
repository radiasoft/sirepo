# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.srw.py`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
pytest.importorskip('srwl_bl')

from pykern import pkresource
from pykern import pkunit


# Epsilon
_EPS = 1e-3


@pytest.fixture(scope='module')
def zip_file():
    import sirepo
    return pkresource.filename('static/dat/magnetic_measurements.zip', sirepo)


def test_find_tab_undulator_length_1(zip_file):
    from sirepo.template import srw
    gap = 6.82
    res = srw._find_tab_undulator_length(zip_file=zip_file, gap=gap)
    assert res['dat_file'] == 'ivu21_srx_g6_8c.dat'
    assert res['closest_gap'] == 6.8
    assert abs(res['found_length'] - 2.5) < _EPS


def test_find_tab_undulator_length_1s(zip_file):
    from sirepo.template import srw
    gap = '6.82'
    res = srw._find_tab_undulator_length(zip_file=zip_file, gap=gap)
    assert res['dat_file'] == 'ivu21_srx_g6_8c.dat'
    assert res['closest_gap'] == 6.8
    assert abs(res['found_length'] - 2.5) < _EPS


def test_find_tab_undulator_length_2(zip_file):
    from sirepo.template import srw
    gap = 3
    res = srw._find_tab_undulator_length(zip_file=zip_file, gap=gap)
    assert res['dat_file'] == 'ivu21_srx_g6_2c.dat'
    assert res['closest_gap'] == 6.2
    assert abs(res['found_length'] - 2.5) < _EPS


def test_find_tab_undulator_length_3(zip_file):
    from sirepo.template import srw
    gap = 45
    res = srw._find_tab_undulator_length(zip_file=zip_file, gap=gap)
    assert res['dat_file'] == 'ivu21_srx_g40_0c.dat'
    assert res['closest_gap'] == 40
    assert abs(res['found_length'] - 2.5) < _EPS


def test_prepare_aux_files_1():
    from sirepo.template import srw
    data = {
        'models': {
            'simulation': {
                'sourceType': 't'
            },
            'tabulatedUndulator': {
                'magneticFile': 'magnetic_measurements.zip',
                'indexFile': '',
                'magnMeasFolder': '',
            }
        }
    }
    srw.prepare_aux_files(pkunit.empty_work_dir(), data)
    assert data['models']['tabulatedUndulator']['magnMeasFolder'] == ''
    assert data['models']['tabulatedUndulator']['indexFile'] == 'ivu21_srx_sum.txt'
