# -*- coding: utf-8 -*-
u""":mod:`sirepo_test_package_path` package

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pkg_resources

try:
    # We only have a version once the package is installed.
    __version__ = pkg_resources.get_distribution('sirepo_test_package_path').version
except pkg_resources.DistributionNotFound:
    pass
