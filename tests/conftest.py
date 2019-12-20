# This avoids a plugin dependency issue with pytest-forked/xdist:
# https://github.com/pytest-dev/pytest/issues/935
import pytest

#: Maximum time an individual test case (function) can run
MAX_CASE_RUN_SECS = 30


@pytest.fixture
def animation_fc(fc):
    fc.sr_animation_run = animation_run
    return fc


def animation_run(fc, sim_name, compute_model, reports, job_run_mode=None, **kwargs):
    from pykern import pkconfig
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp, pkdlog
    from sirepo import srunit
    import re
    import time

    data = fc.sr_sim_data(sim_name)
    if job_run_mode:
        data.models[compute_model].jobRunMode = job_run_mode

    run = fc.sr_run_sim(data, compute_model, **kwargs)
    for r, a in reports.items():
        if 'runSimulation' in a:
            f = fc.sr_run_sim(data, r)
            for k, v in a.items():
                m = re.search('^expect_(.+)', k)
                if m:
                    pkunit.pkre(
                        v(i) if callable(v) else v,
                        str(f.get(m.group(1))),
                    )
            continue
        if 'frame_index' in a:
            c = [a.get('frame_index')]
        else:
            c = range(run.get(a.get('frame_count_key', 'frameCount')))
            assert c, \
                'frame_count_key={} or frameCount={} is zero'.format(
                    a.get('frame_count_key'), a.get('frameCount'),
                )
        pkdlog('frameReport={} count={}', r, c)
        import sirepo.sim_data

        s = sirepo.sim_data.get_class(fc.sr_sim_type)
        for i in c:
            pkdlog('frameIndex={} frameCount={}', i, run.get('frameCount'))
            f = fc.sr_get_json(
                'simulationFrame',
                PKDict(frame_id=s.frame_id(data, run, r, i)),
            )
            for k, v in a.items():
                m = re.search('^expect_(.+)', k)
                if m:
                    pkunit.pkre(
                        v(i) if callable(v) else v,
                        str(f.get(m.group(1))),
                    )


@pytest.fixture
def auth_fc(auth_fc_module):
    # set the sentinel
    auth_fc_module.cookie_jar.clear()
    auth_fc_module.sr_get_root()
    auth_fc_module.sr_email_confirm = email_confirm
    return auth_fc_module


@pytest.fixture
def auth_fc_module(request):
    from sirepo import srunit
    from pykern.pkcollections import PKDict

    cfg = PKDict(
        SIREPO_AUTH_EMAIL_FROM_EMAIL='x',
        SIREPO_AUTH_EMAIL_FROM_NAME='x',
        SIREPO_AUTH_EMAIL_SMTP_PASSWORD='x',
        SIREPO_AUTH_EMAIL_SMTP_SERVER='dev',
        SIREPO_AUTH_EMAIL_SMTP_USER='x',
        SIREPO_AUTH_GITHUB_CALLBACK_URI='/uri',
        SIREPO_AUTH_GITHUB_KEY='key',
        SIREPO_AUTH_GITHUB_SECRET='secret',
        SIREPO_AUTH_GUEST_EXPIRY_DAYS='1',
        SIREPO_AUTH_METHODS='email:guest',
    )
    if 'email3_test' in str(request.fspath):
        cfg.SIREPO_AUTH_METHODS += ':github'
    else:
        cfg.SIREPO_AUTH_DEPRECATED_METHODS = 'github'
    return srunit.flask_client(cfg=cfg)


def email_confirm(fc, resp, display_name=None):
    import re
    from pykern.pkcollections import PKDict

    fc.sr_get(resp.url)
    m = re.search(r'/(\w+)$', resp.url)
    assert m
    r = PKDict(token=m.group(1))
    if display_name:
        r.displayName = display_name
    fc.sr_post(
        resp.url,
        r,
        raw_response=True,
    )


@pytest.fixture(scope='function')
def fc(request, fc_module):
    """Flask client based logged in to specific code of test

    Defaults to myapp.
    """
    import sirepo.srunit

    c = _sim_type(request)
    if fc_module.sr_uid:
        if fc_module.sr_sim_type != c:
            fc_module.sr_get_root(sim_type=c)
    else:
        fc_module.sr_login_as_guest(sim_type=c)
    return fc_module


