# -*- coding: utf-8 -*-
u"""SiRepo front-end command line for :mod:`pykern.pkcli`.

Example:

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import sys

from pykern import pkcli


def main():
    # TODO(e-carlin): create context here
    return pkcli.main('sirepo')


if __name__ == '__main__':
    sys.exit(main())
