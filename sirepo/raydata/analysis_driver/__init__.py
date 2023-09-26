"""Operations for running analysis of a scan

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import base64
import copy
import importlib
import sirepo.raydata.databroker
import uuid

_ANALYSIS_DRIVERS = PKDict()


class AnalysisDriverBase(PKDict):
    def __init__(self, catalog_name, uid, *args, **kwargs):
        super().__init__(catalog_name=catalog_name, uid=uid, *args, **kwargs)
        self._scan_metadata = sirepo.raydata.databroker.get_metadata(uid, catalog_name)

    def get_analysis_pdf_paths(self):
        return pkio.walk_tree(self.get_output_dir(), r".*\.pdf$")

    def get_notebooks(self, *args, **kwargs):
        raise NotImplementedError("children must implement this method")

    def get_output(self):
        res = PKDict()
        for e in [
            PKDict(
                name="images",
                file_type="png",
                op=lambda path: pkcompat.from_bytes(
                    base64.b64encode(
                        pkio.read_binary(path),
                    ),
                ),
            ),
            PKDict(
                name="jsonFiles",
                file_type="json",
                op=pkjson.load_any,
            ),
        ]:
            res[e.name] = [
                PKDict(filename=p.basename, data=e.op(p))
                for p in pkio.sorted_glob(
                    self.get_output_dir().join(f"**/*.{e.file_type}")
                )
            ]
        return res

    def get_output_dir(self):
        raise NotImplementedError("children must implement this method")

    def get_papermill_args(self):
        res = []
        for n, v in [
            ["uid", self.uid],
            ["scan", self.uid],
            *self._get_papermill_args(),
        ]:
            res.extend(["-p", n, str(v)])
        res.append("--report-mode")
        return res

    def get_run_log(self):
        p = self.get_output_dir().join("run.log")
        return PKDict(
            log_path=str(p),
            run_log=pkio.read_text(p) if p.exists() else "",
        )

    def has_analysis_pdfs(self):
        return len(self.get_analysis_pdf_paths()) > 0

    def _get_papermill_args(self, *args, **kwargs):
        return []


def get(incoming):
    def _verify_uid(uid):
        # uid will be combined with paths throughout the application.
        # So, verify that uid is actually a UUID from the start.
        # UUIDs don't have any specials (ex ../) so checking that the
        # value is in fact a uuid also checks that it is safe.
        return str(uuid.UUID(uid))

    i = copy.deepcopy(incoming)
    c = i.pkdel("catalogName" if "catalogName" in i else "catalog_name")
    u = _verify_uid(i.pkdel("uid"))
    return _ANALYSIS_DRIVERS[c](catalog_name=c, uid=u, data=i)


def init(catalog_names):
    assert (
        not _ANALYSIS_DRIVERS
    ), "Module already initialized _ANALYSIS_DRIVERS={_ANALYSIS_DRIVERS}"
    for n in catalog_names:
        _ANALYSIS_DRIVERS[n] = getattr(
            importlib.import_module(f"sirepo.raydata.analysis_driver.{n}"),
            n.upper(),
        )
