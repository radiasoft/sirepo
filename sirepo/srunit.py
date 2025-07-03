"""Support for unit tests

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcollections
from pykern import pkcompat
from pykern import pkjson
from pykern.pkcollections import PKDict
import base64
import contextlib
import copy
import json
import os.path
import pykern.pkinspect
import re
import requests
import threading
import urllib

#: Default "app"
MYAPP = "myapp"

#: Matches javascript-redirect.html
_JAVASCRIPT_REDIRECT_RE = re.compile(r'window.location = "([^"]+)"')

#: set by conftest.py
CONFTEST_DEFAULT_CODES = None

SR_SIM_TYPE_DEFAULT = MYAPP

SR_SIM_NAME_DEFAULT = "Scooby Doo"

#: Sirepo db dir
_DB_DIR = "db"

#: How many checks and how long to wait between checks for scenarios
_ITER_SLEEP = PKDict(
    slurm=PKDict(
        count=5,
        sleep_secs=5,
    )
)


__cfg = None


def http_client(
    env=None, sim_types=None, job_run_mode=None, empty_work_dir=True, port=None
):
    """Create an http_client that talks to server"""
    t = sim_types or CONFTEST_DEFAULT_CODES
    if t:
        if isinstance(t, (tuple, list)):
            t = ":".join(t)
        env.SIREPO_FEATURE_CONFIG_SIM_TYPES = t

    from pykern import pkconfig

    pkconfig.reset_state_for_testing(env)

    from pykern import pkunit

    if empty_work_dir:
        pkunit.empty_work_dir()
    else:
        pkunit.work_dir()
    setup_srdb_root(cfg=env)

    from sirepo import modules

    modules.import_and_init("sirepo.uri")
    return _TestClient(env=env, job_run_mode=job_run_mode, port=port)


@contextlib.contextmanager
def quest_start(want_user=False, want_global_user=False, cfg=None):
    if cfg is None:
        cfg = {}
    setup_srdb_root(cfg=cfg)

    from pykern import pkconfig

    pkconfig.reset_state_for_testing(cfg)

    from sirepo import quest

    with quest.start(in_pkcli=True) as qcall:
        qcall.auth_db.create_or_upgrade()
        if want_global_user or want_user:
            with qcall.auth.srunit_user(want_global=want_global_user):
                yield qcall
        else:
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


def template_import_file(sim_type, path, arguments=None):
    """Call `stateful_compute_import_file`

    Args:
        sim_type (str): template name
        path (object): if path is a str, will be joined with `data_dir`,
        arguments (object): literal passed as import_file_arguments
    Returns:
        PKDict: imported_data if successful; otherwise, error state
    """
    from pykern import pkio, pkunit
    from sirepo import template

    if isinstance(path, str):
        path = pkunit.data_dir().join(path)
    return template.import_module(sim_type).stateful_compute_import_file(
        data=PKDict(
            args=PKDict(
                basename=path.basename,
                ext_lower=path.ext.lower(),
                file_as_str=pkio.read_text(path),
                folder="/import_test",
                import_file_arguments=arguments,
                purebasename=path.purebasename,
            ),
        ),
    )


class _TestClient:
    def __init__(self, env, job_run_mode, port):
        from sirepo import feature_config

        super().__init__()
        self._init_args = PKDict(env=env, job_run_mode=job_run_mode, port=port)
        self.sr_job_run_mode = job_run_mode
        self.sr_sbatch_logged_in = False
        self.sr_sim_type = None
        self.sr_uid = None
        self.port = port
        self.http_prefix = f"http://{env.SIREPO_PKCLI_SERVICE_IP}:{port}"
        self._session = requests.Session()
        self.cookie_jar = self._session.cookies
        self._threads = PKDict()
        if feature_config.cfg().ui_websocket:
            self._websocket = _WebSocket(self)

    def add_plan_trial_role(self):
        from sirepo.pkcli import roles
        from sirepo import auth_role

        roles.add(self.sr_uid, auth_role.ROLE_PLAN_TRIAL)

    def assert_post_will_redirect(self, expect_re, *args, **kwargs):
        rv = self.sr_post(*args, **kwargs)
        rv.assert_http_redirect(expect_re)
        return rv

    def error_or_sr_exception(self):
        """Hack to check for SRException or Error

        Works around the websocket/http differences in this module.
        What should happen is that an exception is always created and
        can be checked later. This means fixing some tests. This is
        easier for now.

        """
        from pykern.pkunit import pkexcept

        return pkexcept("(SRException|Error)\(")

    def iter_sleep(self, kind, op_desc):
        import time
        from pykern import pkunit

        def _setup():
            rv = PKDict(_ITER_SLEEP[kind])
            rv.countdown = range(rv.count, -1, -1)
            return rv

        s = _setup()
        for i in s.countdown:
            yield
            if i > 0:
                time.sleep(s.sleep_secs)
        else:
            pkunit.pkfail(
                "timeout secs={} kind={} op_desc={}",
                s.sleep_secs * s.count,
                kind,
                op_desc,
            )

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
        """Gets authState and parses

        Returns:
            dict: parsed auth_state
        """
        from pykern import pkunit, pkcollections
        from pykern.pkdebug import pkdp

        m = re.search(
            r"(\{.*\})",
            pkcompat.from_bytes(self.sr_get("authState").data),
        )
        s = pkjson.load_any(m.group(1))
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

    def sr_clone(self):
        res = self.__class__(**self._init_args)
        res._session = copy.deepcopy(self._session)
        res.cookie_jar = res._session.cookies
        return res

    def sr_db_dir(self):
        """Database directory of the server"""
        from pykern import pkunit

        return pkunit.work_dir().join(_DB_DIR)

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
        self._uid_clear()
        self.sr_sim_type_set(sim_type)
        self.sr_logout()
        r = self.sr_post(
            "authEmailLogin",
            PKDict(email=email, simulationType=self.sr_sim_type),
        )
        self.sr_email_confirm(r, display_name=email)
        return self._uid_verify_and_save()

    def sr_get(
        self, route_or_uri, params=None, query=None, raw_response=True, **kwargs
    ):
        """Gets a request to route_or_uri to server

        Args:
            route_or_uri (str): string name of route or uri if contains '/' (http:// or '/foo')
            params (dict): optional params to route_or_uri

        Returns:
            SReply: reply object
        """
        return self._do_req(
            route_or_uri,
            params=params,
            query=query,
            op=self._get,
            raw_response=raw_response,
            **kwargs,
        )

    def sr_get_json(self, route_or_uri, params=None, query=None, **kwargs):
        """Gets a request to route_or_uri to server

        Args:
            route_or_uri (str): identifies route in schema-common.json
            params (dict): optional params to route_or_uri
            query (dict): query to be added to uri
            headers (dict): headers to apply (in kwargs)

        Returns:
            object: Parsed JSON result
        """
        return self._do_req(
            route_or_uri,
            params=params,
            query=query,
            op=self._get,
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
        return self._do_req(
            "root",
            params={"path_info": self.sr_sim_type},
            query=None,
            op=self._get,
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
        self._uid_clear()
        self.sr_sim_type_set(sim_type)
        self.cookie_jar.clear()
        # Get a cookie
        self.sr_get("authState")
        self.sr_get("authGuestLogin", {"simulation_type": self.sr_sim_type})
        return self._uid_verify_and_save()

    def sr_logout(self):
        """Logout but leave cookie in place

        Returns:
            object: self
        """
        self._uid_clear()
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
        kwargs["json"] = data
        return self._do_req(
            route_or_uri,
            params=params,
            query={},
            op=self._post,
            raw_response=raw_response,
            **kwargs,
        )

    def sr_post_form(
        self, route_or_uri, data, params=None, raw_response=False, file=None, **kwargs
    ):
        """Posts form data to route_or_uri to server with data

        Args:
            route_or_uri (str): identifies route in schema-common.json
            data (dict): content to post
            params (dict): optional params to route_or_uri
            file (object): if str, will look in data_dir, else assumed py.path

        Returns:
            object: Parsed JSON result
        """
        from pykern import pkunit, pkconfig

        k = PKDict(data=data, **kwargs)
        if file:
            p = file
            if isinstance(p, pkconfig.STRING_TYPES):
                p = pkunit.data_dir().join(p)
            k.file_handle = open(str(p), "rb")
        return self._do_req(
            route_or_uri,
            params,
            query=PKDict(),
            op=self._post,
            raw_response=raw_response,
            **k,
        )

    def sr_run_sim(self, data, model, expect_completed=True, timeout=20, **post_args):
        from pykern import pkunit
        from pykern.pkdebug import pkdlog, pkdexc
        from sirepo import job
        import time

        # Needs to be specific
        def _assert_no_mpiexec():
            """Ensure mpiexec is not running in work_dir"""
            import subprocess

            o = pkcompat.from_bytes(
                subprocess.check_output(["ps", "axwwe"], stderr=subprocess.STDOUT),
            )
            d = str(pkunit.work_dir())
            o = list(
                filter(
                    # regex is problematic because "d" may have specials so just do this
                    lambda x: "mpiexec" in x and d in x,
                    o.split("\n"),
                ),
            )
            if o:
                pkdlog('found "mpiexec" after cancel in ps={}', "\n".join(o))
                # this exception won't be seen because in finally
                raise AssertionError("cancel failed")

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
            for _ in range(timeout):
                r = self.sr_post("runStatus", r.nextRequest)
                if r.state in job.EXIT_STATUSES:
                    cancel = None
                    break
                pkunit.pkok(
                    "nextRequest" in r,
                    "nextRequest missing from reply={}",
                    r,
                )
                pkdlog("reply.state={}", r.get("state"))
                # not asyncio.sleep: in a synchronous unit test
                time.sleep(1)
            else:
                pkunit.pkok(not expect_completed, "did not complete: runStatus={}", r)
            if expect_completed:
                pkunit.pkeq("completed", r.state, "reply={}", r)
            return r
        finally:
            if cancel:
                pkdlog("runCancel")
                self.sr_post("runCancel", cancel)
            _assert_no_mpiexec()

    def sr_sbatch_animation_run(self, sim_name, compute_model, reports, **kwargs):
        self.sr_sbatch_login(compute_model, sim_name)
        self.sr_animation_run(
            self.sr_sim_data(sim_name, compute_model=compute_model),
            compute_model,
            reports,
            # Things take longer with Slurm.
            timeout=90,
            **kwargs,
        )

    def sr_sbatch_creds(self):
        return PKDict(sbatchCredentials=_cfg().sbatch.copy())

    def sr_sbatch_login(self, compute_model, sim_name):
        from pykern.pkunit import pkexcept

        if self.sr_sbatch_logged_in:
            return
        d = self.sr_sim_data(sim_name, compute_model=compute_model)
        with pkexcept("SRException.*no-creds"):
            # Must try to run sim first to seed job_supervisor.db
            self.sr_run_sim(d, compute_model, expect_completed=False)
        self.sr_post(
            "sbatchLogin",
            PKDict(
                report=compute_model,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            ).pkupdate(self.sr_sbatch_creds()),
            raw_response=True,
        ).assert_success()
        self.sr_sbatch_logged_in = True

    def sr_sim_data(self, sim_name=None, sim_type=None, compute_model=None):
        """Return simulation data by name

        Args:
            sim_name (str): case sensitive name ['Scooby Doo']
            sim_type (str): app ['myapp']
            compute_model (str): what model is selected to set jobRunMode [None]

        Returns:
            dict: data
        """
        from pykern import pkunit
        from pykern.pkdebug import pkdpretty, pkdp

        self.sr_sim_type_set(sim_type)
        if not sim_name:
            sim_name = SR_SIM_NAME_DEFAULT
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
        if compute_model and self.sr_job_run_mode:
            res.models[compute_model].jobRunMode = self.sr_job_run_mode
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

    def sr_thread_join(self, *names):
        from pykern import pkunit

        res = PKDict()
        for n in names or list(self._threads.keys()):
            t = self._threads[n]
            t.join()
            del self._threads[n]
            pkunit.pkok(t.sr_ok, f"thread={n} got an exception")
            res[n] = t.sr_res
        return res

    def sr_thread_start(self, name, op, **kwargs):
        t = self._threads[name] = _Thread(
            op=op,
            kwargs=PKDict(kwargs).pkupdate(fc=self.sr_clone()),
        )
        t.start()

    def sr_user_dir(self, uid=None):
        """User's db dir"""
        if not uid:
            uid = self.sr_auth_state().uid
        return self.sr_db_dir().join("user", uid)

    def timeout_secs(self):
        if not hasattr(self, "_timeout_secs"):
            self._timeout_secs = round(_cfg().cpu_div * 0.5)
        return self._timeout_secs

    def _do_req(self, route_or_uri, params, query, op, raw_response, **kwargs):
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
            r = op(u, **kwargs)
            pkdc(
                "status={} data={}",
                r.status_code,
                "<snip-file>" if "download-data-file" in u else r.data,
            )
            res = r.process(raw_response)
            if r.status_code in (301, 302, 303, 305, 307, 308):
                if kwargs.get("redirect", True):
                    # Execute the redirect
                    pkdlog(
                        "redirect status={} location={}",
                        r.status_code,
                        r.header_get("Location"),
                    )
                    return self._do_req(
                        r.header_get("Location"),
                        params=None,
                        query=None,
                        op=self._get,
                        raw_response=raw_response,
                        __redirects=redirects,
                    )
            return res
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

    def _get(self, uri, **kwargs):
        return self._requests_op("get", uri, kwargs=PKDict(kwargs))

    def _post(self, uri, data=None, json=None, file_handle=None, **kwargs):
        assert (data is None) != (json is None)
        k = PKDict(kwargs)
        if data is not None:
            k.data = data
        else:
            k.json = json
        if file_handle is not None:
            k.files = PKDict(file=file_handle)
        return self._requests_op("post", uri, k)

    def _requests_op(self, op, uri, kwargs):
        from pykern.pkdebug import pkdlog, pkdexc, pkdc, pkdp
        from sirepo import const

        if hasattr(self, "_websocket") and not kwargs.get("want_http"):
            r = self._websocket.send(op, uri, **kwargs)
            if r is not None:
                return r
        if "headers" not in kwargs:
            kwargs.headers = PKDict()
        kwargs.headers.setdefault(
            "User-Agent",
            f"{const.SRUNIT_USER_AGENT} {pykern.pkinspect.caller()}",
        )
        u = self._uri(uri)
        # Delete all of our kwargs
        kwargs.pkdel("want_http")
        kwargs.pkdel("__redirects")
        kwargs.pkdel("redirect")
        try:
            return _HTTPResponse(
                getattr(self._session, op)(u, allow_redirects=False, **kwargs),
                self,
            )
        except requests.exceptions.ConnectionError as e:
            from pykern.pkdebug import pkdlog

            pkdlog("op={} uri={} headers={}", op, u, kwargs.headers)
            raise

    def _uid_clear(self):
        self.sr_uid = None

    def _uid_verify_and_save(self):
        self.sr_uid = self.sr_auth_state(
            needCompleteRegistration=False, isLoggedIn=True
        ).uid
        return self.sr_uid

    def _uri(self, uri):
        from pykern.pkdebug import pkdp

        u = urllib.parse.urlparse(uri)
        if u.scheme:
            return uri
        return self.http_prefix + uri


class _Response:
    def assert_http_redirect(self, expect_re):
        from pykern import pkunit, pkdebug

        self.assert_http_status(302)
        pkunit.pkre(expect_re, self.header_get("Location"))

    def assert_http_status(self, expect):
        from pykern import pkunit

        pkunit.pkeq(
            expect,
            self.status_code,
            "expect={} status={} data={}",
            expect,
            self.status_code,
            self.data,
        )

    def assert_success(self):
        from sirepo import util

        self.assert_http_status(200)
        d = self._assert_not_exception()
        if isinstance(d, dict) and (
            d.get("state") == "error" or d.get("error") is not None
        ):
            raise util.Error(
                d.get("error", "internal error"),
                "reply in error reply={}",
                d,
            )
        return d

    def change_to_redirect(self, uri):
        self._headers = PKDict(Location=uri)
        self.data = ""
        self.mimetype = "text/plain"
        self.status_code = 302
        return self

    def header_get(self, name):
        return self._headers[name]

    def _convert_http_status(self, sr_args):
        """set self.status_code

        Returns:
            bool: True if is a redirect
        """
        from pykern import pkdebug
        from sirepo import uri

        if sr_args.routeName == "httpException":
            self.status_code = sr_args.params.code
            return False
        elif sr_args.routeName == "httpRedirect":
            self.change_to_redirect(sr_args.params.uri)
            return True
        elif not uri.is_sr_exception_only(
            self._test_client.sr_sim_type, sr_args.routeName
        ):
            self.change_to_redirect(
                uri.local_route(
                    self._test_client.sr_sim_type, sr_args.routeName, sr_args.params
                )
            )
            return True
        return False

    def _maybe_json_decode(self):
        from pykern import pkjson

        if self.mimetype == pkjson.MIME_TYPE:
            return pkjson.load_any(self.data)
        return self.data


class _HTTPResponse(_Response):
    def __init__(self, reply, test_client):
        from pykern.pkdebug import pkdlog, pkdexc, pkdc, pkdp

        self.status_code = reply.status_code
        self.data = reply.content
        self._test_client = test_client
        c = reply.headers.get("content-type")

        self.mimetype = c.split(";")[0].strip() if c else ""
        self._headers = reply.headers

    def process(self, raw_response):
        from pykern import pkdebug
        from sirepo import util, reply

        # Emulate code in sirepo.js to deal with redirects
        if self.status_code == 200:
            if self.mimetype == "text/html":
                m = _JAVASCRIPT_REDIRECT_RE.search(pkcompat.from_bytes(self.data))
                if m:
                    if m.group(1).endswith("#/error"):
                        raise util.Error(
                            PKDict(error="server error uri={}".format(m.group(1))),
                        )
                    return self.change_to_redirect(m.group(1))
            else:
                d = self._maybe_json_decode()
                if (
                    isinstance(d, dict)
                    and d.get("state") == reply.SR_EXCEPTION_STATE
                    and self._convert_http_status(d.srException)
                ):
                    return self
        if raw_response:
            return self
        return self._assert_not_exception()

    def _assert_not_exception(self):
        from pykern import pkjson
        from sirepo import reply, util

        d = self._maybe_json_decode()
        if isinstance(d, dict) and d.get("state") == reply.SR_EXCEPTION_STATE:
            # Treat SRException as a real exception (so we don't ignore them)
            raise util.SRException(
                d.srException.routeName,
                d.srException.params,
            )
        if self.status_code != 200:
            raise util.Error(
                f"unexpected status={self.status_code}",
                "reply={}",
                self.data,
            )
        return d


class _Thread(threading.Thread):
    def __init__(self, op, kwargs):
        super().__init__()
        self.sr_ok = False
        self._op = op
        self._kwargs = kwargs

    def run(self):
        self.sr_res = self._op(**self._kwargs)
        self.sr_ok = True


class _WebSocket:

    # /download is special below
    _HTTP_RE = re.compile(r"^(?:/download-|https?:)")
    _ANCHOR_RE = re.compile(r"(/.*?)#")

    def __init__(self, test_client):
        self._enabled = False
        self._connection = None
        self.test_client = test_client
        self._is_async = None

    def save_cookie_hash(self):
        self._cookie_hash = self._hash_cookies()

    def send(self, op, uri, headers=None, data=None, files=None, json=None, **kwargs):
        from pykern.pkdebug import pkdp, pkdlog
        import msgpack
        from sirepo import const
        from sirepo import uri as sirepo_uri

        def _combine_req(encoded_uri):
            m = PKDict(
                header=PKDict(
                    kind=const.SCHEMA_COMMON.websocketMsg.kind.httpRequest,
                    uri=sirepo_uri.decode_to_str(encoded_uri),
                    version=const.SCHEMA_COMMON.websocketMsg.version,
                    # POSIT: uri_router will look for this in_dev_mode
                    srunit_caller=str(pykern.pkinspect.caller()),
                ),
            )
            if op == "get":
                assert (
                    data is None and json is None and files is None
                ), f"GET does not support content uri={uri}"
            else:
                assert (
                    data is None or json is None
                ), f"only json or data may be supplied uri={uri}"
                m.content = json if data is None else data
                if files:
                    m.attachment = PKDict(
                        blob=files.file.read(),
                        filename=os.path.basename(files.file.name),
                    )
            return m

        def _must_be_http(uri):
            # POSIT: /auth- match like sirepo.js msgRouter and https?:
            # for browser click on email msg. If there are headers,
            # it's basic auth. /download is special, because we
            # don't have a way of saving a file (easily) in sirepo.js.
            if headers:
                if not headers.get("Authorization"):
                    raise AssertionError(f"restricted use of headers={headers}")
                # basic auth
                return True
            if self._HTTP_RE.search(uri):
                return True
            if not self._enabled:
                self.start()
            if self._cookie_hash != self._hash_cookies():
                # Cookies have changed via http so need to reset websocket state
                self.stop()
                return True
            return False

        if _must_be_http(uri):
            pkdlog("via http: uri={} websocket.enabled={}", uri, self._enabled)
            return None
        assert uri[0] == "/", f"uri={uri} must begin with '/'"
        m = self._ANCHOR_RE.search(uri)
        return self._send(_combine_req(m.group(1) if m else uri))

    def start(self):
        assert not self._enabled
        self.save_cookie_hash()
        self._enabled = True

    def stop(self):
        if not self._enabled:
            return
        c = self._connection
        self._connection = None
        self._enabled = False
        self.req_seq = None
        if c:
            c.close()

    def _hash_cookies(self):
        """Reaches inside cookiejar. No other way..."""
        rv = 0
        for d, domains in self.test_client.cookie_jar._cookies.items():
            rv += hash(d)
            for p, paths in domains.items():
                rv += hash(p)
                for n, c in paths.items():
                    rv += hash(n) + hash(c.value)
        return rv

    def _send(self, msg):
        from websockets.sync import client
        from sirepo import job

        def _connect():
            r = requests.Request(
                url=self.test_client.http_prefix + "/ws",
                cookies=self.test_client.cookie_jar,
            ).prepare()
            self._connection = client.connect(
                r.url.replace("http", "ws"),
                additional_headers=r.headers,
                max_size=job.cfg().max_message_bytes,
            )
            self.req_seq = 1

        if not self._connection:
            _connect()
        self.req_seq += 1
        msg.header.reqSeq = self.req_seq
        self._connection.send(_WebSocketRequest(msg).buf)
        for _ in range(10):
            r = _WebSocketResponse(
                self._connection.recv(timeout=self.test_client.timeout_secs()),
                msg,
                self,
            )
            if not r.is_async_msg:
                return r
        raise AssertionError("too many asyncMsg _WebSocketResponses")


class _WebSocketRequest:
    def __init__(self, msg):
        import msgpack

        p = msgpack.Packer(autoreset=False)
        p.pack(msg.header)
        for x in "content", "attachment":
            if x in msg:
                p.pack(msg[x])
        self.buf = p.bytes()
        p.reset()


class _WebSocketResponse(_Response):
    def __init__(self, msg, req_msg, websocket):
        from pykern.pkdebug import pkdp
        from sirepo import const, util
        import msgpack

        self._req_msg = req_msg
        self._websocket = websocket
        self._test_client = websocket.test_client
        u = msgpack.Unpacker(object_pairs_hook=pkcollections.object_pairs_hook)
        u.feed(msg)
        h = u.unpack()
        self.data = u.unpack() if u.tell() < len(msg) else None
        assert (
            const.SCHEMA_COMMON.websocketMsg.version == h.version
        ), f"invalid msg.version={h.version}"
        self.is_async_msg = const.SCHEMA_COMMON.websocketMsg.kind.asyncMsg == h.kind
        if self.is_async_msg:
            getattr(self, "_async_msg_" + h.method)(self.data)
            return
        assert (
            req_msg.header.reqSeq == h.reqSeq
        ), f"invalid msg.reqSeq={h.reqSeq} expect={req_msg.header.reqSeq}"
        self._headers = PKDict()
        self.mimetype = "application/octet"
        self.status_code = 200
        if const.SCHEMA_COMMON.websocketMsg.kind.httpReply == h.kind:
            self._sr_exception = None
        elif const.SCHEMA_COMMON.websocketMsg.kind.srException == h.kind:
            self._sr_exception = util.SRException(self.data.routeName, self.data.params)
        else:
            raise AssertionError(f"invalid msg.kind={h.kind}")

    def assert_http_status(self, expect):
        from pykern import pkunit, pkdebug

        if expect != 200 and not self._sr_exception:
            pkunit.pkfail("not an srException data={}", self.data)
        super().assert_http_status(expect)

    def header_get(self, name):
        return self._headers[name]

    def process(self, raw_response):
        from sirepo import util, reply

        def _data_to_json():
            from pykern import pkjson

            if not isinstance(self.data, (dict, list)):
                return self
            if self._sr_exception:
                self.data = PKDict(
                    state=reply.SR_EXCEPTION_STATE,
                    srException=self.data,
                )
            # Opposite of what you expect: raw_response is encoded json so need to encode
            self.mimetype = pkjson.MIME_TYPE
            self.data = pkjson.dump_pretty(self.data, pretty=False)
            return self

        if not self._sr_exception:
            if raw_response:
                return _data_to_json()
            return self.data
        if self._convert_http_status(self._sr_exception.sr_args):
            return self
        if raw_response:
            return _data_to_json()
        # Always raises, because _sr_exception is truthy at this point
        self._assert_not_exception()

    def _assert_not_exception(self):
        from sirepo import util
        from pykern.pkdebug import pkdp

        # All websocket errors are sr exceptions
        if self._sr_exception:
            raise self._sr_exception
        if self.status_code != 200:
            raise util.Error(f"unexpected status={self.status_code}", "reply={}", d)
        return self._maybe_json_decode()

    def _async_msg_setCookies(self, content):
        self._test_client.cookie_jar.extract_cookies(
            response=PKDict(info=lambda: PKDict(get_all=lambda x, y: content)),
            request=PKDict(
                unverifiable=False,
                get_full_url=lambda: self._test_client.http_prefix
                + self._req_msg.header.uri,
            ),
        )
        self._websocket.save_cookie_hash()


def _cfg():
    global __cfg

    if __cfg:
        return __cfg

    from pykern import pkconfig
    import getpass

    u = getpass.getuser()
    __cfg = pkconfig.init(
        # 50 is based on a 2.2 GHz server
        cpu_div=(50, int, "cpu speed divisor to compute timeouts"),
        sbatch=dict(
            password=(u, str, "password to login to sbatch"),
            username=(u, str, "user to login to sbatch"),
        ),
    )
    return __cfg
