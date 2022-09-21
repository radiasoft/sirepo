# -*- coding: utf-8 -*-
"""Raydata execution template.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat, pkjson
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdformat, pkdexc
from sirepo.template import template_common
import base64
import databroker
import databroker.queries
import glob
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

_OUTPUT_FILE = "out.ipynb"

_BLUESKY_POLL_TIME_FILE = "bluesky-poll-time.txt"

# TODO(rorour): replace with actual scans
class ScanObject(PKDict):
    def __init__(self, uid=""):
        self.uid = uid
        self.metadata = {
            "field1": "val1",
            "num_points": "1",
            "start": {"time": "000", "uid": uid, "num_points": "2"},
            "stop": {"time": "001"},
        }


def analysis_job_output_files(data):
    def _filename_and_image(path):
        return PKDict(
            filename=path.basename,
            image=pkcompat.from_bytes(
                base64.b64encode(
                    pkio.read_binary(path),
                ),
            ),
        )

    def _paths():
        d = _dir_for_scan_uuid(_parse_scan_uuid(data))

        for f in glob.glob(str(d.join("/**/*.png")), recursive=True):
            yield pkio.py_path(f)

    return PKDict(data=[_filename_and_image(p) for p in _paths()])


def background_percent_complete(report, run_dir, is_running):
    return PKDict(percentComplete=0 if is_running else 100)


def catalog(scans_data_or_catalog_name):
    return databroker.catalog[
        scans_data_or_catalog_name.catalogName
        if isinstance(
            scans_data_or_catalog_name,
            PKDict,
        )
        else scans_data_or_catalog_name
    ]


def stateless_compute_catalog_names(data):
    return PKDict(
        data=PKDict(
            catalogs=[str(s) for s in databroker.catalog.keys()],
        )
    )


def stateless_compute_scans(data):
    # TODO(e-carlin): get scans from daemon
    l = []
    if data.scansStatus == "completed_scans":
        assert data.searchStartTime and data.searchStopTime, pkdformat(
            "must have both searchStartTime and searchStopTime data={}", data
        )
        l = [ScanObject("uid1"), ScanObject("uid2"), ScanObject("uid3")]
    elif data.scansStatus == "queued_scans":
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
        s.append(_scan_info(v.uid, data))
    return _scan_info_result(s)


def stateless_compute_scan_fields(data):
    return PKDict(columns=list(catalog(data)[-1].metadata["start"].keys()))


def stateless_compute_scan_info(data):
    return _scan_info_result([_scan_info(s, data) for s in data.scans])


def write_parameters(data, run_dir, is_parallel):
    raise NotImplementedError("Raydata does not run simulations")


def _dir_for_scan_uuid(scan_uuid):
    return sirepo.feature_config.for_sim_type(SIM_TYPE).data_dir.join(
        sirepo.util.safe_path(scan_uuid),
    )


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


def _scan_info(scan_uuid, scans_data):
    def _get_start(metadata):
        return metadata["start"]["time"]

    def _get_stop(metadata):
        return metadata["stop"]["time"]

    def _get_suid(metadata):
        return _suid(metadata["start"]["uid"])

    m = catalog(scans_data)[scan_uuid].metadata
    # POSIT: uid is no displayed but all of the code expects uid field to exist
    d = PKDict(uid=scan_uuid)
    for c in _DEFAULT_COLUMNS:
        d[c] = locals()[f"_get_{c}"](m)

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


def _parse_scan_uuid(data):
    return data.report


def _suid(scan_uuid):
    return scan_uuid.split("-")[0]
