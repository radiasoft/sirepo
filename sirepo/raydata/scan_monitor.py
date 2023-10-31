# -*- coding: utf-8 -*-
"""ray data scan monitor

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from pykern import pkasyncio
from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdformat
import aenum
import asyncio
import databroker.queries
import io
import math
import pymongo
import requests
import sirepo.feature_config
import sirepo.raydata.analysis_driver
import sirepo.raydata.databroker
import sirepo.srdb
import sirepo.srtime
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import tornado.websocket
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

cfg = None

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
    def have_analyzed_scan(cls, scan_metadata):
        return bool(
            cls.search_by(
                uid=scan_metadata.uid, catalog_name=scan_metadata.catalog_name
            )
        )

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
    def set_scan_status(cls, analysis_driver, status):
        r = cls.search_by(
            uid=analysis_driver.uid, catalog_name=analysis_driver.catalog_name
        )
        if not r:
            cls(
                uid=analysis_driver.uid,
                catalog_name=analysis_driver.catalog_name,
                status=status,
            ).save()
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


class _RequestHandler(_JsonPostRequestHandler):
    async def _incoming(self, body):
        return getattr(self, "_request_" + body.method)(body.data.get("args"))

    async def post(self):
        self.write(await self._incoming(PKDict(pkjson.load_any(self.request.body))))

    def _databroker_search(self, req_data):
        def _search_params(req_data):
            q = databroker.queries.TimeRange(
                since=req_data.searchStartTime, until=req_data.searchStopTime
            )
            if req_data.get("searchText"):
                q = {
                    "$and": [
                        q.query,
                        databroker.queries.TextQuery(req_data.searchText).query,
                    ],
                }
            return q

        def _sort_params(req_data):
            c = _DEFAULT_COLUMNS.get(req_data.sortColumn, req_data.sortColumn)
            s = [
                (
                    c,
                    pymongo.ASCENDING if req_data.sortOrder else pymongo.DESCENDING,
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

        c = sirepo.raydata.databroker.catalog(req_data.catalogName)
        pc = math.ceil(
            len(
                c.search(
                    _search_params(req_data),
                    sort=_sort_params(req_data),
                )
            )
            / req_data.pageSize
        )
        l = [
            PKDict(uid=u)
            for u in c.search(
                _search_params(req_data),
                sort=_sort_params(req_data),
                limit=req_data.pageSize,
                skip=req_data.pageNumber * req_data.pageSize,
            )
        ]
        d = PKDict(
            _Analysis.statuses_for_scans(
                catalog_name=req_data.catalogName, uids=[s.uid for s in l]
            )
        )
        for s in l:
            s.status = d.get(s.uid, _AnalysisStatus.NONE)
        return l, pc

    def _request_analysis_output(self, req_data):
        return sirepo.raydata.analysis_driver.get(req_data).get_output()

    def _request_analysis_run_log(self, req_data):
        return sirepo.raydata.analysis_driver.get(req_data).get_run_log()

    def _request_begin_replay(self, req_data):
        sirepo.raydata.replay.begin(
            req_data.sourceCatalogName,
            req_data.destinationCatalogName,
            req_data.numScans,
        )
        return PKDict(data="ok")

    def _request_catalog_names(self, _):
        return PKDict(
            data=PKDict(
                catalogs=sirepo.raydata.databroker.catalogs(),
            )
        )

    def _request_download_analysis_pdfs(self, req_data):
        def _all_pdfs(uids):
            for u in uids:
                p = sirepo.raydata.analysis_driver.get(
                    PKDict(uid=u, **req_data)
                ).get_analysis_pdf_paths()
                if not p:
                    raise AssertionError(f"no analysis pdfs found for uid={u}")
                yield u, p

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

    def _request_get_scans(self, req_data):
        s = 1
        if req_data.analysisStatus == "allStatuses":
            l, s = self._databroker_search(req_data)
        elif req_data.analysisStatus == "executed":
            assert req_data.searchStartTime and req_data.searchStopTime, pkdformat(
                "must have both searchStartTime and searchStopTime req_data={}",
                req_data,
            )
            l = []
            # TODO(pjm): this could be very slow if there were a lot of old analysis records in the db
            # it makes a mongo call per row with no datetime window
            for s in _Analysis.scans_with_status(
                req_data.catalogName, _AnalysisStatus.EXECUTED
            ):
                m = sirepo.raydata.databroker.get_metadata(s.uid, req_data.catalogName)
                if (
                    m.start() >= req_data.searchStartTime
                    and m.stop() <= req_data.searchStopTime
                ):
                    l.append(s)
        elif req_data.analysisStatus == "queued":
            l = _Analysis.scans_with_status(
                req_data.catalogName, _AnalysisStatus.NON_STOPPED
            )
        elif req_data.analysisStatus == "recentlyExecuted":
            l = _Analysis.get_recently_updated(
                _NUM_RECENTLY_EXECUTED_SCANS,
                req_data.catalogName,
                _AnalysisStatus.EXECUTED,
            )
        else:
            raise AssertionError(
                f"unrecognized analysisStatus={req_data.analysisStatus}"
            )
        if len(l) > _MAX_NUM_SCANS:
            raise AssertionError(
                f"More than {_MAX_NUM_SCANS} scans found. Please reduce your query."
            )
        return _scan_info_result(l, s, req_data)

    def _request_run_analysis(self, req_data):
        _queue_for_analysis(
            sirepo.raydata.databroker.get_metadata(req_data.uid, req_data.catalogName)
        )
        return PKDict(data="ok")

    def _request_scan_fields(self, req_data):
        return PKDict(
            columns=sirepo.raydata.databroker.get_metadata_for_most_recent_scan(
                req_data.catalogName
            ).get_start_fields(),
        )


async def _init_analysis_processors():
    global _ANALYSIS_PROCESSOR_TASKS

    async def _process_analysis_queue():
        while True:
            if not _SCANS_AWAITING_ANALYSIS:
                await pkasyncio.sleep(5)
                continue
            d = sirepo.raydata.analysis_driver.get(_SCANS_AWAITING_ANALYSIS.pop(0))
            s = _AnalysisStatus.ERROR
            try:
                _Analysis.set_scan_status(d, _AnalysisStatus.RUNNING)
                with pkio.save_chdir(d.get_output_dir(), mkdir=True), pkio.open_text(
                    "run.log", mode="w"
                ) as l:
                    try:
                        for n in d.get_notebooks():
                            p = await asyncio.create_subprocess_exec(
                                "bash",
                                d.render_papermill_script(
                                    input_f=n.input_f,
                                    output_f=n.output_f,
                                ),
                                stderr=asyncio.subprocess.STDOUT,
                                stdout=l,
                            )
                            r = await p.wait()
                            assert (
                                r == 0
                            ), f"error returncode={r} catalog={d.catalog_name} scan={d.uid} notebook={n} log={pkio.py_path().join('run.log')}"
                            s = _AnalysisStatus.COMPLETED
                    except Exception as e:
                        pkdlog(
                            "error analyzing scan={} error={} stack={}",
                            d.uid,
                            e,
                            pkdexc(),
                        )
            finally:
                _Analysis.set_scan_status(d, s)

    assert not _ANALYSIS_PROCESSOR_TASKS
    _ANALYSIS_PROCESSOR_TASKS = [
        asyncio.create_task(_process_analysis_queue())
    ] * cfg.concurrent_analyses
    await asyncio.gather(*_ANALYSIS_PROCESSOR_TASKS)


async def _init_catalog_monitors():
    def _monitor_catalog(catalog_name):
        assert catalog_name not in _CATALOG_MONITOR_TASKS
        return asyncio.create_task(_poll_catalog_for_scans(catalog_name))

    if not cfg.automatic_analysis:
        return
    for c in cfg.catalog_names:
        _CATALOG_MONITOR_TASKS[c] = _monitor_catalog(c)
    await asyncio.gather(*_CATALOG_MONITOR_TASKS.values())


# TODO(e-carlin): Rather than polling for scans we should explore using RunEngine.subscribe
# https://nsls-ii.github.io/bluesky/generated/bluesky.run_engine.RunEngine.subscribe.html .
# This will probably involve giving some code to BNL that they would add to their RunEngine for the
# beamline. The callback given to subscribe would then call into this daemon letting us know that
# new documents are available.
# But, for now it is easiest to just poll
async def _poll_catalog_for_scans(catalog_name):
    # TODO(e-carlin): need to test polling feature
    def _collect_new_scans_and_queue(last_known_scan_metadata):
        r = [
            sirepo.raydata.databroker.get_metadata(s, catalog_name)
            for u, s in sirepo.raydata.databroker.catalog(catalog_name)
            .search(
                databroker.queries.TimeRange(since=last_known_scan_metadata.start())
            )
            .items()
            if u != last_known_scan_metadata.uid
        ]
        l = last_known_scan_metadata
        r.sort(key=lambda x: x.start())
        for s in r:
            if s.is_scan_plan_executing():
                return l
            _queue_for_analysis(s)
            l = s
        return l

    async def _poll_for_new_scans(most_recent_scan_metadata):
        m = most_recent_scan_metadata
        while True:
            m = _collect_new_scans_and_queue(m)
            await pkasyncio.sleep(2)

    pkdlog("catalog_name={}", catalog_name)
    c = None
    while not c:
        try:
            c = sirepo.raydata.databroker.catalog(catalog_name)
        except KeyError:
            pkdlog(f"no catalog_name={catalog_name}. Retrying...")
            await pkasyncio.sleep(15)
    s = sirepo.raydata.databroker.get_metadata_for_most_recent_scan(catalog_name)
    if not _Analysis.have_analyzed_scan(s):
        _queue_for_analysis(s)
    await _poll_for_new_scans(s)
    raise AssertionError("should never get here")


def _queue_for_analysis(scan_metadata):
    s = PKDict(
        uid=scan_metadata.uid,
        catalog_name=scan_metadata.catalog_name,
    )
    pkdlog("scan={}", s)
    if s not in _SCANS_AWAITING_ANALYSIS:
        pkio.unchecked_remove(sirepo.raydata.analysis_driver.get(s).get_output_dir())
        _SCANS_AWAITING_ANALYSIS.append(s)
        _Analysis.set_scan_status(s, _AnalysisStatus.PENDING)


def _scan_info(uid, status, req_data):
    m = sirepo.raydata.databroker.get_metadata(uid, req_data.catalogName)
    d = PKDict(
        uid=uid,
        status=status,
        pdf=sirepo.raydata.analysis_driver.get(
            PKDict(uid=uid, **req_data)
        ).has_analysis_pdfs(),
    )
    for c in _DEFAULT_COLUMNS.keys():
        d[c] = getattr(m, c)()

    for c in req_data.get("selectedColumns", []):
        d[c] = m.get_start_field(c, unchecked=True)
    return d


def _scan_info_result(scans, page_count, req_data):
    s = [_scan_info(x.uid, x.status, req_data) for x in scans]
    return PKDict(
        data=PKDict(
            scans=s,
            cols=[k for k in s[0].keys() if k not in _NON_DISPLAY_SCAN_FIELDS]
            if s
            else [],
            pageCount=page_count,
        )
    )


def start():
    def _init():
        global cfg
        cfg = pkconfig.init(
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
        )
        sirepo.srtime.init_module()
        pkio.mkdir_parent(cfg.db_dir)
        _Analysis.init(cfg.db_dir.join("analysis.db"))
        sirepo.raydata.analysis_driver.init(cfg.catalog_names)

    def _start():
        l = pkasyncio.Loop()
        l.run(_init_catalog_monitors(), _init_analysis_processors())
        l.http_server(PKDict(uri_map=((_URI, _RequestHandler),)))
        l.start()

    if cfg:
        return
    _init()
    _start()
