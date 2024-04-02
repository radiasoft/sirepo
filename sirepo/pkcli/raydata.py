# -*- coding: utf-8 -*-
"""CLI for raydata

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from sirepo.template import template_common
import sirepo.raydata.scans
import sirepo.raydata.scan_monitor


def create_scans(num_scans, catalog_name, delay=True):
    sirepo.raydata.scans.create(num_scans, catalog_name, delay)


def run(cfg_dir):
    _run()
    template_common.write_sequential_result(PKDict())


def run_background(cfg_dir):
    _run()


def scan_monitor():
    sirepo.raydata.scan_monitor.start()


def _run():
    template_common.exec_parameters()
