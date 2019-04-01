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
