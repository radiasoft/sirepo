# This avoids a plugin dependency issue with pytest-forked/xdist:
# https://github.com/pytest-dev/pytest/issues/935
import pytest


@pytest.fixture
def animation_fc(fc):
    fc.sr_animation_run = animation_run
    return fc


def animation_run(fc, sim_name, compute_model, reports, **kwargs):
    from pykern import pkconfig
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp, pkdlog
    from sirepo import srunit
    import re
    import time

    data = fc.sr_sim_data(sim_name)
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

    yield sirepo.srunit.flask_client()


@pytest.fixture
def import_req(request):
    def w(path):
        req = http_request.parse_params(
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
    from pykern import pkunit
    # Seems to be the only way to get the module under test
    m = item._request.module
    is_new = m != pkunit.module_under_test
    pkunit.module_under_test = m
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


def _sim_type(request):
    import sirepo.feature_config

    for c in sirepo.feature_config.ALL_CODES:
        if c in request.function.func_name or c in str(request.fspath):
            return c
    return 'myapp'
