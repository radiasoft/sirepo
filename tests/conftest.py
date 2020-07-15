import contextlib
import os
import pytest
import requests
import subprocess

#: Maximum time an individual test case (function) can run
MAX_CASE_RUN_SECS = int(os.getenv('SIREPO_CONFTEST_MAX_CASE_RUN_SECS', 120))


@pytest.fixture
def auth_fc(auth_fc_module):
    # set the sentinel
    auth_fc_module.cookie_jar.clear()
    auth_fc_module.sr_get_root()
    auth_fc_module.sr_email_confirm = email_confirm
    return auth_fc_module


@pytest.fixture
def auth_fc_module(request):
    with _auth_client_module(request) as c:
        yield c


def email_confirm(fc, resp, display_name=None):
    import re
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog

    fc.sr_get(resp.uri)
    pkdlog(resp.uri)
    m = re.search(r'/(\w+)$', resp.uri)
    assert bool(m)
    r = PKDict(token=m.group(1))
    if display_name:
        r.displayName = display_name
    fc.sr_post(
        resp.uri,
        r,
        raw_response=True,
    )


@pytest.fixture(scope='function')
def fc(request, fc_module):
    return _fc(request, fc_module)


@pytest.fixture(scope='module')
def fc_module(request, cfg=None):
    with _subprocess_start(request) as c:
        yield c


@pytest.fixture
def import_req(request):
    import flask

    flask.g = {}

    def w(path):
        import sirepo.http_request
        req = sirepo.http_request.parse_params(
            filename=path.basename,
            folder='/import_test',
            template=True,
            type=_sim_type(request),
        )
        # Supports read() for elegant and zgoubi
        req.file_stream = path
        return req

    return w


@pytest.fixture(scope='function')
def new_user_fc(request, fc_module):
    return _fc(request, fc_module, new_user=True)


def pytest_collection_modifyitems(session, config, items):
    """Restrict which tests are running"""
    import importlib
    import sirepo.feature_config
    from pykern.pkcollections import PKDict
    import os

    s = PKDict(
        elegant='sdds',
        srw='srwl_bl',
        synergia='synergia',
        warp='warp',
    )
    valid_codes = sirepo.feature_config.VALID_CODES
    codes = set()
    import_fail = PKDict()
    res = set()
    skip_list = os.environ.get('SIREPO_PYTEST_SKIP', '').split(':')
    slurm_not_installed = _slurm_not_installed()
    for i in items:
        if i.fspath.purebasename in skip_list:
            i.add_marker(pytest.mark.skip(reason="SIREPO_PYTEST_SKIP"))
            continue
        if 'sbatch' in i.fspath.basename and slurm_not_installed:
            i.add_marker(pytest.mark.skip(reason="slurm not installed"))
            continue
        c = [x for x in valid_codes if x in i.name]
        if not c:
            continue
        c = c[0]
        if c in import_fail:
            i.add_marker(import_fail[c])
            continue
        if c not in valid_codes:
            i.add_marker(
                pytest.mark.skip(
                    reason='skipping code={} not in valid_codes={}'.format(c, valid_codes),
                ),
            )
            continue
        try:
            m = s.get(c)
            if m:
                importlib.import_module(m)
        except Exception:
            import_fail[c] = pytest.mark.skip(reason='unable to import={}'.format(m))
            i.add_marker(import_fail[c])
            continue
        codes.add(c)
    if not codes:
        return
    codes.add('myapp')
    import sirepo.srunit
    sirepo.srunit.CONFTEST_DEFAULT_CODES = ':'.join(codes)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, *args, **kwargs):
    import signal
    from pykern import pkunit

    def _timeout(*args, **kwargs):
        signal.signal(signal.SIGALRM, _timeout_failed)
        signal.alarm(1)
        pkunit.pkfail('MAX_CASE_RUN_SECS={} exceeded', MAX_CASE_RUN_SECS)

    def _timeout_failed(*args, **kwargs):
        import os
        import sys
        from pykern.pkdebug import pkdlog

        pkdlog('failed to die after timeout (pkfail)')
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
        ['--tb=native'],
        config.option,
        namespace=config.option,
    )


@pytest.fixture
def uwsgi_module(request):
    with _auth_client_module(request, uwsgi=True) as c:
        yield c


@contextlib.contextmanager
def _auth_client_module(request, uwsgi=False):
    import sirepo.srunit
    from pykern.pkcollections import PKDict

    cfg = PKDict(
        SIREPO_AUTH_BASIC_PASSWORD='pass',
        SIREPO_AUTH_BASIC_UID='dev-no-validate',
        SIREPO_AUTH_EMAIL_FROM_EMAIL='x',
        SIREPO_AUTH_EMAIL_FROM_NAME='x',
        SIREPO_AUTH_EMAIL_SMTP_PASSWORD='x',
        SIREPO_AUTH_EMAIL_SMTP_SERVER='dev',
        SIREPO_AUTH_EMAIL_SMTP_USER='x',
        SIREPO_AUTH_GITHUB_CALLBACK_URI='/uri',
        SIREPO_AUTH_GITHUB_KEY='key',
        SIREPO_AUTH_GITHUB_SECRET='secret',
        SIREPO_AUTH_GUEST_EXPIRY_DAYS='1',
        SIREPO_AUTH_METHODS='basic:email:guest',
        SIREPO_FEATURE_CONFIG_API_MODULES='status',
    )
    if 'email3_test' in str(request.fspath.purebasename):
        cfg.SIREPO_AUTH_METHODS += ':github'
    else:
        cfg.SIREPO_AUTH_DEPRECATED_METHODS = 'github'
    from pykern import pkconfig
    pkconfig.reset_state_for_testing(cfg)

    from pykern import pkunit
    from pykern import pkio
    cfg['SIREPO_SRDB_ROOT'] = str(pkio.mkdir_parent(pkunit.work_dir().join('db')))
    with _subprocess_start(request, cfg=cfg, uwsgi=uwsgi) as c:
        yield c


