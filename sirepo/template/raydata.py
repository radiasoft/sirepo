# -*- coding: utf-8 -*-
"""Raydata execution template.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdformat, pkdexc
import databroker
import databroker.queries
import requests
import requests.exceptions
import sirepo.feature_config
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.srdb
import sirepo.util


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_DEFAULT_COLUMNS = ["start", "stop", "suid"]

# TODO(e-carlin): tune this number
_MAX_NUM_SCANS = 1000

_NON_DISPLAY_SCAN_FIELDS = "uid"


def catalog(scans_data_or_catalog_name):
    return databroker.catalog[
        scans_data_or_catalog_name.catalogName
        if isinstance(
            scans_data_or_catalog_name,
            PKDict,
        )
        else scans_data_or_catalog_name
    ]


def stateless_compute_analysis_output(data):
    return _request_scan_monitor(PKDict(method="analysis_output", uid=data.uid))


def stateless_compute_catalog_names(data):
    return PKDict(
        data=PKDict(
            catalogs=[str(s) for s in databroker.catalog.keys()],
        )
    )


def stateless_compute_scans(data):
    if data.analysisStatus == "executed":
        assert data.searchStartTime and data.searchStopTime, pkdformat(
            "must have both searchStartTime and searchStopTime data={}", data
        )
        l = []
        c = catalog(data)
        for s in _request_scan_monitor(
            PKDict(method="executed_analyses", catalog_name=data.catalogName)
        ).scans:
            m = c[s.uid].metadata
            if (
                m["start"]["time"] >= data.searchStartTime
                and m["stop"]["time"] <= data.searchStopTime
            ):
                l.append(s)
    elif data.analysisStatus == "queued":
        l = _request_scan_monitor(
            PKDict(method="queued_analyses", catalog_name=data.catalogName)
        ).scans
    else:
        raise AssertionError("unrecognized scanStatus={data.scanStatus}")

    s = []
    for i, v in enumerate(l):
        if i > _MAX_NUM_SCANS:
            raise sirepo.util.UserAlert(
                f"More than {_MAX_NUM_SCANS} scans found. Please reduce your query.",
            )
        s.append(_scan_info(v.uid, data, status=v.status))
    return _scan_info_result(s)


def stateless_compute_scan_fields(data):
    return PKDict(columns=list(catalog(data)[-1].metadata["start"].keys()))


def stateless_compute_scan_info(data):
    return _scan_info_result([_scan_info(s, data) for s in data.scans])


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


def _scan_info(scan_uuid, scans_data, status=None):
    m = catalog(scans_data)[scan_uuid].metadata
    # POSIT: uid is no displayed but all of the code expects uid field to exist
    d = PKDict(uid=scan_uuid, status=status)
    for c in _DEFAULT_COLUMNS:
        d[c] = PKDict(
            start=lambda metadata: metadata["start"]["time"],
            stop=lambda metadata: metadata["stop"]["time"],
            suid=lambda metadata: _suid(metadata["start"]["uid"]),
        )[c](m)

    for c in scans_data.get("selectedColumns", []):
        d[c] = m["start"].get(c)
    return d


def _scan_info_result(scans):
    return PKDict(
        data=PKDict(
            scans=sorted(scans, key=lambda e: e.start),
            cols=[k for k in scans[0].keys() if k not in _NON_DISPLAY_SCAN_FIELDS]
            if scans
            else [],
        )
    )


def _suid(scan_uuid):
    return scan_uuid.split("-")[0]
