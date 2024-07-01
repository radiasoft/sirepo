""":mod:`sirepo` package

:copyright: Copyright (c) 2018-2024 RadiaSoft LLC..  All Rights Reserved.
:license: https://www.apache.org/licenses/LICENSE-2.0.html
"""

import pkg_resources

try:
    # We only have a version once the package is installed.
    __version__ = pkg_resources.get_distribution("sirepo").version
except pkg_resources.DistributionNotFound:
    pass
