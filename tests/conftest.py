import contextlib
import os
import pytest
import re
import requests
import subprocess

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
    from sirepo import srunit_servers

    a = _sirepo_args(request, "fc_module", PKDict())
    if "setup_func" in a:
        a.setup_func()
    with srunit_servers.api_and_supervisor(request, fc_args=a) as c:
        yield c


@pytest.fixture(scope="module")
def sim_db_file_server(request):
    from sirepo import srunit_servers

    with srunit_servers.sim_db_file(request):
        yield None


@pytest.fixture(scope="function")
def new_user_fc(request, fc_module):
    return _fc(request, fc_module, new_user=True)


def pytest_collection_modifyitems(session, config, items):
    """Restrict which tests are running"""
    from pykern.pkcollections import PKDict
    import importlib
    import os
    from sirepo import feature_config

    def _slurm_not_installed():
        try:
            subprocess.check_output(("sbatch", "--help"))
        except OSError:
            return True
        return False

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

    def _timeout(*args, **kwargs):
        from pykern import pkunit

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
    signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(MAX_CASE_RUN_SECS)


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
    from sirepo import srunit_servers

    cfg = PKDict(
        SIREPO_AUTH_BASIC_PASSWORD="pass",
        SIREPO_AUTH_BASIC_UID="dev-no-validate",
        SIREPO_SMTP_FROM_EMAIL="x@x.x",
        SIREPO_SMTP_FROM_NAME="x",
        SIREPO_SMTP_PASSWORD="x",
        SIREPO_SMTP_SERVER="dev",
        SIREPO_SMTP_USER="x",
        SIREPO_AUTH_GUEST_EXPIRY_DAYS="1",
        SIREPO_AUTH_METHODS="basic:email:guest",
        SIREPO_FEATURE_CONFIG_API_MODULES="status",
    )
    from pykern import pkconfig

    pkconfig.reset_state_for_testing(cfg)

    with srunit_servers.api_and_supervisor(request, fc_args=PKDict(cfg=cfg)) as c:
        yield c


def _fc(request, fc_module, new_user=False):
    """HTTP client based logged in to specific code of test

    Defaults to myapp.
    """

    def _sim_type(request):
        from sirepo import feature_config

        f = request.function
        n = getattr(f, "func_name", None) or getattr(f, "__name__")
        for c in feature_config.FOSS_CODES:
            r = re.compile(rf"(?:^|_){c}($|_)")
            if r.search(n) or r.search(str(request.fspath.purebasename)):
                return c
        return "myapp"

    if fc_module.sr_uid and new_user:
        fc_module.sr_logout()

    c = _sim_type(request)
    if fc_module.sr_uid:
        if fc_module.sr_sim_type != c:
            fc_module.sr_get_root(sim_type=c)
    else:
        fc_module.sr_login_as_guest(sim_type=c)
    return fc_module


def _sirepo_args(request, name, default):
    m = request.node.get_closest_marker("sirepo_args")
    res = None
    if m and m.kwargs and name in m.kwargs:
        res = m.kwargs.get(name)
    return default if res is None else res
