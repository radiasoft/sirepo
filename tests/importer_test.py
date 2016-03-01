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

from sirepo.importer import import_python

def test_sirepo_parser():
    with pkunit.save_chdir_work():
        for b in ['SRWLIB_VirtBL_LCLS_SXR_01']:
            base_py = '{}.py'.format(b)
            code = pkio.read_text(pkunit.data_dir().join(base_py))
            error, actual = import_python(
                code,
                tmp_dir='.',
                lib_dir='.',
                user_filename=r'c:\x\{}.y'.format('SRWLIB_VirtBL_LCLS_SXR_01'),
            )
            assert not error, \
                '{}: should be valid input'.format(base_py)
            pkunit.assert_object_with_json(b, actual)
