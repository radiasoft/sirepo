"""Front-end command line for :mod:`sirepo_test_package_path`.

See :mod:`pykern.pkcli` for how this module is used.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcli
import sys


def main():
    return pkcli.main('sirepo_test_package_path')


if __name__ == '__main__':
    sys.exit(main())
