# -*- coding: utf-8 -*-
"""Raydata execution template.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdformat, pkdexc
import requests
import requests.exceptions
import sirepo.feature_config
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.srdb
import sirepo.util


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def stateless_compute_analysis_output(data):
    return _request_scan_monitor(PKDict(method="analysis_output", uid=data.args.uid))


def stateless_compute_catalog_names(_):
    return _request_scan_monitor(PKDict(method="catalog_names"))


def stateless_compute_begin_replay(data):
    return PKDict(data=_request_scan_monitor(PKDict(method="begin_replay", data=data)))


def stateless_compute_scans(data):
    return _request_scan_monitor(PKDict(method="get_scans", data=data))


def stateless_compute_scan_fields(data):
    return _request_scan_monitor(PKDict(method="scan_fields", data=data))


def _request_scan_monitor(data):
    try:
        r = requests.post(
            sirepo.feature_config.for_sim_type(SIM_TYPE).scan_monitor_url,
            json=data,
        )
        r.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        raise sirepo.util.UserAlert(
            "Could not connect to scan monitor. Please contact an administrator.",
            "could not connect to scan monitor error={} stack={}",
            e,
            pkdexc(),
        )
    return pkjson.load_any(r.content)
