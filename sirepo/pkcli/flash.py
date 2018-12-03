# -*- coding: utf-8 -*-
"""Wrapper to run FLASH from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import py.path
import sirepo.template.flash as template
import subprocess

_EXE_PATH = '/home/vagrant/src/FLASH4.5/object/flash4'

def run_background(cfg_dir):
    res = {}
    with pkio.save_chdir(cfg_dir):
        #subprocess.call([_EXE_PATH])
        mpi.run_program([_EXE_PATH])
    simulation_db.write_result(res)
