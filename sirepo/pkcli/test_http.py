# -*- coding: utf-8 -*-
"""async requests to server over http

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdexc, pkdlog, pkdformat
import asyncio
import contextlib
import copy
import inspect
import random
import re
import signal
import sirepo.const
import sirepo.pkcli.service
import sirepo.sim_data
import sirepo.util
import time
import tornado.httpclient
import tornado.ioloop
import tornado.locks


_CODES = PKDict(
    elegant=(
        PKDict(
            name="bunchComp - fourDipoleCSR",
            reports=(
                PKDict(report="bunchReport1", binary_data_file=False),
                PKDict(report="elementAnimation10-5", binary_data_file=True),
            ),
        ),
        PKDict(
            name="SPEAR3",
            reports=(
                PKDict(report="bunchReport2", binary_data_file=False),
                PKDict(report="elementAnimation62-20", binary_data_file=True),
            ),
        ),
    ),
    jspec=(
        PKDict(
            name="Booster Ring",
            reports=(
                PKDict(report="particleAnimation", binary_data_file=False),
                PKDict(report="rateCalculationReport", binary_data_file=False),
            ),
        ),
    ),
    srw=(
        PKDict(
            name="Tabulated Undulator Example",
            reports=(
                PKDict(report="intensityReport", binary_data_file=False),
                PKDict(report="trajectoryReport", binary_data_file=False),
                PKDict(report="multiElectronAnimation", binary_data_file=False),
                PKDict(report="powerDensityReport", binary_data_file=False),
                PKDict(report="sourceIntensityReport", binary_data_file=False),
            ),
        ),
        PKDict(
            name="Bending Magnet Radiation",
            reports=(
                PKDict(report="initialIntensityReport", binary_data_file=False),
                PKDict(report="intensityReport", binary_data_file=False),
                PKDict(report="powerDensityReport", binary_data_file=False),
                PKDict(report="sourceIntensityReport", binary_data_file=False),
                PKDict(report="trajectoryReport", binary_data_file=False),
            ),
        ),
    ),
    warppba=(
        PKDict(
            name="Laser Pulse",
            reports=(
                PKDict(report="fieldAnimation", binary_data_file=True),
                PKDict(report="laserPreviewReport", binary_data_file=False),
            ),
        ),
    ),
    warpvnd=(
        PKDict(
            name="EGun Example",
            reports=(PKDict(report="fieldAnimation", binary_data_file=True),),
        ),
    ),
)

cfg = None

_sims = []


def default_command():
    async def _apps():
        a = []
        for c in await _clients():
            for t in _CODES.keys():
                a.append(
                    await _App(
                        sim_type=t,
                        client=c.copy(),
                        examples=copy.deepcopy(_CODES[t]),
                    ).setup_sim_data()
                )
        return a

    async def _clients():
        return await asyncio.gather(*[_Client(u).login() for u in cfg.emails])

    def _register_signal_handlers(main_task):
        def _s(*args):
            main_task.cancel()

        signal.signal(signal.SIGTERM, _s)
        signal.signal(signal.SIGINT, _s)

    async def _run():
        s = []
        try:
            s = await _sims_tasks()
            t = asyncio.gather(*s)
            _register_signal_handlers(t)
            await t
        except Exception as e:
            await _cancel_all_tasks(s)
            if isinstance(e, sirepo.const.ASYNC_CANCELED_ERROR):
                # Will only be canceled by a signal handler
                return
            pkdlog("error={} stack={} sims={}", e, pkdexc(), _sims)
            raise

    async def _sims_tasks():
        s = []
        for a in await _apps():
            e = a.examples[random.randrange(len(a.examples))]
            for r in random.sample(e.reports, len(e.reports)):
                s.append(
                    _Sim(a, e.name, r.report, r.binary_data_file).create_task(),
                )
                await _pause_for_server()
        return s

    random.seed()
    tornado.ioloop.IOLoop.current().run_sync(_run)


class _App(PKDict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client.app = self

    async def setup_sim_data(self):
        r = await self.client.post("/simulation-list", PKDict(), self)
        self._sim_db = PKDict()
        self._sid = PKDict([(x.name, x.simulationId) for x in r])
        self.sim_data = sirepo.sim_data.get_class(self.sim_type)
        return self

    def get_sid(self, sim_name):
        return self._sid[sim_name]

    async def get_sim(self, sim_name):
        try:
            return self._sim_db[sim_name]
        except KeyError:
            self._sim_db[sim_name] = await self.client.get(
                "/simulation/{}/{}/0".format(
                    self.sim_type,
                    self.get_sid(sim_name),
                ),
                self,
            )
            return self._sim_db[sim_name]

    def pkdebug_str(self):
        return pkdformat(
            "{}(sim_type={} email={} uid={})",
            self.__class__.__name__,
            self.sim_type,
            self.client.email,
            self.client.uid,
        )


async def _cancel_all_tasks(tasks):
    for t in tasks:
        await _pause_for_server()
        pkdlog("cancelling task={}", _task_id(t))
        t.cancel()
    # We need a gather() after cancel() because there are awaits in the
    # finally blocks (ex await post('run-cancel)). We need return_exceptions
    # so the CanceledErrors aren't raised which would cancel the gather.
    await asyncio.gather(*tasks, return_exceptions=True)


class _Client(PKDict):
    def __init__(self, email, **kwargs):
        super().__init__(
            email=email,
            uid=None,
            _headers=PKDict({"User-Agent": "test_http"}),
            **kwargs,
        )
        tornado.httpclient.AsyncHTTPClient.configure(None, max_clients=1000)
        self._client = tornado.httpclient.AsyncHTTPClient()

    def copy(self):
        n = _Client(self.email)
        for k, v in self.items():
            if k != "_client":
                n[k] = copy.deepcopy(v)
        return n

    async def get(self, uri, caller, expect_binary_body=False):
        uri = self._uri(uri)
        with self._timer(uri, caller):
            return self.parse_response(
                await self._client.fetch(
                    uri,
                    headers=self._headers,
                    method="GET",
                    **self._fetch_default_args(),
                ),
                expect_binary_body=expect_binary_body,
            )

    async def login(self):
        r = await self.post("/simulation-list", PKDict(), self)
        assert r.srException.routeName == "missingCookies"
        r = await self.post("/simulation-list", PKDict(), self)
        assert r.srException.routeName == "login"
        r = await self.post("/auth-email-login", PKDict(email=self.email), self)
        t = sirepo.util.create_token(
            self.email,
        )
        r = await self.post(
            self._uri("/auth-email-authorized/{}/{}".format(self.sim_type, t)),
            PKDict(token=t, email=self.email),
            self,
        )
        assert r.state != "srException", "r={}".format(r)
        if r.authState.needCompleteRegistration:
            r = await self.post(
                "/auth-complete-registration",
                PKDict(displayName=self.email),
                self,
            )
        self.uid = re.search(
            r'"uid": "(\w+)"',
            await self.get("/auth-state", self),
        ).group(1)
        return self

    def parse_response(self, resp, expect_binary_body=False):
        assert resp.code == 200, "resp={}".format(resp)
        if "Set-Cookie" in resp.headers:
            self._headers.Cookie = resp.headers["Set-Cookie"]
        if "json" in resp.headers["content-type"]:
            return pkjson.load_any(resp.body)
        try:
            b = pkcompat.from_bytes(resp.body)
            assert (
                not expect_binary_body
            ), "expecting binary body resp={} body={}".format(
                resp,
                b[:1000],
            )
        except UnicodeDecodeError:
            assert expect_binary_body, "unexpected binary body resp={}".format(resp)
            # Binary data files can't be decoded
            return
        if "html" in resp.headers["content-type"]:
            m = re.search('location = "(/[^"]+)', b)
            if m:
                if "error" in m.group(1):
                    return PKDict(state="error", error="server error")
                return PKDict(state="redirect", uri=m.group(1))
        return b

    def pkdebug_str(self):
        return pkdformat(
            "{}(email={} uid={})",
            self.__class__.__name__,
            self.email,
            self.uid,
        )

    async def post(self, uri, data, caller):
        data.simulationType = self.sim_type
        uri = self._uri(uri)

        with self._timer(uri, caller):
            return self.parse_response(
                await self._client.fetch(
                    uri,
                    body=pkjson.dump_bytes(data),
                    headers=self._headers.pksetdefault(
                        "Content-type",
                        pkjson.MIME_TYPE,
                    ),
                    method="POST",
                    **self._fetch_default_args(),
                ),
            )

    def _fetch_default_args(self):
        return PKDict(
            connect_timeout=1e8,
            request_timeout=1e8,
            validate_cert=cfg.validate_cert,
        )

    @contextlib.contextmanager
    def _timer(self, uri, caller):
        s = time.time()
        yield
        if "run-status" not in uri:
            pkdlog(
                "{} {} elapsed_time={:.6}",
                uri,
                caller.pkdebug_str(),
                time.time() - s,
            )

    @property
    def sim_type(self):
        try:
            return self.app.sim_type
        except AttributeError:
            # We don't have an app so the sim type doesn't matter
            # just used for login()
            return "elegant"

    def _uri(self, uri):
        if uri.startswith("http"):
            return uri
        assert uri.startswith("/")
        # Elegant frame_id's sometimes have spaces in them so need to
        # make them url safe. But, the * in the url should not be made
        # url safe
        return cfg.server_uri + uri.replace(" ", "%20")


class _Sim(PKDict):
    def __init__(self, app, sim_name, report, binary_data_file, **kwargs):
        super().__init__(
            _app=app,
            _sim_name=sim_name,
            _report=report,
            _binary_data_file=binary_data_file,
            **kwargs,
        )
        self._sid = self._app.get_sid(self._sim_name)

    @contextlib.contextmanager
    def _set_waiting_on_status(self, frame_before_caller=False):
        f = inspect.currentframe().f_back.f_back
        if frame_before_caller:
            f = getattr(f, "f_back")
        c = pkinspect.Call(f)
        self._waiting_on = {
            k: c[k] for k in sorted(c.keys()) if k in ("lineno", "name")
        }
        yield
        # Only clear _waiting_on in the successful case. In failure
        # leave it for debugging
        self._waiting_on = None

    def create_task(self):
        async def _run():
            _sims.append(self)
            # Must be set here once we are in the _run() task
            self._task_id = _task_id(asyncio.current_task())
            with self._set_waiting_on_status():
                self._data = await self._app.get_sim(self._sim_name)
            try:
                r = await self._run_sim_until_completion()
                if self._app.sim_data.is_parallel(self._report):
                    g = await self._get_sim_frame(r)
                    e = False
                    c = None
                    try:
                        with self._set_waiting_on_status():
                            c = True
                            await self._run_sim()
                            c = False
                        with self._set_waiting_on_status():
                            f = await self._app.client.get(
                                "/simulation-frame/" + g, self
                            )
                        assert (
                            f.state == "error"
                        ), "{} expecting error instead of frame={}".format(
                            self.pkdebug_str(),
                            f,
                        )
                    except Exception:
                        e = True
                        raise
                    finally:
                        if c:
                            await self._cancel(error=e)
            except sirepo.const.ASYNC_CANCELED_ERROR:
                # Don't log on cancel error, we initiate cancels so not interesting
                raise
            except Exception as e:
                # The error will be logged 2x (once here and once at the top level).
                # This is not ideal but we need the context we have here which
                # we don't have at the top level
                pkdlog("{} error={} stack={}", self, e, pkdexc())
                raise

        # TODO(e-carlin): in py3.8 set the task_name to be pkdebug_str()
        return asyncio.create_task(_run())

    def pkdebug_str(self):
        return pkdformat(
            "{}(email={} sim_type={} computeJid={} task={} waiting_on={})",
            self.__class__.__name__,
            self._app.client.email,
            self._app.sim_type,
            self._app.sim_data.parse_jid(
                PKDict(simulationId=self._sid, report=self._report),
                uid=self._app.client.uid,
            ),
            self.get("_task_id", "<unknown>"),
            self.get("_waiting_on", "<unknown>"),
        )

    async def _cancel(self, error=False):
        c = self._app.client.post(
            "/run-cancel",
            PKDict(
                report=self._report,
                models=self._data.models,
                simulationId=self._sid,
                simulationType=self._app.sim_type,
            ),
            self,
        )
        if error:
            await c
            return
        with self._set_waiting_on_status(frame_before_caller=True):
            await c

    async def _get_sim_frame(self, next_request):
        g = self._app.sim_data.frame_id(self._data, next_request, self._report, 0)
        with self._set_waiting_on_status():
            f = await self._app.client.get("/simulation-frame/" + g, self)
        assert (
            f.state == "completed"
        ), f"{self.pkdebug_str()} expected state completed frame={f}"
        assert "title" in f, "{} no title in frame={}".format(self.pkdebug_str(), f)
        with self._set_waiting_on_status():
            await self._app.client.get(
                "/download-data-file/{}/{}/{}/{}".format(
                    self._app.sim_type,
                    self._sid,
                    self._report,
                    0,
                ),
                self,
                expect_binary_body=self._binary_data_file,
            )
        return g

    async def _run_sim(self):
        r = self._report
        if "animation" in self._report.lower() and self._app.sim_type != "srw":
            r = "animation"
        return await self._app.client.post(
            "/run-simulation",
            PKDict(
                # works for sequential simulations, too
                forceRun=True,
                models=self._data.models,
                report=r,
                simulationId=self._sid,
                simulationType=self._app.sim_type,
            ),
            self,
        )

    async def _run_sim_until_completion(self):
        c = True
        e = False
        try:
            with self._set_waiting_on_status():
                r = await self._run_sim()
            t = random.randrange(cfg.run_min_secs, cfg.run_max_secs)
            for _ in range(t):
                if r.state == "completed" or r.state == "error":
                    c = False
                    assert r.state != "error", "{} unexpected error state {}".format(
                        self.pkdebug_str(),
                        r,
                    )
                    break
                assert (
                    "nextRequest" in r
                ), '{} expected "nextRequest" in response={}'.format(
                    self.pkdebug_str(),
                    r,
                )
                with self._set_waiting_on_status():
                    r = await self._app.client.post("/run-status", r.nextRequest, self)
                with self._set_waiting_on_status():
                    await tornado.gen.sleep(1)
            else:
                pkdlog("{} timeout={}", self, t)
            return r
        except Exception:
            e = True
            raise
        finally:
            if c:
                await self._cancel(e)


def _init():
    global cfg
    if cfg:
        return
    c = sirepo.pkcli.service._cfg()
    cfg = pkconfig.init(
        emails=(
            ["one@radia.run", "two@radia.run", "three@radia.run"],
            list,
            "emails to test",
        ),
        server_uri=(
            "http://{}:{}".format(c.ip, c.port),
            str,
            "where to send requests",
        ),
        run_min_secs=(
            90,
            pkconfig.parse_seconds,
            "minimum amount of time to let a simulation run",
        ),
        run_max_secs=(
            120,
            pkconfig.parse_seconds,
            "maximum amount of time to let a simulation run",
        ),
        validate_cert=(
            not pkconfig.channel_in("dev"),
            bool,
            "whether or not to validate server tls cert",
        ),
    )


async def _pause_for_server():
    # Sleep a bit to give the server time to respond to requests. Without
    # it connections were being abruptly closed
    await tornado.gen.sleep(1)


def _task_id(task):
    return str(id(task))[-4:]


_init()
