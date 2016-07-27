# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.srw.py`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from sirepo.template.srw import prepare_aux_files, _find_tab_undulator_length
import pytest
import py.path
import tempfile

_EPS = 1e-3


def test_find_tab_undulator_length_1():
    tmp_dir, data = _prepare_env()
    index_file = py.path.local.join(
        tmp_dir,
        data['models']['tabulatedUndulator']['indexFile']
    )
    gap = 6.82
    tab_parameters = _find_tab_undulator_length(index_file=index_file, gap=gap)
    _clean_env(tmp_dir)

    assert tab_parameters['dat_file'] == 'ivu21_srx_g6_8c.dat'
    assert tab_parameters['closest_gap'] == 6.8
    assert abs(tab_parameters['found_length'] - 2.5) < _EPS


def test_find_tab_undulator_length_1s():
    tmp_dir, data = _prepare_env()
    index_file = py.path.local.join(
        tmp_dir,
        data['models']['tabulatedUndulator']['indexFile']
    )
    gap = '6.82'
    tab_parameters = _find_tab_undulator_length(index_file=index_file, gap=gap)
    _clean_env(tmp_dir)

    assert tab_parameters['dat_file'] == 'ivu21_srx_g6_8c.dat'
    assert tab_parameters['closest_gap'] == 6.8
    assert abs(tab_parameters['found_length'] - 2.5) < _EPS


def test_find_tab_undulator_length_2():
    tmp_dir, data = _prepare_env()
    index_file = py.path.local.join(
        tmp_dir,
        data['models']['tabulatedUndulator']['indexFile']
    )
    gap = 3
    tab_parameters = _find_tab_undulator_length(index_file=index_file, gap=gap)
    _clean_env(tmp_dir)

    assert tab_parameters['dat_file'] == 'ivu21_srx_g6_2c.dat'
    assert tab_parameters['closest_gap'] == 6.2
    assert abs(tab_parameters['found_length'] - 2.5) < _EPS


def test_find_tab_undulator_length_3():
    tmp_dir, data = _prepare_env()
    index_file = py.path.local.join(
        tmp_dir,
        data['models']['tabulatedUndulator']['indexFile']
    )
    gap = 45
    tab_parameters = _find_tab_undulator_length(index_file=index_file, gap=gap)
    _clean_env(tmp_dir)

    assert tab_parameters['dat_file'] == 'ivu21_srx_g40_0c.dat'
    assert tab_parameters['closest_gap'] == 40
    assert abs(tab_parameters['found_length'] - 2.5) < _EPS


def _clean_env(tmp_dir):
    try:
        tmp_dir.remove(ignore_errors=True)
    except:
        pass


def _prepare_env():
    tmp_dir = py.path.local(tempfile.mkdtemp())

    data = {
        'models': {
            'simulation': {
                'sourceType': 't'
            },
            'tabulatedUndulator': {
                'magneticFile': 'magnetic_measurements.zip',
                'indexFile': '',
                'magnMeasFolder': '',
                'gap': 0,
                'length': 0,
            },
            'undulator': {
                'length': 0
            }
        }
    }
    prepare_aux_files(tmp_dir, data)
    return tmp_dir, data
