"""Wrapper around databroker

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import databroker

_CACHED_CATALOGS = PKDict()


class _Metadata:
    def __init__(self, scan, catalog_name):
        self._metadata = scan.metadata
        self.catalog_name = catalog_name
        self.rduid = self.get_start_field("uid")

    def get_start_field(self, name, unchecked=False):
        if unchecked:
            return self._metadata["start"].get(name)
        return self._metadata["start"][name]

    def get_start_fields(self):
        return list(self._metadata["start"].keys())

    def is_scan_plan_executing(self):
        return "stop" not in self._metadata

    def start(self):
        return self.get_start_field("time")

    def stop(self):
        # TODO(e-carlin): Catalogs unpacked with mongo_normalized don't have a stop time.
        #  Just include all of them for now.
        if not isinstance(self._metadata["stop"], dict):
            return 0
        return self._metadata["stop"]["time"] if "stop" in self._metadata else "N/A"

    def suid(self):
        return self.rduid.split("-")[0]


def catalog(name):
    # each call to databroker.catalog[name] create a new pymongo.MongoClient
    # so keep a catalog cache

    # the cached connection could timeout eventually, but the scan_monitor service
    # is polling for new scans, which should keep it active

    if name not in _CACHED_CATALOGS:
        _CACHED_CATALOGS[name] = databroker.catalog[name]
    return _CACHED_CATALOGS[name]


def catalogs():
    return [str(s) for s in databroker.catalog.keys()]


def get_metadata(scan_or_rduid, catalog_name):
    if isinstance(scan_or_rduid, str):
        return _Metadata(catalog(catalog_name)[scan_or_rduid], catalog_name)
    return _Metadata(scan_or_rduid, catalog_name)


def get_metadata_for_most_recent_scan(catalog_name):
    return get_metadata(catalog(catalog_name)[-1], catalog_name)