def _config_sbatch_supervisor_env(env):
    from pykern.pkcollections import PKDict
    import os
    import pykern.pkio
    import pykern.pkunit
    import re
    import socket

    h = socket.gethostname()
    k = pykern.pkio.py_path('~/.ssh/known_hosts').read()
    m = re.search('^{}.*$'.format(h), k, re.MULTILINE)
    assert bool(m), \
        'You need to ssh into {} to get the host key'.format(h)

    env.pkupdate(
        SIREPO_JOB_DRIVER_MODULES='local:sbatch',
        SIREPO_JOB_DRIVER_SBATCH_CORES=os.getenv(
            'SIREPO_JOB_DRIVER_SBATCH_CORES',
            '2',
        ),
        SIREPO_JOB_DRIVER_SBATCH_HOST=h,
        SIREPO_JOB_DRIVER_SBATCH_HOST_KEY=m.group(0),
        SIREPO_JOB_DRIVER_SBATCH_SIREPO_CMD='sirepo',
        SIREPO_JOB_DRIVER_SBATCH_SRDB_ROOT=str(pykern.pkunit.work_dir().join(
            '/{sbatch_user}/sirepo'
        )),
        SIREPO_JOB_SUPERVISOR_SBATCH_POLL_SECS='2',
    )


def _job_supervisor_check(env):
    import socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind((env.SIREPO_PKCLI_JOB_SUPERVISOR_IP, int(env.SIREPO_PKCLI_JOB_SUPERVISOR_PORT)))
    except Exception:
        raise AssertionError(
            'job_supervisor still running on ip={} port={}'.format(
                env.SIREPO_PKCLI_JOB_SUPERVISOR_IP,
                env.SIREPO_PKCLI_JOB_SUPERVISOR_PORT,
            ),
        )
    finally:
        s.close()


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


def _sim_type(request):
    import sirepo.feature_config

    for c in sirepo.feature_config.VALID_CODES:
        f = request.function
        n = getattr(f, 'func_name', None) or getattr(f, '__name__')
        if c in n or c in str(request.fspath.purebasename):
            return c
    return 'myapp'


def _slurm_not_installed():
    try:
        subprocess.check_output(('sbatch', '--help'))
    except OSError:
        return True
    return False


def _subprocess_setup(request, cfg=None, uwsgi=False):
    """setup the supervisor"""
    import os
    from pykern.pkcollections import PKDict
    sbatch_module = 'sbatch' in request.module.__name__
    env = PKDict(os.environ)
    if not cfg:
        cfg = PKDict()
    i = '127.0.0.1'
    # different port than default so can run tests when supervisor running
    p = '8002'
    cfg.pkupdate(
        PYKERN_PKDEBUG_WANT_PID_TIME='1',
        SIREPO_PKCLI_JOB_SUPERVISOR_IP=i,
        SIREPO_PKCLI_JOB_SUPERVISOR_PORT=p,
    )
    for x in 'DRIVER_LOCAL', 'DRIVER_DOCKER', 'API', 'DRIVER_SBATCH':
        cfg['SIREPO_JOB_{}_SUPERVISOR_URI'.format(x)] = 'http://{}:{}'.format(i, p)
    if sbatch_module:
        cfg.pkupdate(SIREPO_SIMULATION_DB_SBATCH_DISPLAY='testing@123')
    env.pkupdate(**cfg)

    import sirepo.srunit
    c = None
    if uwsgi:
        c = sirepo.srunit.UwsgiClient()
    else:
        c = sirepo.srunit.flask_client(
            cfg=cfg,
            job_run_mode='sbatch' if sbatch_module else None,
        )

    if sbatch_module:
        # must be performed after fc initialized so work_dir is configured
        _config_sbatch_supervisor_env(env)

    import sirepo.srdb
    env.SIREPO_SRDB_ROOT = str(sirepo.srdb.root())

    _job_supervisor_check(env)
    return (env, c)


@contextlib.contextmanager
def _subprocess_start(request, cfg=None, uwsgi=False):
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    import sirepo.srunit
    import time

    env, c = _subprocess_setup(request, cfg, uwsgi)
    p = []
    try:
        if uwsgi:
            p = [
                subprocess.Popen(('sirepo', 'service', 'nginx-proxy'), env=env),
                subprocess.Popen(('sirepo', 'service', 'uwsgi'), env=env),
            ]
        p.append(subprocess.Popen(
            ['sirepo', 'job_supervisor'],
            env=env,
        ))

        for i in range(30):
            try:
                r = c.sr_post('jobSupervisorPing', PKDict(simulationType=sirepo.srunit.SR_SIM_TYPE_DEFAULT))
                if r.state == 'ok':
                    break
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(.1)
        else:
            import sirepo.job_api
            from pykern.pkdebug import pkdlog
            pkdlog(sirepo.job_api.cfg.supervisor_uri)
            pkunit.pkfail('could not connect to {}', sirepo.job_api.cfg.supervisor_uri)
        yield c
    finally:
        for x in p:
            x.terminate()
            x.wait()
