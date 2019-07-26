# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.srw_importer`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

pytest.importorskip('srwl_bl')

def test_importer():
    from sirepo.template.srw_importer import import_python
    from pykern import pkio
    from pykern import pkresource
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp
    import glob
    import py
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
        'nsls-ii-esm-beamline': ('nsls-ii-esm-beamline', None),
    }

    dat_dir = py.path.local(pkresource.filename('template/srw/', import_python))
    with pkunit.save_chdir_work():
        for b in sorted(_TESTS.keys()):
            base_py = '{}.py'.format(_TESTS[b][0])
            code = pkio.read_text(pkunit.data_dir().join(base_py))
            actual = import_python(
                code,
                tmp_dir='.',
                lib_dir=str(dat_dir),
                user_filename=r'c:\anything\{}.anysuffix'.format(_TESTS[b][0]),
                arguments=_TESTS[b][1],
            )
            actual['version'] = 'IGNORE-VALUE'
            pkunit.assert_object_with_json(b, actual)
