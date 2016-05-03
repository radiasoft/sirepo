# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.importer`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkresource
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp
import glob
import py
import pytest
import shutil
import uuid

pytest.importorskip('srwl_bl')

_ROOT_DIR = py.path.local()
_DAT_DIR = _ROOT_DIR.join('sirepo/package_data/static/dat')
_TESTS = {  # Values are optional arguments:
    'lcls_sxr': ('lcls_sxr', None),
    'chx': ('chx', None),
    'lcls_simplified': ('lcls_simplified', None),
    'srx': ('srx', None),
    'srx_bl2': ('srx', '--op_BL=2'),
    'srx_bl3': ('srx', '--op_BL=3'),
    'srx_bl4': ('srx', '--op_BL=4'),
    'amx': ('amx', None),
    'amx_bl2': ('amx', '--op_BL=2'),
    'amx_bl3': ('amx', '--op_BL=3'),
    'amx_bl4': ('amx', '--op_BL=4'),
}


def _create_tmp_dir():
    tmp_dir = py.path.local('/tmp').join(str(uuid.uuid4()))
    _remove_dir(tmp_dir)
    tmp_dir.mkdir()
    for f in glob.glob(str(_DAT_DIR.join('mirror_*d.dat'))):
        shutil.copy2(f, str(tmp_dir))
    return tmp_dir


def _remove_dir(tmp_dir):
    try:
        tmp_dir.remove(ignore_errors=True)
    except:
        pass


def test_importer():
    from sirepo.importer import import_python
    with pkunit.save_chdir_work():
        for b in sorted(_TESTS.keys()):
            base_py = '{}.py'.format(_TESTS[b][0])
            code = pkio.read_text(pkunit.data_dir().join(base_py))
            tmp_dir = _create_tmp_dir()
            error, actual = import_python(
                code,
                tmp_dir='.',
                lib_dir=str(tmp_dir),
                user_filename=r'c:\anything\{}.anysuffix'.format(_TESTS[b][0]),
                arguments=_TESTS[b][1],
            )
            _remove_dir(tmp_dir)
            assert not error, \
                '{}: should import with an error: {}'.format(base_py, error)
            actual['version'] = 'IGNORE-VALUE'
            assert not error, \
                '{}: should be valid input'.format(base_py)
            pkunit.assert_object_with_json(b, actual)
