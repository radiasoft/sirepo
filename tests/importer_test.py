# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.importer`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern.pkdebug import pkdc, pkdp
import py
import pytest
import re
from pykern import pkunit
from pykern import pkio

from sirepo.importer import python_to_json

def test_sirepo_parser():
    with pkunit.save_chdir_work():
        for b in ['SRWLIB_VirtBL_LCLS_SXR_01']:
            base_py = '{}.py'.format(b)
            in_py = py.path.local(base_py)
            pkunit.data_dir().join(base_py).copy(in_py)
            actual = python_to_json(in_py)
            actual = re.sub(r'Imported file[^"]+', 'IGNORE-VALUE', actual)
            actual_json = pkio.write_text('out.json', actual)
            expect_json = pkunit.data_dir().join('{}.json'.format(b))
            expect = pkio.read_text(expect_json)
            assert expect == actual, \
                '{} should match expected {}'.format(actual_json, expect_json)
