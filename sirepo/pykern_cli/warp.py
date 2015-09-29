# -*- coding: utf-8 -*-
"""Wrapper to run SRW from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import json

from pykern import pkio

def run(cfg_dir):
    """Run srw in ``cfg_dir``

    The files in ``cfg_dir`` must be configured properly.

    Args:
        cfg_dir (str): directory to run srw in
    """
    with pkio.save_chdir(cfg_dir):
        _run_warp()


def _run_warp():
    with open('/home/vagrant/tmp/in.json', 'r') as infile:
        info = json.load(infile)
    with open('out.json', 'w') as outfile:
        json.dump(info, outfile)
