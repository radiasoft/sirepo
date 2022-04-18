# -*- coding: utf-8 -*-
"""CLI for genesis

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdp, pkdlog
from sirepo.template import template_common


def run_background(cfg_dir):
    # TODO(e-carlin): use the mpi version of genesis?
    template_common.exec_parameters()
