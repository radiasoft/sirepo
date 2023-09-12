# -*- coding: utf-8 -*-
"""ray data scan monitor

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern import pkasyncio
from pykern import pkcompat
from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdformat
import aenum
import asyncio
import base64
import databroker
import databroker.queries
import io
import math
import pymongo
import requests
import sirepo.feature_config
import sirepo.raydata
import sirepo.srdb
import sirepo.srtime
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import tornado.websocket
import uuid
import zipfile

#: task(s) monitoring the execution of the analysis process
_ANALYSIS_PROCESSOR_TASKS = None

#: task(s) monitoring catalogs for new scans
_CATALOG_MONITOR_TASKS = PKDict()

_DEFAULT_COLUMNS = PKDict(
    start="time",
    stop="time",
    suid="uid",
)

# TODO(e-carlin): tune this number
_MAX_NUM_SCANS = 1000

_NON_DISPLAY_SCAN_FIELDS = "uid"

_NUM_RECENTLY_EXECUTED_SCANS = 5

#: scan(s) awaiting analysis to be run on them
_SCANS_AWAITING_ANALYSIS = []

#: path scan_monitor registers to receive api requests
_URI = "/scan-monitor"

_cfg = None

engine = None


class _AnalysisStatus(aenum.NamedConstant):
    """Status of the analysis runs"""

    COMPLETED = "completed"
    ERROR = "error"
    PENDING = "pending"
    RUNNING = "running"
    NON_STOPPED = frozenset((PENDING, RUNNING))
    EXECUTED = frozenset((COMPLETED, ERROR))
    NONE = "none"


@sqlalchemy.ext.declarative.as_declarative()
class _DbBase:
    def save(self):
        self.last_updated = sirepo.srtime.utc_now()
        self.session.add(self)
        self.session.commit()


class _Analysis(_DbBase):
    __tablename__ = "analysis_t"
    uid = sqlalchemy.Column(sqlalchemy.String(36), nullable=False, primary_key=True)
    catalog_name = sqlalchemy.Column(
        sqlalchemy.String(20), nullable=False, primary_key=True
    )
    status = sqlalchemy.Column(sqlalchemy.String(20), nullable=False)
    last_updated = sqlalchemy.Column(
        sqlalchemy.DateTime(),
        nullable=False,
    )

    @classmethod
    def analysis_output_dir(cls, uid):
        return _cfg.db_dir.join(uid)

    @classmethod
    def get_recently_updated(cls, num_scans, catalog_name, statuses):
        r = []
        for x in (
            cls.session.query(cls)
            .filter(cls.status.in_(statuses))
            .filter(cls.catalog_name == catalog_name)
            .order_by(sqlalchemy.desc("last_updated"))
            .limit(num_scans)
        ):
            r.append(PKDict(uid=x.uid, status=x.status, catalog_name=catalog_name))
        return r

    @classmethod
    def have_analyzed_scan(cls, uid, catalog_name):
        return True if cls.search_by(uid=uid, catalog_name=catalog_name) else False

    @classmethod
    def init(cls, db_file):
        def _fixup_running_statuses():
            for x in cls.session.query(cls).filter(
                cls.status.in_(_AnalysisStatus.NON_STOPPED)
            ):
                cls.set_scan_status(
                    PKDict(uid=x.uid, catalog_name=x.catalog_name),
                    _AnalysisStatus.ERROR,
                )

        global engine
        if engine is None:
            engine = sqlalchemy.create_engine(f"sqlite:///{db_file}")
        cls.metadata.create_all(bind=engine)
        cls.session = sqlalchemy.orm.Session(bind=engine)
        _fixup_running_statuses()

    @classmethod
    def scans_with_status(cls, catalog_name, statuses):
        r = []
        for s in statuses:
            for x in cls.search_all_by(catalog_name=catalog_name, status=s):
                r.append(PKDict(uid=x.uid, status=x.status, catalog_name=catalog_name))
        return r

    @classmethod
    def search_all_by(cls, **kwargs):
        return cls.session.query(cls).filter_by(**kwargs).all()

    @classmethod
    def search_by(cls, **kwargs):
        return cls.session.query(cls).filter_by(**kwargs).first()

    @classmethod
    def set_scan_status(cls, analysis_queue_record, status):
        u = analysis_queue_record.uid
        c = analysis_queue_record.catalog_name
        r = cls.search_by(uid=u, catalog_name=c)
        if not r:
            cls(uid=u, catalog_name=c, status=status).save()
            return
        r.status = status
        r.save()

    @classmethod
    def statuses_for_scans(cls, catalog_name, uids):
        return (
            cls.session.query(cls.uid, cls.status)
            .filter(cls.catalog_name == catalog_name, cls.uid.in_(uids))
            .all()
        )


# TODO(e-carlin): copied from sirepo
# TODO(e-carlin): Since we are going to sockets for communication we should probably use them here.
# But, for now it is easier to just make a normal http request
class _JsonPostRequestHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", pkjson.CONTENT_TYPE)


class _Metadata:
    def __init__(self, scan):
        self.scan = scan
        self._metadata = self.scan.metadata

    def get_scan_field(self, name):
        return self._metadata["start"].get(name)

    def get_scan_fields(self):
        return list(self._metadata["start"].keys())

    def is_scan_plan_executing(self):
        return "stop" not in self._metadata

    def start(self):
        return self._metadata["start"]["time"]

    def stop(self):
        # TODO(e-carlin): Catalogs unpacked with mongo_normalized don't have a stop time.
        #  Just include all of them for now.
        if not isinstance(self._metadata["stop"], dict):
            return 0
        return self._metadata["stop"]["time"] if "stop" in self._metadata else "N/A"

    def suid(self):
        return self.uid().split("-")[0]

    def uid(self):
        return self._metadata["start"]["uid"]


class _Req(_JsonPostRequestHandler):
    async def _incoming(self, req):
        return getattr(self, "_" + req.pkdel("method"))(req)

    async def post(self):
        self.write(await self._incoming(PKDict(pkjson.load_any(self.request.body))))

    def _analysis_output(self, req):
        def _filename_and_image(path):
            return PKDict(
                filename=path.basename,
                image=pkcompat.from_bytes(
                    base64.b64encode(
                        pkio.read_binary(path),
                    ),
                ),
            )

        def _filename_and_json(path):
            return PKDict(filename=path.basename, json=pkjson.load_any(path))

        def _image_paths(uid):
            return pkio.sorted_glob(_Analysis.analysis_output_dir(uid).join("**/*.png"))

        def _json_paths(uid):
            return pkio.sorted_glob(
                _Analysis.analysis_output_dir(uid).join("**/*.json")
            )

        return PKDict(
            images=[_filename_and_image(p) for p in _image_paths(req.uid)],
            jsonFiles=[_filename_and_json(p) for p in _json_paths(req.uid)],
        )

    def _analysis_run_log(self, req):
        p = _Analysis.analysis_output_dir(req.uid).join("run.log")
        return PKDict(
            log_path=str(p),
            run_log=pkio.read_text(p) if p.exists() else "",
        )

    def _begin_replay(self, req):
        sirepo.raydata.replay.begin(
            req.data.sourceCatalogName,
            req.data.destinationCatalogName,
            req.data.numScans,
        )
        return PKDict(data="ok")

    def _catalog_names(self, _):
        return PKDict(
            data=PKDict(
                catalogs=[str(s) for s in databroker.catalog.keys()],
            )
        )

    def _databroker_search(self, catalog, args):
        def _search_params(args):
            q = databroker.queries.TimeRange(
                since=args.searchStartTime, until=args.searchStopTime
            )
            if args.get("searchText"):
                q = {
                    "$and": [
                        q.query,
                        databroker.queries.TextQuery(args.searchText).query,
                    ],
                }
            return q

        def _sort_params(args):
            c = _DEFAULT_COLUMNS.get(args.sortColumn, args.sortColumn)
            s = [
                (
                    c,
                    pymongo.ASCENDING if args.sortOrder else pymongo.DESCENDING,
                ),
            ]
            if c != "time":
                s.append(
                    (
                        "time",
                        pymongo.DESCENDING,
                    )
                )
            return s

        pc = math.ceil(
            len(
                catalog.search(
                    _search_params(args),
                    sort=_sort_params(args),
                )
            )
            / args.pageSize
        )
        l = [
            PKDict(uid=u)
            for u in catalog.search(
                _search_params(args),
                sort=_sort_params(args),
                limit=args.pageSize,
                skip=args.pageNumber * args.pageSize,
            )
        ]
        d = PKDict(
            _Analysis.statuses_for_scans(
                catalog_name=args.catalogName, uids=[s.uid for s in l]
            )
        )
        for s in l:
            s.status = d.get(s.uid, _AnalysisStatus.NONE)
        return l, pc

    def _download_analysis_pdfs(self, req):
        def _is_valid_uuid(uid):
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

        for u in req.data.args.uids:
            assert _is_valid_uuid(u), f"invalid uid={u}"
        with io.BytesIO() as t:
            with zipfile.ZipFile(t, "w") as f:
                for u, v in _all_pdfs(req.data.args.uids):
                    for p in v:
                        f.write(p, pkio.py_path(f"/uids/{u}").join(p.basename))
            t.seek(0)
            requests.put(
                req.data.dataFileUri + "analysis_pdfs.zip",
                data=t.getbuffer(),
                verify=not pkconfig.channel_in("dev"),
            ).raise_for_status()
            return PKDict()

    def _get_scans(self, req):
        a = req.data.args
        c = _catalog(a.catalogName)
        s = 1
        if a.analysisStatus == "allStatuses":
            l, s = self._databroker_search(c, a)
        elif a.analysisStatus == "executed":
            assert a.searchStartTime and a.searchStopTime, pkdformat(
                "must have both searchStartTime and searchStopTime args={}", a
            )
            l = []
            # TODO(pjm): this could be very slow if there were a lot of old analysis records in the db
            # it makes a mongo call per row with no datetime window
            for s in _Analysis.scans_with_status(
                a.catalogName, _AnalysisStatus.EXECUTED
            ):
                m = _Metadata(c[s.uid])
                if m.start() >= a.searchStartTime and m.stop() <= a.searchStopTime:
                    l.append(s)
        elif a.analysisStatus == "queued":
            l = _Analysis.scans_with_status(a.catalogName, _AnalysisStatus.NON_STOPPED)
        elif a.analysisStatus == "recentlyExecuted":
            l = _Analysis.get_recently_updated(
                _NUM_RECENTLY_EXECUTED_SCANS,
                a.catalogName,
                _AnalysisStatus.EXECUTED,
            )
        else:
            raise AssertionError(f"unrecognized analysisStatus={a.analysisStatus}")
        return _scan_info_result(l, c, a, s)

    def _run_analysis(self, req):
        _queue_for_analysis(req.data.args.uid, req.data.args.catalogName)
        return PKDict(data="ok")

    def _scan_fields(self, req):
        return PKDict(
            columns=_Metadata(
                _catalog(req.data.args.catalogName)[-1]
            ).get_scan_fields(),
        )


def _analysis_pdf_paths(uid):
    return pkio.walk_tree(_Analysis.analysis_output_dir(uid), r".*\.pdf$")


def _catalog(name):
    return databroker.catalog[name]


def _check_notebooks_for_catalogs():
    for n in _cfg.catalog_names:
        _notebook_zip_path(n)


def _get_notebooks(catalog_name):
    with zipfile.ZipFile(_notebook_zip_path(catalog_name), "r") as z:
        z.extractall()
    return pkio.sorted_glob("*.ipynb")


async def _init_analysis_processors():
    global _ANALYSIS_PROCESSOR_TASKS

    async def _process_analysis_queue():
        while True:
            if not _SCANS_AWAITING_ANALYSIS:
                await pkasyncio.sleep(5)
                continue
            v = _SCANS_AWAITING_ANALYSIS.pop(0)
            s = _AnalysisStatus.ERROR
            try:
                _Analysis.set_scan_status(v, _AnalysisStatus.RUNNING)
                with pkio.save_chdir(
                    _Analysis.analysis_output_dir(v.uid), mkdir=True
                ), pkio.open_text("run.log", mode="w") as l:
                    try:
                        for n in _get_notebooks(v.catalog_name):
                            p = await asyncio.create_subprocess_exec(
                                "papermill",
                                str(n),
                                f"{n}-out.ipynb",
                                "-p",
                                "uid",
                                v.uid,
                                "-p",
                                "scan",
                                v.uid,
                                stderr=asyncio.subprocess.STDOUT,
                                stdout=l,
                            )
                            r = await p.wait()
                            assert (
                                r == 0
                            ), f"error returncode={r} scan={v} notebook={n} log={pkio.py_path().join('run.log')}"
                            s = _AnalysisStatus.COMPLETED
                    except Exception as e:
                        pkdlog(
                            "error analyzing scan={} error={} stack={}",
                            v,
                            e,
                            pkdexc(),
                        )
            finally:
                _Analysis.set_scan_status(v, s)

    assert not _ANALYSIS_PROCESSOR_TASKS
    _ANALYSIS_PROCESSOR_TASKS = [
        asyncio.create_task(_process_analysis_queue())
    ] * _cfg.concurrent_analyses
    await asyncio.gather(*_ANALYSIS_PROCESSOR_TASKS)


async def _init_catalog_monitors():
    def _monitor_catalog(catalog_name):
        assert catalog_name not in _CATALOG_MONITOR_TASKS
        return asyncio.create_task(_poll_catalog_for_scans(catalog_name))

    if not _cfg.automatic_analysis:
        return
    for c in _cfg.catalog_names:
        _CATALOG_MONITOR_TASKS[c] = _monitor_catalog(c)
    await asyncio.gather(*_CATALOG_MONITOR_TASKS.values())


def _notebook_zip_path(catalog_name):
    return _cfg.notebook_dir.join(f"{catalog_name}.zip")


# TODO(e-carlin): Rather than polling for scans we should explore using RunEngine.subscribe
# https://nsls-ii.github.io/bluesky/generated/bluesky.run_engine.RunEngine.subscribe.html .
# This will probably involve giving some code to BNL that they would add to their RunEngine for the
# beamline. The callback given to subscribe would then call into this daemon letting us know that
# new documents are available.
# But, for now it is easiest to just poll
async def _poll_catalog_for_scans(catalog_name):
    def _collect_new_scans_and_queue(last_known):
        l = last_known
        m = _Metadata(last_known)
        r = [
            scan
            for uid, scan in databroker.catalog[catalog_name]
            .search(databroker.queries.TimeRange(since=m.start()))
            .items()
            if uid != m.uid()
        ]
        r.sort(key=lambda x: _Metadata(x).start())
        for s in r:
            if _Metadata(s).is_scan_plan_executing():
                return l
            _queue_for_analysis(s, catalog_name)
            l = s
        return l

    async def _poll_for_new_scans(most_recent):
        while True:
            most_recent = _collect_new_scans_and_queue(most_recent)
            await pkasyncio.sleep(2)

    pkdlog("catalog_name={}", catalog_name)
    c = None
    while not c:
        try:
            c = databroker.catalog[catalog_name]
        except KeyError:
            pkdlog(f"no catalog_name={catalog_name}. Retrying...")
            await pkasyncio.sleep(15)
    s = c[-1]
    if not _Analysis.have_analyzed_scan(_Metadata(s).uid(), catalog_name):
        _queue_for_analysis(s, catalog_name)
    await _poll_for_new_scans(s)
    raise AssertionError("should never get here")


def _queue_for_analysis(scan, catalog_name):
    s = PKDict(
        uid=scan if isinstance(scan, str) else _Metadata(scan).uid(),
        catalog_name=catalog_name,
    )
    pkdlog("scan={}", s)
    if s not in _SCANS_AWAITING_ANALYSIS:
        pkio.unchecked_remove(_Analysis.analysis_output_dir(s.uid).join("*"))
        _SCANS_AWAITING_ANALYSIS.append(s)
        _Analysis.set_scan_status(s, _AnalysisStatus.PENDING)


def _scan_info(catalog, scan_uuid, scans_data, status=None):
    m = _Metadata(catalog[scan_uuid])
    d = PKDict(
        uid=scan_uuid,
        status=status,
        pdf=True if _analysis_pdf_paths(scan_uuid) else False,
    )
    for c in _DEFAULT_COLUMNS.keys():
        d[c] = getattr(m, c)()

    for c in scans_data.get("selectedColumns", []):
        d[c] = m.get_scan_field(c)
    return d


def _scan_info_result(scans, catalog, args, count):
    s = []
    for i, v in enumerate(scans):
        if i > _MAX_NUM_SCANS:
            raise AssertionError(
                f"More than {_MAX_NUM_SCANS} scans found. Please reduce your query."
            )
        s.append(_scan_info(catalog, v.uid, args, status=v.status))
    return PKDict(
        data=PKDict(
            scans=s,
            cols=[k for k in s[0].keys() if k not in _NON_DISPLAY_SCAN_FIELDS]
            if s
            else [],
            pageCount=count,
        )
    )


def start():
    def _init():
        global _cfg
        _cfg = pkconfig.init(
            automatic_analysis=(
                True,
                bool,
                "automatically queue every incoming scan for analysis",
            ),
            catalog_names=(frozenset(), set, "list of catalog names to monitor"),
            concurrent_analyses=(
                2,
                int,
                "max number of analyses that can run concurrently",
            ),
            db_dir=pkconfig.RequiredUnlessDev(
                sirepo.srdb.root().join("raydata"),
                pkio.py_path,
                "root directory for db",
            ),
            notebook_dir=pkconfig.Required(
                pkio.py_path, "directory for analysis notebooks"
            ),
        )
        sirepo.srtime.init_module()
        _check_notebooks_for_catalogs()
        pkio.mkdir_parent(_cfg.db_dir)
        _Analysis.init(_cfg.db_dir.join("analysis.db"))

    def _start():
        l = pkasyncio.Loop()
        l.run(_init_catalog_monitors(), _init_analysis_processors())
        l.http_server(PKDict(uri_map=((_URI, _Req),)))
        l.start()

    if _cfg:
        return
    _init()
    _start()
