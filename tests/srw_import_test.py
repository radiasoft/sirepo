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

pytest.importorskip('srwl_bl')

_TESTS = {  # Values are optional arguments:
    'amx': ('amx', None),
    'amx_bl2': ('amx', '--op_BL=2'),
    'amx_bl3': ('amx', '--op_BL=3'),
    'amx_bl4': ('amx', '--op_BL=4'),
    'chx': ('chx', None),
    'chx_fiber': ('chx_fiber', None),
    'exported_chx': ('exported_chx', None),
    'exported_gaussian_beam': ('exported_gaussian_beam', None),
    'exported_undulator_radiation': ('exported_undulator_radiation', None),
    'lcls_simplified': ('lcls_simplified', None),
    'lcls_sxr': ('lcls_sxr', None),
    'sample_from_image': ('sample_from_image', None),
    'smi_es1_bump_norm': ('smi', '--beamline ES1 --bump --BMmode Norm'),
    'smi_es1_nobump': ('smi', '--beamline ES1'),
    'smi_es2_bump_lowdiv': ('smi', '--beamline ES2 --bump --BMmode LowDiv'),
    'smi_es2_bump_norm': ('smi', '--beamline ES2 --bump --BMmode Norm'),
    'srx': ('srx', None),
    'srx_bl2': ('srx', '--op_BL=2'),
    'srx_bl3': ('srx', '--op_BL=3'),
    'srx_bl4': ('srx', '--op_BL=4'),
}


def test_importer():
    from sirepo.importer import import_python
    dat_dir = py.path.local(pkresource.filename('template/srw/', import_python))
    with pkunit.save_chdir_work():
        work_dir = py.path.local('.')
        for f in glob.glob(str(dat_dir.join('mirror_*d.dat'))):
            py.path.local(f).copy(work_dir)
        py.path.local(str(dat_dir.join('sample.tif'))).copy(work_dir)
        for b in sorted(_TESTS.keys()):
            base_py = '{}.py'.format(_TESTS[b][0])
            code = pkio.read_text(pkunit.data_dir().join(base_py))
            error, actual = import_python(
                code,
                tmp_dir=str(work_dir),
                lib_dir=str(work_dir),
                user_filename=r'c:\anything\{}.anysuffix'.format(_TESTS[b][0]),
                arguments=_TESTS[b][1],
            )
            assert not error, \
                '{}: should import with an error: {}'.format(base_py, error)
            actual['version'] = 'IGNORE-VALUE'
            assert not error, \
                '{}: should be valid input'.format(base_py)
            pkunit.assert_object_with_json(b, actual)
