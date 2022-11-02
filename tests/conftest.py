import contextlib
import os
import pytest
import requests
import subprocess

#: Convenience constant
_LOCALHOST = "127.0.0.1"
#: Maximum time an individual test case (function) can run
MAX_CASE_RUN_SECS = int(os.getenv("SIREPO_CONFTEST_MAX_CASE_RUN_SECS", 120))


@pytest.fixture(scope="function")
def auth_fc(auth_fc_module):
    # set the sentinel
    auth_fc_module.cookie_jar.clear()
    auth_fc_module.sr_get_root()
    auth_fc_module.sr_email_confirm = email_confirm
    return auth_fc_module


@pytest.fixture(scope="module")
def auth_fc_module(request):
    with _auth_client_module(request) as c:
        yield c


def email_confirm(fc, resp, display_name=None):
    import re
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog

    fc.sr_get(resp.uri)
    pkdlog(resp.uri)
    m = re.search(r"/(\w+)$", resp.uri)
    assert bool(m)
    r = PKDict(token=m.group(1))
    if display_name:
        r.displayName = display_name
    fc.sr_post(
        resp.uri,
        r,
        raw_response=True,
    )


@pytest.fixture(scope="function")
def fc(request, fc_module):
    return _fc(request, fc_module)


@pytest.fixture(scope="module")
def fc_module(request):
    from pykern.pkcollections import PKDict

    a = _sirepo_args(request, "fc_module", PKDict())
    if "setup_func" in a:
        a.setup_func()
    with _subprocess_start(request, fc_args=a) as c:
        yield c


@pytest.fixture
def import_req(request):
    def w(path):
        import sirepo.srunit
        import sirepo.http_request

        with sirepo.srunit.quest_start() as qcall:
            req = qcall.parse_params(
                filename=path.basename,
                folder="/import_test",
                template=True,
                type=_sim_type(request),
            )
            # Supports read() for elegant and zgoubi
            req.file_stream = path
            return req

    return w


@pytest.fixture(scope="function")
def new_user_fc(request, fc_module):
    return _fc(request, fc_module, new_user=True)


def pytest_collection_modifyitems(session, config, items):
    """Restrict which tests are running"""
    from pykern.pkcollections import PKDict
    import importlib
    import os
    import sirepo.feature_config

    s = PKDict(
        elegant="sdds",
        srw="srwl_bl",
        synergia="synergia",
        warp="warp",
    )
    codes = set()
    import_fail = PKDict()
    res = set()
    skip_list = os.environ.get("SIREPO_PYTEST_SKIP", "").split(":")
    slurm_not_installed = _slurm_not_installed()
    for i in items:
        if i.fspath.purebasename in skip_list:
            i.add_marker(pytest.mark.skip(reason="SIREPO_PYTEST_SKIP"))
            continue
        if "sbatch" in i.fspath.basename and slurm_not_installed:
            i.add_marker(pytest.mark.skip(reason="slurm not installed"))
            continue
        c = [x for x in sirepo.feature_config.FOSS_CODES if x in i.name]
        if not c:
            continue
        c = c[0]
        if c in import_fail:
            i.add_marker(import_fail[c])
            continue
        m = s.get(c)
        try:
            if m:
                importlib.import_module(m)
        except Exception:
            import_fail[c] = pytest.mark.skip(reason="unable to import={}".format(m))
            i.add_marker(import_fail[c])
            continue
        codes.add(c)
    if not codes:
        return
    codes.add("myapp")
    import sirepo.srunit

    sirepo.srunit.CONFTEST_DEFAULT_CODES = ":".join(codes)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, *args, **kwargs):
    import signal
    from pykern import pkunit

    def _timeout(*args, **kwargs):
        signal.signal(signal.SIGALRM, _timeout_failed)
        signal.alarm(1)
        pkunit.pkfail("MAX_CASE_RUN_SECS={} exceeded", MAX_CASE_RUN_SECS)

    def _timeout_failed(*args, **kwargs):
        import os
        import sys
        from pykern.pkdebug import pkdlog

        pkdlog("failed to die after timeout (pkfail)")
        os.killpg(os.getpgrp(), signal.SIGKILL)

    # Seems to be the only way to get the module under test
    m = item._request.module
    is_new = m != pkunit.module_under_test

    if is_new:
        signal.signal(signal.SIGALRM, _timeout)
    pkunit.module_under_test = m
    signal.alarm(MAX_CASE_RUN_SECS)
    if is_new:
        from pykern import pkio

        pkio.unchecked_remove(pkunit.work_dir())


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    config._parser.parse_setoption(
        # run each test file in a separate process
        # the native trace works better, e.g. for emacs
        ["--tb=native"],
        config.option,
        namespace=config.option,
    )
    config.addinivalue_line("markers", "sirepo_args: pass parameters to fixtures")


