# -*- coding: utf-8 -*-
u"""Run SRW

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open
from pykern.pkdebug import pkdc, pkdp


def run():
    """Run srw in current directory"""
    from sirepo import run_srw
    run_srw.main()
