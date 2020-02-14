# This avoids a plugin dependency issue with pytest-forked/xdist:
# https://github.com/pytest-dev/pytest/issues/935
import pytest
import subprocess

#: Maximum time an individual test case (function) can run
MAX_CASE_RUN_SECS = 120


@pytest.fixture
def auth_fc(auth_fc_module):
    # set the sentinel
    auth_fc_module.cookie_jar.clear()
    auth_fc_module.sr_get_root()
    auth_fc_module.sr_email_confirm = email_confirm
    return auth_fc_module


@pytest.fixture
def auth_fc_module(request):
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
    if 'email3_test' in str(request.fspath):
        cfg.SIREPO_AUTH_METHODS += ':github'
    else:
        cfg.SIREPO_AUTH_DEPRECATED_METHODS = 'github'
    from pykern import pkconfig
    pkconfig.reset_state_for_testing(cfg)

    from pykern import pkunit
    from pykern import pkio
    cfg['SIREPO_SRDB_ROOT'] = str(pkio.mkdir_parent(pkunit.work_dir().join('db')))
    p, fc = _job_supervisor_start(request, cfg=cfg)
    if p:
        yield fc
        p.terminate()
        p.wait()
    else:
        yield sirepo.srunit.flask_client(cfg=cfg)


def email_confirm(fc, resp, display_name=None):
    import re
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp

    fc.sr_get(resp.uri)
    pkdp(resp.uri)
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
    import sirepo.srunit
    p, fc = _job_supervisor_start(request)
    if p:
        yield fc
        p.terminate()
        p.wait()
    else:
        yield sirepo.srunit.flask_client()


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

    def _mark_skip(test, reason):
        test.add_marker(pytest.mark.skip(reason=reason))

    s = PKDict(
        elegant='sdds',
        srw='srwl_bl',
        synergia='synergia',
        warp='warp',
        zgoubi='zgoubi',
    )
    all_codes = set(sirepo.feature_config.ALL_CODES)
    codes = set()
    import_fail = PKDict()
    skip_list = os.environ.get('SIREPO_PYTEST_SKIP', '').split(':')
    slurm_not_installed = _check_installed('sbatch')
    docker_not_installed = _check_installed('docker')
    for i in items:
        b = i.fspath.purebasename
        if b in skip_list:
            _mark_skip(i, 'SIREPO_PYTEST_SKIP')
            continue
        if 'sbatch' in b and slurm_not_installed:
            _mark_skip(i, 'slurm not installed')
            continue
        if 'docker' in b and docker_not_installed:
            _mark_skip(i, 'docker not installed')
            continue
        c = [x for x in all_codes if x in i.name]
        if not c:
            continue
        c = c[0]
        if c in import_fail:
            i.add_marker(import_fail[c])
            continue
        if c not in all_codes:
            _mark_skip(
                i,
                'skipping code={} not in codes={}'.format(c, all_codes),
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
    sirepo.srunit.CONFTEST_ALL_CODES = ':'.join(codes)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_protocol(item, *args, **kwargs):
    import signal
    from pykern import pkunit

    def _timeout(*args, **kwargs):
        pkunit.pkfail('MAX_CASE_RUN_SECS={} exceeded', MAX_CASE_RUN_SECS)

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


def _check_installed(program):
    try:
        subprocess.check_output((program, '--help'))
    except OSError:
        return True
    return False


def _config_sbatch_supervisor_env(env):
    from pykern.pkcollections import PKDict
    import os
    import pykern.pkio
    import pykern.pkunit
    import re
    import socket
    import subprocess

    h = socket.gethostname()
    k = pykern.pkio.py_path('~/.ssh/known_hosts').read()
    m = re.search('^{}.*$'.format(h), k, re.MULTILINE)
    assert bool(m), \
        'You need to ssh into {} to get the host key'.format(h)

    env.pkupdate(
        SIREPO_JOB_DRIVER_SBATCH_CORES=os.getenv(
            'SIREPO_JOB_DRIVER_SBATCH_CORES',
            '2',
        ),
        SIREPO_JOB_DRIVER_SBATCH_HOST=h,
        SIREPO_JOB_DRIVER_SBATCH_HOST_KEY=m.group(0),
        SIREPO_JOB_DRIVER_SBATCH_SIREPO_CMD=subprocess.check_output(
            'PYENV_VERSION=py3 pyenv which sirepo',
            stderr=subprocess.STDOUT,
            shell=True
        ).rstrip(),
        SIREPO_JOB_DRIVER_SBATCH_SRDB_ROOT=str(pykern.pkunit.work_dir().join(
            '/{sbatch_user}/sirepo'
        )),
        SIREPO_JOB_SUPERVISOR_SBATCH_POLL_SECS='2',
    )


def _job_supervisor_check(env):
    import sirepo.job
    import socket
    import subprocess

    try:
        o = subprocess.check_output(
            ['pyenv', 'exec', 'sirepo', 'job_supervisor', '--help'],
            env=env,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        from pykern.pkdebug import pkdlog

        pkdlog('job_supervisor --help exit={} output={}', e.returncode, e.output)
        raise
    assert 'usage: sirepo job_supervisor' in str(o)
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


def _job_supervisor_setup(request, cfg=None):
    """setup the supervisor"""
    import os
    from pykern.pkcollections import PKDict
    env = PKDict()
    for k, v in os.environ.items():
        if ('PYENV' in k or 'PYTHON' in k):
            continue
        if k in ('PATH', 'LD_LIBRARY_PATH'):
            v2 = []
            for x in v.split(':'):
                if x and 'py2' not in x:
                    v2.append(x)
            v = ':'.join(v2)
        env[k] = v
    if not cfg:
        cfg = PKDict()
    i = '127.0.0.1'
    # different port than default so can run tests when supervisor running
    p = '8002'
    cfg.pkupdate(
        PYKERN_PKDEBUG_WANT_PID_TIME='1',
        SIREPO_FEATURE_CONFIG_JOB='1',
        SIREPO_PKCLI_JOB_SUPERVISOR_IP=i,
        SIREPO_PKCLI_JOB_SUPERVISOR_PORT=p,
    )
    for x in 'DRIVER_LOCAL', 'DRIVER_DOCKER', 'API', 'DRIVER_SBATCH':
        cfg['SIREPO_JOB_{}_SUPERVISOR_URI'.format(x)] = 'http://{}:{}'.format(i, p)
    for i in ('docker', 'sbatch'):
        if i in request.module.__name__:
            m = i
            break

    m = None
    if 'sbatch' in request.module.__name__:
        m = 'sbatch'
        cfg.pkupdate(SIREPO_SIMULATION_DB_SBATCH_DISPLAY='testing@123')
        env.pkupdate(SIREPO_JOB_DRIVER_MODULES='local:sbatch')
    elif 'docker' in request.module.__name__:
        m = 'docker'
        env.pkupdate(SIREPO_JOB_DRIVER_MODULES='docker')

    env.pkupdate(
        PYENV_VERSION='py3',
        PYTHONUNBUFFERED='1',
        **cfg
    )

    import sirepo.srunit
    fc = sirepo.srunit.flask_client(
        cfg=cfg,
        job_run_mode=m if m == 'sbatch' else None,
    )

    if m == 'sbatch':
        # must be performed after fc initialized so work_dir is configured
        _config_sbatch_supervisor_env(env)

    import sirepo.srdb
    env.SIREPO_SRDB_ROOT = str(sirepo.srdb.root())

    _job_supervisor_check(env)
    return (env, fc)


def _job_supervisor_start(request, cfg=None):
    import os
    if os.environ.get('SIREPO_FEATURE_CONFIG_JOB') != '1':
        return None, None

    from pykern import pkunit
    from pykern.pkcollections import PKDict
    import subprocess
    import time

    env, fc = _job_supervisor_setup(request, cfg)
    p = subprocess.Popen(
        ['pyenv', 'exec', 'sirepo', 'job_supervisor'],
        env=env,
    )
    for i in range(30):
        r = fc.sr_post('jobSupervisorPing', PKDict(simulationType=fc.SR_SIM_TYPE_DEFAULT))
        if r.state == 'ok':
            break
        time.sleep(.1)
    else:
        import sirepo.job_api
        from pykern.pkdebug import pkdp
        pkdp(sirepo.job_api.cfg.supervisor_uri)
        pkunit.pkfail('could not connect to {}', sirepo.job_api.cfg.supervisor_uri)
    return p, fc


def _sim_type(request):
    import sirepo.feature_config

    for c in sirepo.feature_config.ALL_CODES:
        if c in request.function.func_name or c in str(request.fspath):
            return c
    return 'myapp'
