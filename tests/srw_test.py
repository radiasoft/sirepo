# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.srw.py`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from sirepo.template.srw import prepare_aux_files, _find_tab_undulator_length
import os
import py.path
import tempfile

_EPS = 1e-3
zip_file = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../sirepo/package_data/static/dat/magnetic_measurements.zip',
    )
)


def test_find_tab_undulator_length_1():
    gap = 6.82
    tab_parameters = _find_tab_undulator_length(zip_file=zip_file, gap=gap)

    assert tab_parameters['dat_file'] == 'ivu21_srx_g6_8c.dat'
    assert tab_parameters['closest_gap'] == 6.8
    assert abs(tab_parameters['found_length'] - 2.5) < _EPS


def test_find_tab_undulator_length_1s():
    gap = '6.82'
    tab_parameters = _find_tab_undulator_length(zip_file=zip_file, gap=gap)

    assert tab_parameters['dat_file'] == 'ivu21_srx_g6_8c.dat'
    assert tab_parameters['closest_gap'] == 6.8
    assert abs(tab_parameters['found_length'] - 2.5) < _EPS


def test_find_tab_undulator_length_2():
    gap = 3
    tab_parameters = _find_tab_undulator_length(zip_file=zip_file, gap=gap)

    assert tab_parameters['dat_file'] == 'ivu21_srx_g6_2c.dat'
    assert tab_parameters['closest_gap'] == 6.2
    assert abs(tab_parameters['found_length'] - 2.5) < _EPS


def test_find_tab_undulator_length_3():
    gap = 45
    tab_parameters = _find_tab_undulator_length(zip_file=zip_file, gap=gap)

    assert tab_parameters['dat_file'] == 'ivu21_srx_g40_0c.dat'
    assert tab_parameters['closest_gap'] == 40
    assert abs(tab_parameters['found_length'] - 2.5) < _EPS


def test_prepare_aux_files_1():
    tmp_dir = _prepare_env()
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
    prepare_aux_files(tmp_dir, data)
    _clean_env(tmp_dir)

    assert data['models']['tabulatedUndulator']['magnMeasFolder'] == ''
    assert data['models']['tabulatedUndulator']['indexFile'] == 'ivu21_srx_sum.txt'


def _clean_env(tmp_dir):
    try:
        tmp_dir.remove(ignore_errors=True)
    except:
        pass


def _prepare_env():
    return py.path.local(tempfile.mkdtemp())
