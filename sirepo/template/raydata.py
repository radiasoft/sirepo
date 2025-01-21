# -*- coding: utf-8 -*-
"""Raydata execution template.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdformat, pkdexc
from sirepo.template import template_common
import pygments
import pygments.formatters
import pygments.lexers
import re
import requests
import requests.exceptions
import sirepo.feature_config
import sirepo.sim_data
import sirepo.tornado
import sirepo.util

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def new_simulation(data, new_simulation_data, qcall, **kwargs):
    data.models.catalog.catalogName = new_simulation_data.catalogNamePicker


def stateless_compute_analysis_output(data, **kwargs):
    return _request_scan_monitor(PKDict(method="analysis_output", data=data))


def stateless_compute_analysis_run_log(data, **kwargs):
    def _filter_log(log):
        for f in ("Ending Cell.*\n", "Executing Cell.*\n"):
            log = re.sub(f, "", log)
        return log

    def _log_to_html(log):
        return pygments.highlight(
            log,
            pygments.lexers.get_lexer_by_name("text"),
            pygments.formatters.HtmlFormatter(
                noclasses=False,
                linenos=False,
            ),
        )

    r = _request_scan_monitor(PKDict(method="analysis_run_log", data=data))
    r.run_log = _log_to_html(_filter_log(r.run_log))
    return r


def stateless_compute_catalog_names(data, **kwargs):
    return _request_scan_monitor(PKDict(method="catalog_names", data=data))


def stateless_compute_download_analysis_pdfs(data, data_file_uri=None, **kwargs):
    assert data_file_uri, f"expected data_file_uri={data_file_uri}"
    data.args.dataFileUri = data_file_uri
    return _request_scan_monitor(PKDict(method="download_analysis_pdfs", data=data))


def stateless_compute_get_automatic_analysis(data, **kwargs):
    return _request_scan_monitor(PKDict(method="get_automatic_analysis", data=data))


def stateless_compute_reorder_scan(data, **kwargs):
    return _request_scan_monitor(PKDict(method="reorder_scan", data=data))


def stateless_compute_run_analysis(data, **kwargs):
    return _request_scan_monitor(PKDict(method="run_analysis", data=data))


def stateless_compute_scans(data, **kwargs):
    return _request_scan_monitor(PKDict(method="get_scans", data=data))


def stateless_compute_scan_fields(data, **kwargs):
    return _request_scan_monitor(PKDict(method="scan_fields", data=data))


def stateless_compute_set_automatic_analysis(data, **kwargs):
    return _request_scan_monitor(PKDict(method="set_automatic_analysis", data=data))


def _request_scan_monitor(data):
    c = sirepo.feature_config.for_sim_type(SIM_TYPE)
    try:
        r = requests.post(
            c.scan_monitor_url,
            json=data,
            headers=sirepo.tornado.AuthHeaderRequestHandler.get_header(
                c.scan_monitor_api_secret
            ),
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
