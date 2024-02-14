# -*- coding: utf-8 -*-
"""CLI for raydata

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.raydata.scans
import sirepo.raydata.replay
import sirepo.raydata.scan_monitor


def create_scans(num_scans, catalog_name, delay=True):
    sirepo.raydata.scans.create(num_scans, catalog_name, delay)


def replay(source_catalog, destination_catalog, num_scans):
    sirepo.raydata.replay.begin(source_catalog, destination_catalog, num_scans)


def run(cfg_dir):
    import sirepo.template.raydata

    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data.report == "scansReport":
        res = sirepo.template.raydata._request_scan_monitor(
            PKDict(method="get_scans", data=data.models.scansReport)
        )
    else:
        raise AssertionError("unknown report: {}".format(data.report))
    template_common.write_sequential_result(res)


def run_background(cfg_dir):
    _run()


def scan_monitor():
    sirepo.raydata.scan_monitor.start()


def _run():
    template_common.exec_parameters()
