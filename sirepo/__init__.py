# -*- coding: utf-8 -*-
u"""sirepo package

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pkg_resources

try:
    # We only have a version once the package is installed.
    #TODO(pjm): this needs to get fixed
    #__version__ = pkg_resources.get_distribution('pykern').version
    __version__ = '20181022.000000'
except pkg_resources.DistributionNotFound:
    pass
