"""ray data scan monitor

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkasyncio
from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdformat
import aenum
import asyncio
import databroker.queries
import datetime
import functools
import io
import itertools
import math
import pymongo
import re
import requests
import sirepo.feature_config
import sirepo.raydata.adaptive_workflow
import sirepo.raydata.analysis_driver
import sirepo.raydata.databroker
import sirepo.sim_data
import sirepo.srdb
import sirepo.srtime
import sirepo.tornado
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import zipfile


#: task(s) monitoring the execution of the analysis process
_ANALYSIS_PROCESSOR_TASKS = None

#: task(s) monitoring catalogs for new scans
_CATALOG_MONITOR_TASKS = PKDict()

# TODO(e-carlin): tune this number
_MAX_NUM_SCANS = 1000


# Fields that come from the top-level of metadata (as opposed to start document).
# Must match key name from _default_columns()
_METADATA_COLUMNS = {"start", "stop", "suid"}

_NON_DISPLAY_SCAN_FIELDS = "rduid"

_NUM_RECENTLY_EXECUTED_SCANS = 5

#: scan(s) awaiting analysis to be run on them
_SCANS_AWAITING_ANALYSIS = []

#: path scan_monitor registers to receive api requests
_URI = "/scan-monitor"

#: Whether or not new scans should be automatically analyzed (per catalog)
_WANT_AUTOMATIC_ANALYSIS_FOR_CATALOG = PKDict()


_SIM_TYPE = "raydata"

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
    rduid = sqlalchemy.Column(sqlalchemy.String(36), nullable=False, primary_key=True)
    catalog_name = sqlalchemy.Column(
        sqlalchemy.String(20), nullable=False, primary_key=True
    )
    status = sqlalchemy.Column(sqlalchemy.String(20), nullable=False)
    analysis_elapsed_time = sqlalchemy.Column(
        sqlalchemy.Integer(),
        nullable=True,
    )
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
            r.append(
                PKDict(
                    rduid=x.rduid,
                    status=x.status,
                    detailed_status=_get_detailed_status(catalog_name, x.rduid),
                    analysis_elapsed_time=x.analysis_elapsed_time,
                    catalog_name=catalog_name,
                )
            )
        return r

    @classmethod
    def have_analyzed_scan(cls, scan_metadata):
        return bool(
            cls.search_by(
                rduid=scan_metadata.rduid, catalog_name=scan_metadata.catalog_name
            )
        )

    @classmethod
    def init(cls, db_file):
        global engine
        if engine is None:
            engine = sqlalchemy.create_engine(f"sqlite:///{db_file}")
        cls.metadata.create_all(bind=engine)
        cls.session = sqlalchemy.orm.Session(bind=engine)
        cls._db_upgrade()

    @classmethod
    def scans_with_status(cls, catalog_name, statuses):
        r = []
        for s in statuses:
            for x in cls.search_all_by(catalog_name=catalog_name, status=s):
                r.append(
                    PKDict(
                        rduid=x.rduid,
                        status=x.status,
                        detailed_status=_get_detailed_status(catalog_name, x.rduid),
                        analysis_elapsed_time=x.analysis_elapsed_time,
                        catalog_name=catalog_name,
                    )
                )
        return r

    @classmethod
    def search_all_by(cls, **kwargs):
        return cls.session.query(cls).filter_by(**kwargs).all()

    @classmethod
    def search_by(cls, **kwargs):
        return cls.session.query(cls).filter_by(**kwargs).first()

    @classmethod
    def set_scan_status(cls, analysis_driver, status, analysis_elapsed_time=None):
        r = cls.search_by(
            rduid=analysis_driver.rduid, catalog_name=analysis_driver.catalog_name
        )
        if not r:
            cls(
                rduid=analysis_driver.rduid,
                catalog_name=analysis_driver.catalog_name,
                status=status,
                analysis_elapsed_time=analysis_elapsed_time,
            ).save()
            return
        r.status = status
        r.analysis_elapsed_time = analysis_elapsed_time
        r.save()

    @classmethod
    def status_and_elapsed_time(cls, catalog_name, rduid):
        r = (
            cls.session.query(cls.status, cls.analysis_elapsed_time)
            .filter(cls.rduid == rduid)
            .one_or_none()
        )
        if r:
            return PKDict(status=r[0], analysis_elapsed_time=r[1])
        return PKDict(status=None, analysis_elapsed_time=None)

    @classmethod
    def _db_upgrade(cls):
        def _add_analysis_elapsed_time_column():
            if _analysis_elapsed_time_in_schema():
                return
            cls.session.execute(
                sqlalchemy.text(
                    f"ALTER TABLE {cls.__tablename__} ADD COLUMN analysis_elapsed_time INTEGER"
                )
            )
            cls.session.commit()

        def _analysis_elapsed_time_in_schema():
            for c in sqlalchemy.inspect(engine).get_columns(cls.__tablename__):
                if c.get("name") == "analysis_elapsed_time":
                    return True
            return False

        def _fixup_running_statuses():
            for x in cls.session.query(cls).filter(
                cls.status.in_(_AnalysisStatus.NON_STOPPED)
            ):

                cls.set_scan_status(
                    PKDict(rduid=x.rduid, catalog_name=x.catalog_name),
                    _AnalysisStatus.ERROR,
                )

        def _rduid_in_schema():
            for c in sqlalchemy.inspect(engine).get_columns(cls.__tablename__):
                if c.get("name") == "rduid":
                    return True
            return False

        def _rename_uid_column_to_rduid():
            if _rduid_in_schema():
                return
            cls.session.execute(
                sqlalchemy.text(
                    f"ALTER TABLE {cls.__tablename__} RENAME COLUMN uid TO rduid"
                )
            )
            cls.session.commit()

        _add_analysis_elapsed_time_column()
        _rename_uid_column_to_rduid()
        _fixup_running_statuses()


# TODO(e-carlin): copied from sirepo
# TODO(e-carlin): Since we are going to sockets for communication we should probably use them here.
# But, for now it is easier to just make a normal http request
class _JsonPostRequestHandler(sirepo.tornado.AuthHeaderRequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", pkjson.CONTENT_TYPE)


class _RequestHandler(_JsonPostRequestHandler):
    async def _incoming(self, body):
        return getattr(self, "_request_" + body.method)(body.data.get("args"))

    def _build_search_terms(self, terms):
        res = []
        for search in terms:
            if self._can_cast_to_float(search.term):
                # numeric values might be stored as strings in the mongo db
                # so need to search for either string value or number value
                res.append(
                    {
                        "$or": [
                            {
                                search.column: search.term,
                            },
                            {
                                search.column: float(search.term),
                            },
                        ]
                    }
                )
            else:
                if "*" in search.term:
                    res.append(
                        {
                            search.column: {"$regex": re.sub(r"\*", ".*", search.term)},
                        }
                    )
                else:
                    res.append(
                        {
                            search.column: search.term,
                        }
                    )
        return res

    def _build_search_text(self, text):
        # separate out scan_id (integer) searches from the text terms
        nums = []
        terms = re.findall(r'(".*?")', text)
        for t in re.split(r"\s+", re.sub(r'".*?"', "", text).strip()):
            if t.startswith("-"):
                terms.append(t)
            elif re.search(r"^\d{5,}$", t):
                nums.append(int(t))
            elif t:
                terms.append(f'"{t}"')
        terms = " ".join(terms)

        if len(nums) and len(terms):
            return {
                "$and": [
                    databroker.queries.TextQuery(terms).query,
                    {
                        "scan_id": {"$in": nums},
                    },
                ],
            }
        if len(nums):
            return {
                "scan_id": {"$in": nums},
            }
        return databroker.queries.TextQuery(terms).query

    def _can_cast_to_float(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _databroker_search(self, req_data):
        def _search_params(req_data):
            q = databroker.queries.TimeRange(
                since=req_data.searchStartTime, until=req_data.searchStopTime
            )
            if req_data.get("searchText") or len(req_data.get("searchTerms", [])):
                items = [
                    q.query,
                ]
                if req_data.get("searchText"):
                    items.append(self._build_search_text(req_data.searchText))
                if req_data.get("searchTerms"):
                    items += self._build_search_terms(req_data.searchTerms)
                q = {
                    "$and": items,
                }
            return q

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
        res = []
        for u in c.search(
            _search_params(req_data),
            sort=_sort_params(req_data),
            limit=req_data.pageSize,
            skip=req_data.pageNumber * req_data.pageSize,
        ):
            # Code after this (ex detailed_status) expects that the
            # scan is valid (ex 'cycle' exists in start doc for chx).
            # So, don't even show scans to users that aren't elegible.
            if sirepo.raydata.analysis_driver.get(
                PKDict(catalog_name=req_data.catalogName, rduid=u)
            ).is_scan_elegible_for_analysis():
                res.append(
                    PKDict(
                        rduid=u,
                        detailed_status=_get_detailed_status(req_data.catalogName, u),
                        **_Analysis.status_and_elapsed_time(req_data.catalogName, u),
                    )
                )
        return res, pc

    def _request_analysis_output(self, req_data):
        return sirepo.raydata.analysis_driver.get(req_data).get_output()

    def _request_analysis_run_log(self, req_data):
        return sirepo.raydata.analysis_driver.get(req_data).get_run_log()

    def _request_catalog_names(self, _):
        return PKDict(
            data=PKDict(
                catalogs=sirepo.raydata.databroker.catalogs(),
            )
        )

    def _request_download_analysis_pdfs(self, req_data):
        def _all_pdfs(rduids):
            for u in rduids:
                p = sirepo.raydata.analysis_driver.get(
                    PKDict(rduid=u, **req_data)
                ).get_analysis_pdf_paths()
                if not p:
                    raise AssertionError(f"no analysis pdfs found for rduid={u}")
                yield u, p

        with io.BytesIO() as t:
            with zipfile.ZipFile(t, "w") as f:
                for u, v in _all_pdfs(req_data.rduids):
                    for p in v:
                        f.write(p, pkio.py_path(f"/rduids/{u}").join(p.basename))
            t.seek(0)
            requests.put(
                req_data.dataFileUri + "analysis_pdfs.zip",
                data=t.getbuffer(),
                verify=not pkconfig.channel_in("dev"),
            ).raise_for_status()
            return PKDict()

    def _request_get_automatic_analysis(self, req_data):
        return PKDict(
            data=PKDict(
                automaticAnalysis=_WANT_AUTOMATIC_ANALYSIS_FOR_CATALOG[
                    req_data.catalogName
                ]
            )
        )

    def _request_get_scans(self, req_data):
        s = 1
        if req_data.analysisStatus == "allStatuses":
            l, s = self._databroker_search(req_data)
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

    def _request_reorder_scan(self, req_data):
        i = _scan_index(req_data.rduid, req_data)
        if i >= 0:
            s = _SCANS_AWAITING_ANALYSIS.pop(i)
            if s.rduid != req_data.rduid:
                raise AssertionError(
                    f"Failed to pop() correct scan: {req_data.rduid} != {s.rduid}"
                )
            if req_data.action == "first":
                _SCANS_AWAITING_ANALYSIS.insert(0, s)
            elif req_data.action == "last":
                _SCANS_AWAITING_ANALYSIS.append(s)
            else:
                raise AssertionError(f"Unknown reorder action {req_data.action}")
        return PKDict(data="ok")

    def _request_run_analysis(self, req_data):
        _queue_for_analysis(
            sirepo.raydata.databroker.get_metadata(req_data.rduid, req_data.catalogName)
        )
        return PKDict(data="ok")

    def _request_run_engine_event_callback(self, req_data):
        # Start as a task. No need to hold request until task is
        # completed because the caller does nothing with the response.
        pkasyncio.create_task(
            sirepo.raydata.adaptive_workflow.run_engine_event_callback(req_data)
        )
        return PKDict()

    def _request_scan_fields(self, req_data):
        return PKDict(
            columns=_display_columns(
                sirepo.raydata.databroker.get_metadata_for_most_recent_scan(
                    req_data.catalogName
                ).get_start_fields(),
            )
        )

    def _request_set_automatic_analysis(self, req_data):
        _WANT_AUTOMATIC_ANALYSIS_FOR_CATALOG[req_data.catalogName] = bool(
            int(req_data.automaticAnalysis)
        )
        return PKDict(data="ok")

    def _sr_authenticate(self, token):
        if (
            token
            == sirepo.feature_config.for_sim_type(_SIM_TYPE).scan_monitor_api_secret
        ):
            return token
        raise sirepo.tornado.error_forbidden()

    async def _sr_post(self, *args, **kwargs):
        self.write(await self._incoming(PKDict(pkjson.load_any(self.request.body))))


def _sort_params(req_data):
    r = []
    has_time = False
    for x in req_data.sortColumns:
        n = _default_columns(req_data.catalogName).get(x[0], x[0])
        if n == "time":
            has_time = True
        r.append(
            [
                n,
                pymongo.ASCENDING if x[1] else pymongo.DESCENDING,
            ]
        )
    if not has_time:
        r.append(["time", pymongo.DESCENDING])
    return r


async def _init_analysis_processors():
    global _ANALYSIS_PROCESSOR_TASKS

    async def _process_analysis_queue():
        while True:
            if not _SCANS_AWAITING_ANALYSIS:
                await pkasyncio.sleep(5)
                continue
            d = sirepo.raydata.analysis_driver.get(_SCANS_AWAITING_ANALYSIS.pop(0))
            s = _AnalysisStatus.ERROR
            start = None
            end = None
            try:
                _Analysis.set_scan_status(d, _AnalysisStatus.RUNNING)
                with pkio.save_chdir(d.get_output_dir(), mkdir=True), pkio.open_text(
                    "run.log", mode="w"
                ) as l:
                    try:
                        start = datetime.datetime.now()
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
                            ), f"error returncode={r} catalog={d.catalog_name} scan={d.rduid} notebook={n} log={pkio.py_path().join('run.log')}"
                            s = _AnalysisStatus.COMPLETED
                            end = datetime.datetime.now()
                    except Exception as e:
                        end = datetime.datetime.now()
                        pkdlog(
                            "error analyzing scan={} error={} stack={}",
                            d.rduid,
                            e,
                            pkdexc(),
                        )
            finally:
                t = int((end - start).total_seconds()) if (end and start) else None
                _Analysis.set_scan_status(d, s, t)

    assert not _ANALYSIS_PROCESSOR_TASKS
    _ANALYSIS_PROCESSOR_TASKS = [
        pkasyncio.create_task(_process_analysis_queue())
    ] * cfg.concurrent_analyses
    await asyncio.gather(*_ANALYSIS_PROCESSOR_TASKS)


def _display_columns(columns):
    return [k for k in columns if k not in _NON_DISPLAY_SCAN_FIELDS]


def _default_columns(catalog_name):
    return PKDict(
        start="time",
        stop="time",
        suid="uid",
        **{
            e: e
            for e in sirepo.sim_data.get_class(_SIM_TYPE)
            .schema()
            .constants.defaultColumns.get(catalog_name, [])
        },
    )


def _get_detailed_status(catalog_name, rduid):
    return sirepo.raydata.analysis_driver.get(
        PKDict(catalog_name=catalog_name, rduid=rduid)
    ).get_detailed_status_file(rduid)


async def _init_catalog_monitors():
    def _monitor_catalog(catalog_name):
        assert catalog_name not in _CATALOG_MONITOR_TASKS
        return asyncio.create_task(_poll_catalog_for_scans(catalog_name))

    for c in cfg.catalog_names:
        _CATALOG_MONITOR_TASKS[c] = _monitor_catalog(c)
        _WANT_AUTOMATIC_ANALYSIS_FOR_CATALOG[c] = cfg.automatic_analysis
    await asyncio.gather(*_CATALOG_MONITOR_TASKS.values())


# TODO(e-carlin): Rather than polling for scans we should explore using RunEngine.subscribe
# https://nsls-ii.github.io/bluesky/generated/bluesky.run_engine.RunEngine.subscribe.html .
# This will probably involve giving some code to BNL that they would add to their RunEngine for the
# beamline. The callback given to subscribe would then call into this daemon letting us know that
# new documents are available.
# But, for now it is easiest to just poll
async def _poll_catalog_for_scans(catalog_name):
    def _collect_new_scans_and_queue(last_known_scan_metadata):
        r = [
            sirepo.raydata.databroker.get_metadata(s, catalog_name)
            for u, s in sirepo.raydata.databroker.catalog(catalog_name)
            .search(
                databroker.queries.TimeRange(since=last_known_scan_metadata.start())
            )
            .items()
            if u != last_known_scan_metadata.rduid
        ]
        l = last_known_scan_metadata
        r.sort(key=lambda x: x.start())
        for s in r:
            if s.is_scan_plan_executing():
                return l
            _queue_for_analysis(s)
            l = s
        return l

    async def _poll_for_new_scans():
        while True:
            if not _WANT_AUTOMATIC_ANALYSIS_FOR_CATALOG[catalog_name]:
                await asyncio.sleep(2)
                continue
            s = sirepo.raydata.databroker.get_metadata_for_most_recent_scan(
                catalog_name
            )
            if not _Analysis.have_analyzed_scan(s):
                _queue_for_analysis(s)
            while _WANT_AUTOMATIC_ANALYSIS_FOR_CATALOG[catalog_name]:
                s = _collect_new_scans_and_queue(s)
                await pkasyncio.sleep(2)

    async def _wait_for_catalog():
        while True:
            try:
                sirepo.raydata.databroker.catalog(catalog_name)
                return
            except KeyError:
                pkdlog(f"no catalog_name={catalog_name}. Retrying...")
                await pkasyncio.sleep(15)

    pkdlog("catalog_name={}", catalog_name)
    await _wait_for_catalog()
    await _poll_for_new_scans()
    raise AssertionError("should never get here")


def _queue_for_analysis(scan_metadata):
    s = PKDict(
        rduid=scan_metadata.rduid,
        catalog_name=scan_metadata.catalog_name,
    )
    if not sirepo.raydata.analysis_driver.get(s).is_scan_elegible_for_analysis():
        return
    pkdlog("scan={}", s)
    if s not in _SCANS_AWAITING_ANALYSIS:
        pkio.unchecked_remove(sirepo.raydata.analysis_driver.get(s).get_output_dir())
        _SCANS_AWAITING_ANALYSIS.append(s)
        _Analysis.set_scan_status(s, _AnalysisStatus.PENDING)


def _scan_index(rduid, req_data):
    s = PKDict(
        rduid=rduid,
        catalog_name=req_data.catalogName,
    )
    return _SCANS_AWAITING_ANALYSIS.index(s) if s in _SCANS_AWAITING_ANALYSIS else -1


def _scan_info(
    rduid, status, detailed_status, analysis_elapsed_time, req_data, all_columns
):
    def _get_start_field(metadata, column):
        return

    m = sirepo.raydata.databroker.get_metadata(rduid, req_data.catalogName)
    d = PKDict(
        rduid=rduid,
        status=status,
        detailed_status=detailed_status,
        analysis_elapsed_time=analysis_elapsed_time,
        pdf=sirepo.raydata.analysis_driver.get(
            PKDict(rduid=rduid, **req_data)
        ).has_analysis_pdfs(),
    )
    for c in itertools.chain(
        _default_columns(req_data.catalogName).keys(),
        req_data.get("selectedColumns", []),
    ):
        d[c] = (
            getattr(m, c)()
            if c in _METADATA_COLUMNS
            else m.get_start_field(c, unchecked=True)
        )
    for c in m.get_start_fields():
        all_columns.add(c)

    d["queue order"] = _scan_index(rduid, req_data) + 1
    return d


def _scan_info_result(scans, page_count, req_data):
    def _compare_values(v1, v2):
        sort_column = _sort_params(req_data)[0][0]
        # very careful compare - needs to account for missing values or mismatched types
        v1 = v1.get(sort_column)
        v2 = v2.get(sort_column)
        if v1 is None and v2 is None:
            return 0
        if v1 is None:
            return -1
        if v2 is None:
            return 1
        if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
            return v1 - v2
        if not isinstance(v1, str):
            v1 = pkjson.dump_pretty(v1)
        if not isinstance(v2, str):
            v2 = pkjson.dump_pretty(v2)
        if v1 == v2:
            return 0
        return -1 if v1 < v2 else 1

    all_columns = set()
    s = [
        _scan_info(
            x.rduid,
            x.status,
            x.detailed_status,
            x.analysis_elapsed_time,
            req_data,
            all_columns,
        )
        for x in scans
    ]
    if req_data.analysisStatus in ("recentlyExecuted", "queued"):
        s = sorted(
            s,
            key=functools.cmp_to_key(_compare_values),
            reverse=not _sort_params(req_data)[0][1],
        )
    return PKDict(
        data=PKDict(
            scans=s,
            cols=_display_columns(all_columns),
            pageCount=page_count,
            pageNumber=req_data.pageNumber,
            sortColumns=req_data.sortColumns,
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
                sirepo.srdb.root().join(_SIM_TYPE),
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
