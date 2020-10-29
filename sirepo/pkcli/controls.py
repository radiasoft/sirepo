# -*- coding: utf-8 -*-
"""Wrapper to run controls code from the command line.

Under the covers the controls app calls MAD-X

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import sirepo.pkcli.madx


def run_background(cfg_dir):
    sirepo.pkcli.madx.run_background(cfg_dir)