@pytest.fixture
def uwsgi_module(request):
    with _auth_client_module(request, uwsgi=True) as c:
        yield c


@contextlib.contextmanager
def _auth_client_module(request, uwsgi=False):
    import sirepo.srunit
    from pykern.pkcollections import PKDict

    cfg = PKDict(
        SIREPO_AUTH_BASIC_PASSWORD="pass",
        SIREPO_AUTH_BASIC_UID="dev-no-validate",
        SIREPO_SMTP_FROM_EMAIL="x",
        SIREPO_SMTP_FROM_NAME="x",
        SIREPO_SMTP_PASSWORD="x",
        SIREPO_SMTP_SERVER="dev",
        SIREPO_SMTP_USER="x",
        SIREPO_AUTH_GITHUB_CALLBACK_URI="/uri",
        SIREPO_AUTH_GITHUB_KEY="key",
        SIREPO_AUTH_GITHUB_SECRET="secret",
        SIREPO_AUTH_GUEST_EXPIRY_DAYS="1",
        SIREPO_AUTH_METHODS="basic:email:guest",
        SIREPO_FEATURE_CONFIG_API_MODULES="status",
    )
    if "email3_test" in str(request.fspath.purebasename):
        cfg.SIREPO_AUTH_METHODS += ":github"
    else:
        cfg.SIREPO_AUTH_DEPRECATED_METHODS = "github"
    from pykern import pkconfig

    pkconfig.reset_state_for_testing(cfg)

    with _subprocess_start(request, fc_args=PKDict(cfg=cfg, uwsgi=uwsgi)) as c:
        yield c


def _check_port(port):
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((_LOCALHOST, int(port)))


def _config_sbatch_supervisor_env(env):
    from pykern.pkcollections import PKDict
    import os
    import pykern.pkio
    import pykern.pkunit
    import re
    import socket

    h = socket.gethostname()
    k = pykern.pkio.py_path("~/.ssh/known_hosts").read()
    m = re.search("^{}.*$".format(h), k, re.MULTILINE)
    assert bool(m), "You need to ssh into {} to get the host key".format(h)

    env.pkupdate(
        SIREPO_JOB_DRIVER_MODULES="local:sbatch",
        SIREPO_JOB_DRIVER_SBATCH_CORES=os.getenv(
            "SIREPO_JOB_DRIVER_SBATCH_CORES",
            "2",
        ),
        SIREPO_JOB_DRIVER_SBATCH_HOST=h,
        SIREPO_JOB_DRIVER_SBATCH_HOST_KEY=m.group(0),
        SIREPO_JOB_DRIVER_SBATCH_SIREPO_CMD="sirepo",
        SIREPO_JOB_DRIVER_SBATCH_SRDB_ROOT=str(
            pykern.pkunit.work_dir().join("/{sbatch_user}/sirepo")
        ),
        SIREPO_JOB_SUPERVISOR_SBATCH_POLL_SECS="2",
    )


def _job_supervisor_check(env):
    _check_port(env.SIREPO_PKCLI_JOB_SUPERVISOR_PORT)


def _fc(request, fc_module, new_user=False):
    """Flask client based logged in to specific code of test

    Defaults to myapp.
    """
    import sirepo.srunit

    if fc_module.sr_uid and new_user:
        fc_module.sr_logout()

    c = _sim_type(request)
    if fc_module.sr_uid:
        if fc_module.sr_sim_type != c:
            fc_module.sr_get_root(sim_type=c)
    else:
        fc_module.sr_login_as_guest(sim_type=c)
    return fc_module


def _port():
    import random
    from sirepo import const

    for p in random.sample(const.TEST_PORT_RANGE, 100):
        try:
            _check_port(p)
            return str(p)
        except Exception:
            pass
    raise AssertionError(f"ip={_LOCALHOST} unable to allocate port")


def _sim_type(request):
    import sirepo.feature_config

    for c in sirepo.feature_config.FOSS_CODES:
        f = request.function
        n = getattr(f, "func_name", None) or getattr(f, "__name__")
        if c in n or c in str(request.fspath.purebasename):
            return c
    return "myapp"


