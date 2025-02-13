"""Entry points for job execution

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat, pkinspect, pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdpretty, pkdformat
from sirepo import simulation_db
from sirepo.template import template_common
import asyncio
import contextlib
import inspect
import pykern.pkconfig
import pykern.pkio
import re
import sirepo.auth
import sirepo.feature_config
import sirepo.job
import sirepo.quest
import sirepo.sim_data
import sirepo.sim_run
import sirepo.uri_router
import sirepo.util
import tornado.httpclient


#: how many call frames to search backwards to find the api_.* caller
_MAX_FRAME_SEARCH_DEPTH = 6

_MUST_HAVE_METHOD = ("api_analysisJob", "api_statefulCompute", "api_statelessCompute")

_JSON_TYPE = re.compile(f"^{pkjson.MIME_TYPE}")

_HTTP_CLIENT_CONNECTION_ERRORS = (
    tornado.httpclient.HTTPClientError,
    ConnectionRefusedError,
)


class API(sirepo.quest.API):
    @sirepo.quest.Spec("internal_test", days="TimeDeltaDays")
    async def api_adjustSupervisorSrtime(self, days):
        return await self._request_api(
            api_name="not used",
            _request_content=PKDict(days=days),
            _request_uri=self._supervisor_uri(sirepo.job.SERVER_SRTIME_URI),
        )

    @sirepo.quest.Spec("require_adm")
    async def api_admJobs(self):
        return await self._request_api(
            _request_content=self._parse_post_just_data(),
        )

    @sirepo.quest.Spec("require_plan")
    async def api_analysisJob(self):
        # TODO(robnagler): computeJobHash has to be checked
        return await self._request_api()

    @sirepo.quest.Spec("require_plan")
    async def api_beginSession(self):
        """Starts beginSession request asynchronously

        Returns:
            SReply: always OK
        """
        return await self._request_api(
            _ignore_reply=True,
            _request_content=self._parse_post_just_data(),
        )

    @sirepo.quest.Spec(
        "require_plan",
        sid="SimId",
        model="AnalysisModel",
        frame="DataFileIndex",
        suffix="FileSuffix optional",
    )
    async def api_downloadDataFile(
        self, simulation_type, simulation_id, model, frame, suffix=None
    ):
        """Deprecated use `api_downloadRunFile`"""
        return await self.api_downloadRunFile(
            simulation_type, simulation_id, model, frame, suffix=suffix
        )

    @sirepo.quest.Spec(
        "require_plan",
        sid="SimId",
        model="AnalysisModel",
        frame="DataFileIndex",
        suffix="FileSuffix optional",
    )
    async def api_downloadRunFile(
        self, simulation_type, simulation_id, model, frame, suffix=None
    ):
        def _content_too_large(req):
            return sirepo.util.ContentTooLarge(
                "sim_type={} sid={} report={}",
                req.type,
                req.id,
                req.req_data.report,
            )

        # TODO(robnagler) validate suffix and frame
        req = self.parse_params(
            id=simulation_id,
            model=model,
            type=simulation_type,
            check_sim_exists=True,
        )
        s = suffix and sirepo.srschema.parse_name(suffix)
        t = None
        with sirepo.sim_run.tmp_dir(qcall=self) as d:
            # TODO(e-carlin): computeJobHash
            t = sirepo.job.DATA_FILE_ROOT.join(sirepo.util.unique_key())
            t.mksymlinkto(d, absolute=True)
            try:
                r = await self._request_api(
                    computeJobHash="unused",
                    dataFileKey=t.basename,
                    frame=int(frame),
                    isParallel=False,
                    req_data=req.req_data,
                    suffix=s,
                )
                if r.state == sirepo.job.CANCELED:
                    # POSIT: Users can't cancel donwloadDataFile. So canceled means there was a
                    # timeout (max_run_secs exceeded).
                    raise _content_too_large(req)
                if r.state == sirepo.job.ERROR:
                    if r.get("errorCode") == sirepo.job.ERROR_CODE_RESPONSE_TOO_LARGE:
                        raise _content_too_large(req)
                    raise AssertionError(pkdformat("error state in request=={}", r))
                f = d.listdir()
                if len(f) > 0:
                    assert len(f) == 1, "too many files={}".format(f)
                    return self.reply_attachment(f[0])
            except _HTTP_CLIENT_CONNECTION_ERRORS:
                # TODO(robnagler) is this too coarse a check?
                pass
            finally:
                if t:
                    pykern.pkio.unchecked_remove(t)
            raise sirepo.util.NotFound(
                f"frame={frame} not found sid={req.id} sim_type={req.type}",
            )

    @sirepo.quest.Spec("require_plan")
    async def api_globalResources(self):
        assert (
            sirepo.feature_config.cfg().enable_global_resources
        ), "global resources server api called but system not enabled"
        return await self._request_api(
            _request_content=self._parse_post_just_data(),
        )

    @sirepo.quest.Spec("allow_visitor")
    async def api_jobSupervisorPing(self):
        e = None
        try:
            k = sirepo.util.unique_key()
            r = await self._request_api(
                _request_content=PKDict(ping=k),
                _request_uri=self._supervisor_uri(sirepo.job.SERVER_PING_URI),
            )
            if r.get("state") != "ok":
                return r
            try:
                x = r.pknested_get("ping")
            except KeyError:
                e = "incorrectly formatted reply"
            else:
                if x == k:
                    return r
                e = "expected={} but got ping={}".format(k, x)
        except _HTTP_CLIENT_CONNECTION_ERRORS as e2:
            pkdlog("HTTPClientError={}", e2)
            e = "unable to connect to supervisor"
        except Exception as e2:
            pkdlog("unexpected exception={} exc={} stack={}", type(e2), e2, pkdexc())
            e = "unexpected exception"
        return PKDict(state="error", error=e)

    @sirepo.quest.Spec("require_plan")
    async def api_ownJobs(self):
        return await self._request_api(
            _request_content=self._parse_post_just_data(),
        )

    @sirepo.quest.Spec("require_plan")
    async def api_runCancel(self):
        try:
            return await self._request_api()
        except Exception as e:
            pkdlog("ignoring exception={} stack={}", e, pkdexc())
        # Always true from the client's perspective
        return self.reply_dict({"state": "canceled"})

    @sirepo.quest.Spec("require_plan")
    async def api_runSimulation(self):
        r = self._request_content(PKDict())
        if r.isParallel:
            r.isPremiumUser = self.auth.is_premium_user()
        return await self._request_api(_request_content=r)

    @sirepo.quest.Spec("require_plan")
    async def api_runStatus(self):
        # runStatus receives models when an animation status if first queried
        return await self._request_api(_request_content=self._request_content(PKDict()))

    @sirepo.quest.Spec("require_plan")
    async def api_sbatchLogin(self):
        r = self._request_content(
            PKDict(computeJobHash="unused", jobRunMode=sirepo.job.SBATCH),
        )
        # SECURITY: Don't include credentials so the agent can't see them.
        r.sbatchCredentials = r.data.sbatchCredentials
        r.pkdel("data")
        return await self._request_api(_request_content=r)

    @sirepo.quest.Spec("require_plan")
    async def api_sbatchLoginStatus(self):
        if sirepo.job.SBATCH not in simulation_db.JOB_RUN_MODE_MAP:
            raise AssertionError(f"{sirepo.job.SBATCH} jobRunMode is not enabled")
        return await self._request_api(
            _request_content=self._request_content(
                PKDict(computeJobHash="unused", jobRunMode=sirepo.job.SBATCH),
            )
        )

    @sirepo.quest.Spec("require_plan", frame_id="SimFrameId")
    async def api_simulationFrame(self, frame_id):
        return await template_common.sim_frame(
            frame_id,
            lambda a: self._request_api(
                analysisModel=a.frameReport,
                # simulation frames are always sequential requests even though
                # the report name has 'animation' in it.
                isParallel=False,
                req_data=PKDict(**a),
            ),
            self,
        )

    @sirepo.quest.Spec("require_plan")
    async def api_statefulCompute(self):
        return await self._request_compute(op_key="stful")

    @sirepo.quest.Spec("require_plan")
    async def api_statelessCompute(self):
        return await self._request_compute(op_key="stlss")

    def _parse_post_just_data(self, want_type=False):
        """Remove computed objects"""
        r = self.parse_post(template=False, type=want_type)
        r.pkdel("qcall")
        r.pkdel("sim_data")
        r.data = r.pkdel("req_data")
        if want_type:
            r.simulationType = r.pkdel("type")
        return self._request_content_put_user(r)

    async def _request_api(self, **kwargs):
        def _api_name(value):
            if value:
                return value
            f = inspect.currentframe()
            for _ in range(_MAX_FRAME_SEARCH_DEPTH):
                m = re.search(r"^api_.*$", f.f_code.co_name)
                if m:
                    return m.group()
                f = f.f_back
            else:
                raise AssertionError(
                    "{}: max frame search depth reached".format(f.f_code)
                )

        def _args(kwargs):
            res = PKDict()
            k = PKDict(kwargs)
            res.uri = k.pkdel("_request_uri") or self._supervisor_uri(
                sirepo.job.SERVER_URI
            )
            res.ignore_reply = k.pkdel("_ignore_reply")
            res.api = _api_name(k.pkdel("api_name"))
            c = (
                k.pkdel("_request_content")
                if "_request_content" in k
                else self._request_content(k)
            )
            c.pkupdate(
                api=res.api,
                serverSecret=sirepo.job.cfg().server_secret,
            )
            if c.api in _MUST_HAVE_METHOD:
                # TODO(robnagler) should be error reply
                assert (
                    "method" in c.data
                ), f"missing method for api={c.api} in content={list(c.keys())}"
            if c.api not in ("api_runStatus",):
                pkdlog("api={} runDir={}", c.api, c.get("runDir"))
            res.content = c
            return res

        a = _args(kwargs)
        with self._reply_maybe_file(a.content) as d:
            r = tornado.httpclient.AsyncHTTPClient(
                max_buffer_size=sirepo.job.cfg().max_message_bytes,
                force_instance=True,
            ).fetch(
                tornado.httpclient.HTTPRequest(
                    body=pkjson.dump_bytes(a.content),
                    connect_timeout=60,
                    headers=PKDict({"Content-type": pkjson.MIME_TYPE}),
                    method="POST",
                    request_timeout=0,
                    url=a.uri,
                    validate_cert=sirepo.job.cfg().verify_tls,
                ),
            )
            if a.ignore_reply:
                asyncio.ensure_future(r)
                return self.reply_ok()
            r = await r
            if not _JSON_TYPE.search(r.headers["content-type"]):
                raise AssertionError(
                    f"expected json content-type={r.headers['content-type']}"
                )
            j = pkjson.load_any(r.body)
            if d and (
                sirepo.job.is_ok_reply(j) or j.get("state") == sirepo.job.COMPLETED
            ):
                return self._reply_with_file(d)
            return j

    async def _request_compute(self, op_key):
        c = self._parse_post_just_data(want_type=True)
        j = sirepo.job.quasi_jid(c.uid, op_key, c.data.method)
        s = sirepo.job.split_jid(j)
        c.pkupdate(
            computeJid=j,
            computeModel=s.compute_model,
            isParallel=False,
            jobRunMode=sirepo.job.SEQUENTIAL,
            # TODO(robnagler) not supposed to access run dir
            runDir=None,
            simulationId=s.sid,
        )
        self.bucket_set("sim_data", sirepo.sim_data.get_class(c.simulationType))
        return await self._request_api(_request_content=c)

    def _request_content(self, kwargs):
        def _run_mode(request_content):
            if "models" not in request_content.data or "jobRunMode" in request_content:
                return request_content
            # TODO(robnagler) make sure this is set for animation sim frames
            m = request_content.data.models.get(request_content.computeModel)
            j = m and m.get("jobRunMode")
            if not j:
                request_content.jobRunMode = (
                    sirepo.job.PARALLEL
                    if request_content.isParallel
                    else sirepo.job.SEQUENTIAL
                )
                return request_content
            if j not in simulation_db.JOB_RUN_MODE_MAP:
                raise sirepo.util.Error(
                    "invalid jobRunMode",
                    "invalid jobRunMode={} computeModel={} computeJid={}",
                    j,
                    request_content.computeModel,
                    request_content.computeJid,
                )
            request_content.jobRunMode = j
            return _validate_and_add_sbatch_fields(request_content, m)

        def _validate_and_add_sbatch_fields(request_content, compute_model):
            m = compute_model
            c = request_content
            d = simulation_db.cfg().get("sbatch_display")
            if d and "nersc" in d.lower():
                assert (
                    m.sbatchQueue in sirepo.job.NERSC_QUEUES
                ), f"sbatchQueue={m.sbatchQueue} not in NERSC_QUEUES={sirepo.job.NERSC_QUEUES}"
                c.sbatchQueue = m.sbatchQueue
                c.sbatchProject = m.sbatchProject
            for f in "sbatchCores", "sbatchHours", "sbatchNodes", "tasksPerNode":
                if f not in m:
                    continue
                assert m[f] > 0, f"{f}={m[f]} must be greater than 0"
                c[f] = m[f]
            return request_content

        d = kwargs.pkdel("req_data")
        if not d:
            # TODO(robnagler) need to use parsed values, ok for now, because none of
            # of the used values are modified by parse_post. If we have files (e.g. file_type, filename),
            # we need to use those values from parse_post
            d = self.parse_post(
                id=True,
                model=True,
                check_sim_exists=True,
            ).req_data
        s = sirepo.sim_data.get_class(d)
        ##TODO(robnagler) this should be req_data
        b = self._request_content_put_user(PKDict(data=d, **kwargs))
        # TODO(e-carlin): some of these fields are only used for some type of reqs
        b.pksetdefault(
            analysisModel=lambda: s.parse_model(d),
            computeJobHash=lambda: d.get("computeJobHash")
            or s.compute_job_hash(d, qcall=self),
            computeJobSerial=lambda: d.get("computeJobSerial", 0),
            computeModel=lambda: s.compute_model(d),
            isParallel=lambda: s.is_parallel(d),
            # TODO(robnagler) relative to srdb root
            runDir=lambda: str(simulation_db.simulation_run_dir(d, qcall=self)),
            simulationId=lambda: s.parse_sid(d),
            simulationType=lambda: d.simulationType,
        ).pkupdate(
            computeJid=s.parse_jid(d, uid=b.uid),
        )
        self.bucket_set("sim_data", s)
        return _run_mode(b)

    def _request_content_put_user(self, content):
        """Required request content"""
        return content.pkupdate(
            uid=self.auth.logged_in_user(),
            userDir=str(sirepo.simulation_db.user_path(qcall=self)),
        )

    @contextlib.contextmanager
    def _reply_maybe_file(self, content):
        s = self.bucket_unchecked_get("sim_data")
        if (
            not s
            or content.api not in _MUST_HAVE_METHOD
            or not s.does_api_reply_with_file(
                content.api,
                content.data.get("method"),
            )
        ):
            yield None
            return
        with sirepo.sim_run.tmp_dir(qcall=self) as d:
            t = None
            try:
                t = sirepo.job.DATA_FILE_ROOT.join(sirepo.util.unique_key())
                t.mksymlinkto(d, absolute=True)
                content.dataFileKey = t.basename
                yield d
            finally:
                if t:
                    pykern.pkio.unchecked_remove(t)

    def _reply_with_file(self, tmp_dir):
        f = tmp_dir.listdir()
        if len(f) != 1:
            raise AssertionError(
                f"too many files={f}" if f else f"no files in tmp_dir={tmp_dir}",
            )
        return self.reply_file(f[0])

    def _supervisor_uri(self, path):
        return _cfg.supervisor_uri + path


def init_apis(*args, **kwargs):
    # TODO(robnagler) if we recover connections with agents and running jobs remove this
    pykern.pkio.unchecked_remove(sirepo.job.DATA_FILE_ROOT)
    pykern.pkio.mkdir_parent(sirepo.job.DATA_FILE_ROOT)


_cfg = pykern.pkconfig.init(
    supervisor_uri=sirepo.job.DEFAULT_SUPERVISOR_URI_DECL,
)
