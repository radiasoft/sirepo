"""Wrapper around databroker

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import databroker


class _Metadata:
    def __init__(self, scan, catalog_name):
        self._metadata = scan.metadata
        self.catalog_name = catalog_name
        self.uid = self.get_start_field("uid")

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
        return self.uid.split("-")[0]


def catalog(name):
    return databroker.catalog[name]


def catalogs():
    return [str(s) for s in databroker.catalog.keys()]


def get_metadata(scan_or_uid, catalog_name):
    if isinstance(scan_or_uid, str):
        return _Metadata(catalog(catalog_name)[scan_or_uid], catalog_name)
    return _Metadata(scan_or_uid, catalog_name)


def get_metadata_for_most_recent_scan(catalog_name):
    return get_metadata(catalog(catalog_name)[-1], catalog_name)
