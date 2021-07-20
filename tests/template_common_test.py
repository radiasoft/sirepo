# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.srw.py`

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import zipfile

from pykern import pkresource
from pykern import pkunit
from pykern.pkcollections import PKDict
from sirepo.template import template_common


def test_validate_safe_zip():
    from sirepo.template import srw

    zip_dir = str(pkunit.data_dir() + '/zip_dir')

    # Reject a zip that would overwrite files
    with pkunit.pkexcept(AssertionError):
        srw._validate_safe_zip(zip_dir + '/bad_zip_would_overwrite.zip', zip_dir)

    # Reject a zip that would extract a file above the target directory
    with pkunit.pkexcept(AssertionError):
        srw._validate_safe_zip(zip_dir + '/bad_zip_external_file.zip', zip_dir)

    # Reject a zip with unacceptably large file
    with pkunit.pkexcept(AssertionError):
        srw._validate_safe_zip(zip_dir + '/bad_zip_large_file.zip', zip_dir)

    # Reject a zip with executable permissions set
    with pkunit.pkexcept(AssertionError):
        srw._validate_safe_zip(zip_dir + '/bad_zip_executables.zip', zip_dir)

    # Finally, accept a zip file known to be safe
    srw._validate_safe_zip(zip_dir + '/good_zip.zip', zip_dir, srw.validate_magnet_data_file)


def test_dict_to_from_h5():
    from pykern import pkio
    import h5py

    # _TEST_DICT includes single-valued entries (str and int), an array,
    # and keys that evaluate to ints
    _TEST_DICT = PKDict(
        a_str='A',
        b_dict=PKDict(
            b_str='B',
            b_arr=[0, 1, 2]
        )
    )
    _TEST_DICT['999'] = '999'
    _TEST_DICT['998'] = 998
    _TEST_H5_FILE = 'test.h5'

    pkio.unchecked_remove(_TEST_H5_FILE)
    template_common.write_dict_to_h5(_TEST_DICT, _TEST_H5_FILE)
    d = None
    with h5py.File(_TEST_H5_FILE, 'r') as f:
        d = template_common.h5_to_dict(f)
    pkunit.pkeq(_TEST_DICT, d)
