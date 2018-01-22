# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.importer`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkresource
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
import pytest
pytest.importorskip('srwl_bl')

def test_magnetic_measurements_zip_file():
    from sirepo.template import srw

    m = srw.MagnMeasZip(pkresource.filename('template/srw/magnetic_measurements.zip', srw))
    assert m.index_dir == ''
    assert m.index_file == 'ivu21_srx_sum.txt'
    assert m.find_closest_gap('6.72') == 2.500648
    assert m.find_closest_gap('8.4') == 2.500648
    assert 'ivu21_srx_g6_2c.dat' in m.dat_files

    m = srw.MagnMeasZip(pkresource.filename('template/srw/magn_meas_fmx.zip', srw))
    assert m.index_dir == 'magn_meas'
    assert m.index_file == 'ivu21_fmx_sum.txt'
    assert m.find_closest_gap('6.7') == 2.500384
    assert m.find_closest_gap('8.4') == 2.501031
    assert 'ivu21_fmx_g7_7c.dat' in m.dat_files
