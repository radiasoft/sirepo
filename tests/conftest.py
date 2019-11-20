# This avoids a plugin dependency issue with pytest-forked/xdist:
# https://github.com/pytest-dev/pytest/issues/935
import pytest
pytest_plugins = ['pykern.pytest_plugin']


@pytest.fixture(scope='function')
def fc(request):
    """Flask client based logged in to specific code of test

    Defaults to myapp.
    """
    import sirepo.feature_config
    import sirepo.srunit

    for c in sirepo.feature_config.ALL_CODES:
        if c in request.function.func_name:
            break
    else:
        c = 'myapp'
    res = sirepo.srunit.flask_client()
    res.sr_login_as_guest(sim_type=c)
    return res


def pytest_addoption(parser):
    """Passing --code restricts tests to that code(s)

    May be passed multiple times.

    """
    parser.addoption(
        '--code',
        action='append',
        default=[],
        help='run a code (or multiple with multiple args)',
    )


def pytest_collection_modifyitems(session, config, items):
    """Restrict which tests are running"""
    import importlib
    import sirepo.feature_config
    from pykern.pkcollections import PKDict

    s = PKDict(
        elegant='sdds',
        srw='srwl_bl',
        synergia='synergia',
        warp='warp',
        zgoubi='zgoubi',
    )
    all_codes = set(sirepo.feature_config.ALL_CODES)
    c = config.getoption('code')
    if c:
        all_codes = [x for x in c if x in all_codes]
    codes = set()
    import_fail = PKDict()
    res = set()
    for i in items:
        c = [x for x in sirepo.feature_config.ALL_CODES if x in i.name]
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
    import sirepo.srunit
    sirepo.srunit.CONFTEST_ALL_CODES = ':'.join(codes)
