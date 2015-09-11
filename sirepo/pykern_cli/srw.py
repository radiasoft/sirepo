# -*- coding: utf-8 -*-
"""Wrapper to run SRW from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from pykern import pkio
from pykern.pkdebug import pkdc, pkdp


def run(cfg_dir):
    """Run srw in ``cfg_dir``

    The files in ``cfg_dir`` must be configured properly.

    Args:
        cfg_dir (str): directory to run srw in
    """
    from sirepo import run_srw
    with pkio.save_chdir(cfg_dir):
        run_srw.main()
