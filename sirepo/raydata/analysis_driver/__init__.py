from pykern import pkcompat
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import base64
import importlib
import sirepo.raydata.scan_monitor

_ANALYSIS_DRIVERS = PKDict()


class AnalysisDriverBase(PKDict):
    def __init__(self, uid, catalog_name, *args, **kwargs):
        super().__init__(*args, uid=uid, catalog_name=catalog_name, **kwargs)

    def get_analysis_pdfs(self):
        def _is_safe_name(uid):
            # UUIDs don't have any specials (ex ../) so checking that the
            # value is in fact a uuid also checks that it is safe.
            try:
                uuid.UUID(str(uid))
                return True
            except ValueError:
                return False

        def _all_pdfs(uids):
            for u in uids:
                p = _analysis_pdf_paths(u)
                if not p:
                    raise FileNotFoundError(f"no analysis pdfs found for uid={u}")
                yield u, p

        for u in req_data.uids:
            assert _is_safe_name(u), f"invalid uid={u}"
        with io.BytesIO() as t:
            with zipfile.ZipFile(t, "w") as f:
                for u, v in _all_pdfs(req_data.uids):
                    for p in v:
                        f.write(p, pkio.py_path(f"/uids/{u}").join(p.basename))
            t.seek(0)
            requests.put(
                req_data.dataFileUri + "analysis_pdfs.zip",
                data=t.getbuffer(),
                verify=not pkconfig.channel_in("dev"),
            ).raise_for_status()
            return PKDict()

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
        return sirepo.raydata.scan_monitor.cfg.db_dir.join(self.uid)

    def get_run_log(self):
        p = self.get_output_dir().join("run.log")
        return PKDict(
            log_path=str(p),
            run_log=pkio.read_text(p) if p.exists() else "",
        )


def get(uid, catalog_name, **kwargs):
    return _ANALYSIS_DRIVERS[catalog_name](uid, catalog_name)


def init(catalog_names):
    assert (
        not _ANALYSIS_DRIVERS
    ), "Module already initialized _ANALYSIS_DRIVERS={_ANALYSIS_DRIVERS}"
    for n in catalog_names:
        _ANALYSIS_DRIVERS[n] = getattr(
            importlib.import_module(f"sirepo.raydata.analysis_driver.{n}"),
            n.upper(),
        )
