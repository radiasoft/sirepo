# -*- coding: utf-8 -*-
"""Wrapper to run omega from the command line.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp, pkdc, pkdlog
import sirepo.mpi
import sirepo.template.omega as template


def run(cfg_dir):
    r = template_common.exec_parameters()
