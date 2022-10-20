# -*- coding: utf-8 -*-
"""CLI for raydata

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo.template import template_common


def run(cfg_dir):
    _run()
    template_common.write_sequential_result(PKDict())


def run_background(cfg_dir):
    _run()


def _run():
    template_common.exec_parameters()
