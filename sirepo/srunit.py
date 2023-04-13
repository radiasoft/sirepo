# -*- coding: utf-8 -*-
"""Support for unit tests

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern.pkcollections import PKDict
import contextlib
import json
import pykern.pkinspect
import re
import requests
import urllib

#: Default "app"
MYAPP = "myapp"

#: Matches javascript-redirect.html
_JAVASCRIPT_REDIRECT_RE = re.compile(r'window.location = "([^"]+)"')

#: set by conftest.py
CONFTEST_DEFAULT_CODES = None

SR_SIM_TYPE_DEFAULT = MYAPP

#: Sirepo db dir
_DB_DIR = "db"

_client = None


def http_client(
    env=None, sim_types=None, job_run_mode=None, empty_work_dir=True, port=None
):
    """Create an http_client that talks to server"""
    global _client
    t = sim_types or CONFTEST_DEFAULT_CODES
    if t:
        if isinstance(t, (tuple, list)):
            t = ":".join(t)
        env.SIREPO_FEATURE_CONFIG_SIM_TYPES = t

    from pykern import pkconfig

    pkconfig.reset_state_for_testing(env)
    if _client:
        return _client

    from pykern import pkunit

    if empty_work_dir:
        pkunit.empty_work_dir()
    else:
        pkunit.work_dir()
    setup_srdb_root(cfg=env)

    from sirepo import modules

    modules.import_and_init("sirepo.uri")
    _client = _TestClient(env=env, job_run_mode=job_run_mode, port=port)
    return _client


@contextlib.contextmanager
def quest_start(want_user=False, cfg=None):
    if cfg is None:
        cfg = {}
    setup_srdb_root(cfg=cfg)

    from pykern import pkconfig

    pkconfig.reset_state_for_testing(cfg)

    from sirepo import quest

    with quest.start(in_pkcli=True) as qcall:
        qcall.auth_db.create_or_upgrade()
        if want_user:
            qcall.auth.login(is_mock=True)
        yield qcall


def setup_srdb_root(cfg=None):
    from pykern import pkunit, pkio
    import os

    e = cfg
    if not e:
        e = os.environ
    e.update(
        SIREPO_SRDB_ROOT=str(pkio.mkdir_parent(pkunit.work_dir().join(_DB_DIR))),
    )


class _TestClient:
    def __init__(self, env, job_run_mode, port):
        super().__init__()
        self.sr_job_run_mode = job_run_mode
        self.sr_sbatch_logged_in = False
        self.sr_sim_type = None
        self.sr_uid = None
        self.port = port
        self.http_prefix = f"http://{env.SIREPO_PKCLI_SERVICE_IP}:{port}"
        self._session = requests.Session()
        self.cookie_jar = self._session.cookies

    def get(self, uri, headers=None):
        return self._requests_op("get", uri, headers, kwargs=PKDict())

    def post(self, uri, data=None, json=None, headers=None, file_handle=None):
        assert (data is None) != (json is None)
        k = PKDict()
        if data is not None:
            k.data = data
        else:
            k.json = json
        if file_handle is not None:
            k.files = PKDict(file=file_handle)
        return self._requests_op("post", uri, headers, k)

    @contextlib.contextmanager
    def sr_adjust_time(self, days):
        from sirepo import srtime

        def _do(days):
            srtime.adjust_time(days)
            self.sr_get_json("adjustTime", params=PKDict(days=days))

        _do(days)
        yield
        _do(0)

    def sr_animation_run(self, data, compute_model, reports=None, **kwargs):
        from pykern import pkunit
        from pykern.pkcollections import PKDict
        from pykern.pkdebug import pkdp, pkdlog
        import re

        run = self.sr_run_sim(data, compute_model, **kwargs)
        for r, a in reports.items():
            if "runSimulation" in a:
                f = self.sr_run_sim(data, r)
                for k, v in a.items():
                    m = re.search("^expect_(.+)", k)
                    if m:
                        pkunit.pkre(
                            v(i) if callable(v) else v,
                            str(f.get(m.group(1))),
                        )
                continue
            if "frame_index" in a:
                c = [a.get("frame_index")]
            else:
                c = range(run.get(a.get("frame_count_key", "frameCount")))
                assert c, "frame_count_key={} or frameCount={} is zero".format(
                    a.get("frame_count_key"),
                    a.get("frameCount"),
                )
            pkdlog("frameReport={} count={}", r, c)
            from sirepo import sim_data

            s = sim_data.get_class(self.sr_sim_type)
            for i in c:
                pkdlog("frameIndex={} frameCount={}", i, run.get("frameCount"))
                f = self.sr_get_json(
                    "simulationFrame",
                    PKDict(frame_id=s.frame_id(data, run, r, i)),
                )
                for k, v in a.items():
                    m = re.search("^expect_(.+)", k)
                    if m:
                        pkunit.pkre(
                            v(i) if callable(v) else v,
                            str(f.get(m.group(1))),
                        )

    def sr_auth_state(self, **kwargs):
        """Gets authState and prases

        Returns:
            dict: parsed auth_state
        """
        from pykern import pkunit
        from pykern import pkcollections

        m = re.search(
            r"(\{.*\})",
            pkcompat.from_bytes(self.sr_get("authState").data),
        )
        s = pkcollections.json_load_any(m.group(1))
        for k, v in kwargs.items():
            pkunit.pkeq(
                v,
                s[k],
                "key={} expected={} != actual={}: auth_state={}",
                k,
                v,
                s[k],
                s,
            )
        return s

    def sr_email_confirm(self, resp, display_name=None):
        from pykern.pkdebug import pkdlog

        self.sr_get(resp.uri)
        pkdlog(resp.uri)
        m = re.search(r"/(\w+)$", resp.uri)
        assert bool(m)
        r = PKDict(token=m.group(1))
        if display_name:
            r.displayName = display_name
        self.sr_post(resp.uri, r, raw_response=True)

    def sr_email_login(self, email, sim_type=None):
        self.sr_sim_type_set(sim_type)
        self.sr_logout()
        r = self.sr_post(
            "authEmailLogin",
            PKDict(email=email, simulationType=self.sr_sim_type),
        )
        self.sr_email_confirm(r, display_name=email)
        return self._verify_and_save_uid()

    def sr_get(self, route_or_uri, params=None, query=None, **kwargs):
        """Gets a request to route_or_uri to server

        Args:
            route_or_uri (str): string name of route or uri if contains '/' (http:// or '/foo')
            params (dict): optional params to route_or_uri

        Returns:
            SReply: reply object
        """
        return self.__req(
            route_or_uri,
            params=params,
            query=query,
            op=self.get,
            raw_response=True,
            **kwargs,
        )

    def sr_get_json(
        self, route_or_uri, params=None, query=None, headers=None, **kwargs
    ):
        """Gets a request to route_or_uri to server

        Args:
            route_or_uri (str): identifies route in schema-common.json
            params (dict): optional params to route_or_uri

        Returns:
            object: Parsed JSON result
        """
        return self.__req(
            route_or_uri,
            params=params,
            query=query,
            op=lambda r: self.get(r, headers=headers),
            raw_response=False,
            **kwargs,
        )

    def sr_get_root(self, sim_type=None, **kwargs):
        """Gets root app for sim_type

        Args:
            sim_type (str): app name ['myapp' or default type]

        Returns:
            SReply: reply object
        """
        self.sr_sim_type_set(sim_type)
        return self.__req(
            "root",
            params={"path_info": self.sr_sim_type},
            query=None,
            op=self.get,
            raw_response=True,
            **kwargs,
        )

    def sr_login_as_guest(self, sim_type=None):
        """Sets up a guest login

        Args:
            sim_type (str): simulation type ['myapp']

        Returns:
            str: new user id
        """
        self.sr_sim_type_set(sim_type)
        self.cookie_jar.clear()
        # Get a cookie
        self.sr_get("authState")
        self.sr_get("authGuestLogin", {"simulation_type": self.sr_sim_type})
        return self._verify_and_save_uid()

    def sr_logout(self):
        """Logout but leave cookie in place

        Returns:
            object: self
        """
        self.sr_uid = None
        self.sr_get("authLogout", PKDict(simulation_type=self.sr_sim_type))
        return self

    def sr_post(self, route_or_uri, data, params=None, raw_response=False, **kwargs):
        """Posts JSON data to route_or_uri to server

        File parameters are posted as::

        Args:
            route_or_uri (str): string name of route or uri if contains '/' (http:// or '/foo')
            data (object): will be formatted as form data
            params (dict): optional params to route_or_uri

        Returns:
            object: Parsed JSON result
        """
        op = lambda r: self.post(r, json=data)
        return self.__req(
            route_or_uri,
            params=params,
            query={},
            op=op,
            raw_response=raw_response,
            **kwargs,
        )

    def sr_post_form(
        self, route_or_uri, data, params=None, raw_response=False, file=None, **kwargs
    ):
        """Posts form data to route_or_uri to server with data

        Args:
            route_or_uri (str): identifies route in schema-common.json
            data (dict): will be formatted as form-data
            params (dict): optional params to route_or_uri
            file (object): if str, will look in data_dir, else assumed py.path

        Returns:
            object: Parsed JSON result
        """
        from pykern import pkunit, pkconfig

        k = PKDict(data=data)
        if file:
            p = file
            if isinstance(p, pkconfig.STRING_TYPES):
                p = pkunit.data_dir().join(p)
            k.file_handle = open(str(p), "rb")
        return self.__req(
            route_or_uri,
            params,
            query=PKDict(),
            op=lambda r: self.post(r, **k),
            raw_response=raw_response,
            **kwargs,
        )

    def sr_run_sim(self, data, model, expect_completed=True, timeout=20, **post_args):
        from pykern import pkunit
        from pykern.pkdebug import pkdlog, pkdexc
        import time

        if self.sr_job_run_mode:
            data.models[model].jobRunMode = self.sr_job_run_mode

        cancel = None
        try:
            r = self.sr_post(
                "runSimulation",
                PKDict(
                    models=data.models,
                    report=model,
                    simulationId=data.models.simulation.simulationId,
                    simulationType=data.simulationType,
                ).pkupdate(**post_args),
            )
            if r.state == "completed":
                return r
            pkunit.pkok(
                r.state in ("running", "pending"),
                "runSimulation did not start: reply={}",
                r,
            )
            cancel = r.nextRequest
            for i in range(timeout):
                if i != 0:
                    pkunit.pkok(
                        "nextRequest" in r,
                        "nextRequest missing from reply={}",
                        r,
                    )
                    r = self.sr_post("runStatus", r.nextRequest)
                pkdlog(r.state)
                if r.state in ("completed", "error"):
                    cancel = None
                    break
                time.sleep(1)
            else:
                pkunit.pkok(not expect_completed, "did not complete: runStatus={}", r)
            if expect_completed:
                pkunit.pkeq("completed", r.state)
            return r
        finally:
            if cancel:
                pkdlog("runCancel")
                self.sr_post("runCancel", cancel)
            import subprocess

            o = pkcompat.from_bytes(
                subprocess.check_output(["ps", "axww"], stderr=subprocess.STDOUT),
            )
            o = list(filter(lambda x: "mpiexec" in x, o.split("\n")))
            if o:
                pkdlog('found "mpiexec" after cancel in ps={}', "\n".join(o))
                # this exception won't be seen because in finally
                raise AssertionError("cancel failed")

    def sr_sbatch_animation_run(self, sim_name, compute_model, reports, **kwargs):
        from pykern.pkunit import pkexcept

        d = self.sr_sim_data(sim_name)
        if not self.sr_sbatch_logged_in:
            with pkexcept("SRException.*no-creds"):
                # Must try to run sim first to seed job_supervisor.db
                self.sr_run_sim(d, compute_model, expect_completed=False)
            self.sr_sbatch_login(compute_model, d)
            self.sr_sbatch_logged_in = True
        self.sr_animation_run(
            self.sr_sim_data(sim_name),
            compute_model,
            reports,
            # Things take longer with Slurm.
            timeout=90,
            **kwargs,
        )

    def sr_sbatch_login(self, compute_model, data):
        import getpass

        p = getpass.getuser()
        self.sr_post(
            "sbatchLogin",
            PKDict(
                password=p,
                report=compute_model,
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
                username=p,
            ),
        )

    def sr_sim_data(self, sim_name=None, sim_type=None):
        """Return simulation data by name

        Args:
            sim_name (str): case sensitive name ['Scooby Doo']
            sim_type (str): app ['myapp']

        Returns:
            dict: data
        """
        from pykern import pkunit
        from pykern.pkdebug import pkdpretty

        self.sr_sim_type_set(sim_type)

        if not sim_name:
            sim_name = "Scooby Doo"
        d = self.sr_post(
            "listSimulations",
            PKDict(
                simulationType=self.sr_sim_type,
                search=PKDict({"simulation.name": sim_name}),
            ),
        )
        assert 1 == len(d), "listSimulations name={} returned count={}".format(
            sim_name, len(d)
        )
        d = d[0].simulation
        res = self.sr_get_json(
            "simulationData",
            PKDict(
                simulation_type=self.sr_sim_type,
                pretty="0",
                simulation_id=d.simulationId,
            ),
        )
        pkunit.pkeq(sim_name, res.models.simulation.name)
        return res

    def sr_sim_type_set(self, sim_type=None):
        """Set `sr_sim_type

        Args:
            sim_type (str): app name
        Returns:
            object: self
        """
        self.sr_sim_type = sim_type or self.sr_sim_type or SR_SIM_TYPE_DEFAULT
        return self

    def sr_user_dir(self, uid=None):
        """User's db dir"""
        from pykern import pkunit

        if not uid:
            uid = self.sr_auth_state().uid
        return pkunit.work_dir().join(_DB_DIR, "user", uid)

    def _verify_and_save_uid(self):
        self.sr_uid = self.sr_auth_state(
            needCompleteRegistration=False, isLoggedIn=True
        ).uid
        return self.sr_uid

    def __req(self, route_or_uri, params, query, op, raw_response, **kwargs):
        """Make request and parse result

        Args:
            route_or_uri (str): string name of route or uri if contains '/' (http:// or '/foo')
            params (dict): parameters to apply to route
            op (func): how to request

        Returns:
            object: parsed JSON result
        """
        from pykern.pkdebug import pkdlog, pkdexc, pkdc, pkdp
        from pykern import pkjson
        from sirepo import uri, util, reply

        redirects = kwargs.setdefault("__redirects", 0) + 1
        assert redirects <= 5
        kwargs["__redirects"] = redirects

        u = None
        r = None
        try:
            u = uri.server_route(route_or_uri, params, query)
            pkdc("uri={}", u)
            r = op(u)
            pkdc(
                "status={} data={}",
                r.status_code,
                "<snip-file>" if "download-data-file" in u else r.data,
            )
            # Emulate code in sirepo.js to deal with redirects
            if r.status_code == 200 and r.mimetype == "text/html":
                m = _JAVASCRIPT_REDIRECT_RE.search(pkcompat.from_bytes(r.data))
                if m:
                    if m.group(1).endswith("#/error"):
                        raise util.Error(
                            PKDict(error="server error uri={}".format(m.group(1))),
                        )
                    if kwargs.get("redirect", True):
                        # Execute the redirect
                        return self.__req(
                            m.group(1),
                            params=None,
                            query=None,
                            op=self.get,
                            raw_response=raw_response,
                            __redirects=redirects,
                        )
                    return r.change_to_redirect(m.group(1))
            if r.status_code in (301, 302, 303, 305, 307, 308):
                if kwargs.get("redirect", True):
                    # Execute the redirect
                    return self.__req(
                        r.headers["Location"],
                        params=None,
                        query=None,
                        op=self.get,
                        raw_response=raw_response,
                        __redirects=redirects,
                    )
            if raw_response:
                return r
            # Treat SRException as a real exception (so we don't ignore them)
            d = pkjson.load_any(r.data)
            if isinstance(d, dict) and d.get("state") == reply.SR_EXCEPTION_STATE:
                raise util.SRException(
                    d.srException.routeName,
                    d.srException.params,
                )
            return d
        except Exception as e:
            if not isinstance(e, (util.ReplyExc)):
                pkdlog(
                    "Exception: {}: msg={} uri={} status={} data={} stack={}",
                    type(e),
                    e,
                    u,
                    r and r.status_code,
                    r and r.data,
                    pkdexc(),
                )
            raise

    def _requests_op(self, op, uri, headers, kwargs):
        from sirepo import const

        u = self._uri(uri)
        if headers is None:
            headers = PKDict()
        headers.setdefault(
            "User-Agent",
            f"{const.SRUNIT_USER_AGENT} {pykern.pkinspect.caller()}",
        )
        try:
            return _Response(
                getattr(self._session, op)(u, headers=headers, **kwargs),
            )
        except requests.exceptions.ConnectionError as e:
            from pykern.pkdebug import pkdlog

            pkdlog("op={} uri={} headers={}", op, u, headers)
            raise

    def _uri(self, uri):
        from pykern.pkdebug import pkdp

        u = urllib.parse.urlparse(uri)
        if u.scheme:
            return uri
        return self.http_prefix + uri


class _Response:
    def __init__(self, reply):
        self._reply = reply

    @property
    def data(self):
        return self._reply.content

    def header_get(self, name):
        return self._reply.headers[name]

    @property
    def mimetype(self):
        c = self._reply.headers.get("content-type")
        if not c:
            return ""
        return c.split(";")[0].strip()

    @property
    def status_code(self):
        return self._reply.status_code

    def change_to_redirect(self, uri):
        self._reply = PKDict(
            status_code=302,
            headers=PKDict(Location=uri),
        )
        return self
