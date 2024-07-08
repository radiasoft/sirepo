"""Front-end command line for :mod:`sirepo`.

See :mod:`pykern.pkcli` for how this module is used.

:copyright: Copyright (c) 2015-2024 RadiaSoft LLC.  All Rights Reserved.
:license: https://www.apache.org/licenses/LICENSE-2.0.html
"""

import pykern.pkcli
import sys


def main():
    return pykern.pkcli.main("sirepo")


if __name__ == "__main__":
    sys.exit(main())