@pytest.fixture(scope='module')
def fc_module(request):
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
        zgoubi='zgoubi',
    )
    all_codes = set(sirepo.feature_config.ALL_CODES)
    codes = set()
    import_fail = PKDict()
    res = set()
    skip_list = os.environ.get('SIREPO_PYTEST_SKIP', '').split(':')
    for i in items:
        if i.fspath.purebasename in skip_list:
            i.add_marker(pytest.mark.skip(reason="SIREPO_PYTEST_SKIP"))
            continue
        c = [x for x in all_codes if x in i.name]
        if not c:
            continue
        c = c[0]
        if c in import_fail:
            i.add_marker(import_fail[c])
            continue
        if c not in all_codes:
            i.add_marker(
                pytest.mark.skip(
                    reason='skipping code={} not in codes={}'.format(c, all_codes),
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


@pytest.fixture
def sbatch_animation_fc(fc):
    import functools
    fc.sr_animation_run = functools.partial(
        animation_run,
        job_run_mode='sbatch',
    )
    return fc


def _configure_sbatch_env(env, cfg):
    from pykern.pkcollections import PKDict
    import pykern.pkio
    import re
    import subprocess

    h = 'v.radia.run'
    k = pykern.pkio.py_path('/home/vagrant/.ssh/known_hosts').read()
    m = re.search('^{}.*$'.format(h), k, re.MULTILINE)
    assert m, \
        'You need to ssh into {} to get the host key'.format(h)

    try:
        subprocess.check_output(['sbatch', '--help'], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        from pykern.pkdebug import pkdlog
        pkdlog('you need to install slurm. run `radia_run slurm-dev`')
        raise

    d = PKDict(SIREPO_SIMULATION_DB_SBATCH_DISPLAY='testing@123')
    cfg.pkupdate(**d)

    env.pkupdate(
        SIREPO_JOB_DRIVER_MODULES='local:sbatch',
        SIREPO_JOB_DRIVER_SBATCH_HOST=h,
        SIREPO_JOB_DRIVER_SBATCH_HOST_KEY=m.group(0),
        SIREPO_JOB_DRIVER_SBATCH_SIREPO_CMD='$HOME/.pyenv/versions/py3/bin/sirepo',
        # TODO(e-carlin): this isn't right for testing. I'm not sure env.SIREPO_SRDB_ROOT is right either
        SIREPO_JOB_DRIVER_SBATCH_SRDB_ROOT='/var/tmp/{sbatch_user}/sirepo',
        SIREPO_JOB_SUPERVISOR_SBATCH_POLL_SECS='2',
        **d
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
    try:
        s.bind((sirepo.job.DEFAULT_IP, int(sirepo.job.DEFAULT_PORT)))
    except Exception:
        raise AssertionError(
            'job_supervisor still running on port={}'.format(sirepo.job.DEFAULT_PORT),
        )
    finally:
        s.close()


def _job_supervisor_setup(request):
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
    cfg = PKDict(
        PYKERN_PKDEBUG_WANT_PID_TIME='1',
        SIREPO_FEATURE_CONFIG_JOB='1',
    )
    env.pkupdate(
        PYENV_VERSION='py3',
        PYTHONUNBUFFERED='1',
        **cfg
    )

    if 'sbatch' in request.module.__name__:
        _configure_sbatch_env(env, cfg)

    import sirepo.srunit
    fc = sirepo.srunit.flask_client(cfg=cfg)

    import sirepo.srdb
    env.SIREPO_SRDB_ROOT = str(sirepo.srdb.root())

    _job_supervisor_check(env)
    return (env, fc)


def _job_supervisor_start(request):
    import os
    if not os.environ.get('SIREPO_FEATURE_CONFIG_JOB') == '1':
        return None, None

    from pykern import pkunit
    from pykern.pkcollections import PKDict
    import sirepo.job
    import subprocess
    import time

    env, fc = _job_supervisor_setup(request)
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
        pkunit.pkfail('could not connect to {}', sirepo.job.SERVER_PING_ABS_URI)
    return p, fc


def _sim_type(request):
    import sirepo.feature_config

    for c in sirepo.feature_config.ALL_CODES:
        if c in request.function.func_name or c in str(request.fspath):
            return c
    return 'myapp'
