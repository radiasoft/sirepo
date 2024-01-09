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
    return auth_fc_module


@pytest.fixture(scope="module")
def auth_fc_module(request):
    with _auth_client_module(request) as c:
        yield c


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


@pytest.fixture(scope="function")
def new_user_fc(request, fc_module):
    return _fc(request, fc_module, new_user=True)


def pytest_collection_modifyitems(session, config, items):
    """Restrict which tests are running"""
    from pykern.pkcollections import PKDict
    import importlib
    import os
    from sirepo import feature_config

    s = PKDict(
        elegant="sdds",
        srw="srwpy.srwl_bl",
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
        c = [x for x in feature_config.FOSS_CODES if x in i.name]
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


@contextlib.contextmanager
def _auth_client_module(request):
    from pykern.pkcollections import PKDict

    cfg = PKDict(
        SIREPO_AUTH_BASIC_PASSWORD="pass",
        SIREPO_AUTH_BASIC_UID="dev-no-validate",
        SIREPO_SMTP_FROM_EMAIL="x@x.x",
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

    with _subprocess_start(request, fc_args=PKDict(cfg=cfg)) as c:
        yield c


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


def _fc(request, fc_module, new_user=False):
    """HTTP client based logged in to specific code of test

    Defaults to myapp.
    """
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

    def _check_port(port):
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((_LOCALHOST, int(port)))
        return str(port)

    for p in random.sample(const.TEST_PORT_RANGE, 100):
        try:
            return _check_port(p)
        except Exception:
            pass
    raise AssertionError(
        f"ip={_LOCALHOST} unable to bind to port in range={const.TEST_PORT_RANGE}"
    )


def _sim_type(request):
    from sirepo import feature_config

    for c in feature_config.FOSS_CODES:
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
    cfg.SIREPO_PKCLI_SERVICE_PORT = _port()
    for x in "DRIVER_LOCAL", "DRIVER_DOCKER", "API", "DRIVER_SBATCH":
        cfg[f"SIREPO_JOB_{x}_SUPERVISOR_URI"] = f"http://{_LOCALHOST}:{p}"
    if sbatch_module:
        cfg.pkupdate(SIREPO_SIMULATION_DB_SBATCH_DISPLAY="testing@123")
    env.pkupdate(**cfg)

    from sirepo import srunit

    c = None
    u = [env.SIREPO_PKCLI_JOB_SUPERVISOR_PORT]
    c = srunit.http_client(
        env=env,
        empty_work_dir=fc_args.empty_work_dir,
        job_run_mode="sbatch" if sbatch_module else None,
        sim_types=fc_args.sim_types,
        port=env.SIREPO_PKCLI_SERVICE_PORT,
    )
    u.append(c.port)
    t = fc_args.sim_types
    if isinstance(t, (tuple, list)):
        t = ":".join(t)
    cfg.SIREPO_FEATURE_CONFIG_SIM_TYPES = t
    for i in u:
        subprocess.run(["kill -9 $(lsof -t -i :" + i + ") >& /dev/null"], shell=True)
    if sbatch_module:
        # must be performed after fc initialized so work_dir is configured
        _config_sbatch_supervisor_env(env)
    return (env, c)


@contextlib.contextmanager
def _subprocess_start(request, fc_args):
    from pykern import pkunit, pkjson
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog, pkdp
    from sirepo import srunit
    import time

    fc_args.pksetdefault(
        cfg=PKDict,
        sim_types=None,
        append_package=None,
        empty_work_dir=True,
    )

    def _ping_supervisor(uri):
        l = None
        for _ in range(100):
            try:
                r = requests.post(uri, json=None)
                r.raise_for_status()
                d = pkjson.load_any(r.text)
                if d.state == "ok":
                    return
                raise RuntimeError(f"state={r.get('state')}")
            except Exception as e:
                l = e
                time.sleep(0.3)
        pkunit.restart_or_fail("start failed uri={} exception={}", uri, l)

    def _subprocess(cmd):
        p.append(subprocess.Popen(cmd, env=env, cwd=wd))

    env, c = _subprocess_setup(request, fc_args)
    wd = pkunit.work_dir()
    p = []
    try:
        for k in sorted(env.keys()):
            if k.endswith("_PORT"):
                pkdlog("{}={}", k, env[k])
        _subprocess(("sirepo", "service", "server"))
        # allow db to be created
        time.sleep(0.5)
        _subprocess(("sirepo", "job_supervisor"))
        _ping_supervisor(c.http_prefix + "/job-supervisor-ping")
        from sirepo import template
        from pykern import pkio

        if template.is_sim_type("srw"):
            pkio.unchecked_remove(
                "~/src/radiasoft/sirepo/sirepo/package_data/template/srw/predefined.json"
            )
            template.import_module("srw").get_predefined_beams()
        yield c
    finally:
        import sys

        for x in p:
            x.terminate()
            x.wait()
