""":mod:`sirepo` package

:copyright: Copyright (c) 2018-2024 RadiaSoft LLC..  All Rights Reserved.
:license: https://www.apache.org/licenses/LICENSE-2.0.html
"""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("sirepo")
except importlib.metadata.PackageNotFoundError:
    # We only have a version once the package is installed.
    pass
