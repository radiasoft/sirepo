"""Sirepo front-end command line for :mod:`pykern.pkcli`.

Example:

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import sys
from pykern import pkcli


def main():
    return pkcli.main("sirepo")


if __name__ == "__main__":
    sys.exit(main())