def _slurm_not_installed():
    try:
        subprocess.check_output(("sbatch", "--help"))
    except OSError:
        return True
    return False


def _sirepo_args(request, name, default):
    m = request.node.get_closest_marker("sirepo_args")
    res = None
    if m and m.kwargs and name in m.kwargs:
        res = m.kwargs.get(name)
    return default if res is None else res


def _subprocess_setup(request, fc_args):
    """setup the supervisor"""
    import os
    from pykern.pkcollections import PKDict

    sbatch_module = "sbatch" in request.module.__name__
    env = PKDict(os.environ)
    cfg = fc_args.cfg
    from pykern import pkunit
    from pykern import pkio

    p = _port()
    cfg.pkupdate(
        PYKERN_PKDEBUG_WANT_PID_TIME="1",
        SIREPO_PKCLI_JOB_SUPERVISOR_IP=_LOCALHOST,
        SIREPO_PKCLI_JOB_SUPERVISOR_PORT=p,
        SIREPO_PKCLI_SERVICE_IP=_LOCALHOST,
        SIREPO_SRDB_ROOT=str(pkio.mkdir_parent(pkunit.work_dir().join("db"))),
    )
    if fc_args.uwsgi:
        cfg.SIREPO_PKCLI_SERVICE_PORT = _port()
        cfg.SIREPO_PKCLI_SERVICE_NGINX_PROXY_PORT = _port()
    for x in "DRIVER_LOCAL", "DRIVER_DOCKER", "API", "DRIVER_SBATCH":
        cfg["SIREPO_JOB_{}_SUPERVISOR_URI".format(x)] = "http://{}:{}".format(
            _LOCALHOST, p
        )
    if sbatch_module:
        cfg.pkupdate(SIREPO_SIMULATION_DB_SBATCH_DISPLAY="testing@123")
    env.pkupdate(**cfg)

    import sirepo.srunit

    c = None
    u = [env["SIREPO_PKCLI_JOB_SUPERVISOR_PORT"]]
    if fc_args.uwsgi:
        c = sirepo.srunit.UwsgiClient(env)
        u.append(env["SIREPO_PKCLI_SERVICE_NGINX_PROXY_PORT"])
    else:
        c = sirepo.srunit.flask_client(
            cfg=cfg,
            empty_work_dir=fc_args.empty_work_dir,
            job_run_mode="sbatch" if sbatch_module else None,
            sim_types=fc_args.sim_types,
        )

    for i in u:
        subprocess.run(["kill -9 $(lsof -t -i :" + i + ") >& /dev/null"], shell=True)

    if sbatch_module:
        # must be performed after fc initialized so work_dir is configured
        _config_sbatch_supervisor_env(env)

    _job_supervisor_check(env)
    return (env, c)


@contextlib.contextmanager
def _subprocess_start(request, fc_args):
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    import sirepo.srunit
    import time

    fc_args.pksetdefault(
        uwsgi=False,
        cfg=PKDict,
        sim_types=None,
        append_package=None,
        empty_work_dir=True,
    )

    def _post(uri, data):
        for _ in range(30):
            try:
                r = requests.post(uri, json=data)
                if r.status_code == 200:
                    return
            except requests.exceptions.ConnectionError:
                time.sleep(0.3)
        pkunit.pkfail("could not connect to {}", uri)

    def _subprocess(cmd):
        p.append(subprocess.Popen(cmd, env=env, cwd=wd))

    env, c = _subprocess_setup(request, fc_args)
    wd = pkunit.work_dir()
    p = []
    try:
        _subprocess(("sirepo", "job_supervisor"))
        _post(
            env["SIREPO_JOB_API_SUPERVISOR_URI"] + "/job-api-ping",
            PKDict(ping="echoedValue"),
        )
        if fc_args.uwsgi:
            for s in ("nginx-proxy", "uwsgi"):
                _subprocess(("sirepo", "service", s))
            _post(
                f'http://{_LOCALHOST}:{env["SIREPO_PKCLI_SERVICE_NGINX_PROXY_PORT"]}'
                f"/job-supervisor-ping",
                PKDict(simulationType=sirepo.srunit.SR_SIM_TYPE_DEFAULT),
            )
        from sirepo import feature_config, template
        from pykern import pkio

        if template.is_sim_type("srw"):
            pkio.unchecked_remove(
                "~/src/radiasoft/sirepo/sirepo/package_data/template/srw/predefined.json"
            )
            template.import_module("srw").get_predefined_beams()
        yield c
    finally:
        for x in p:
            x.terminate()
            x.wait()
