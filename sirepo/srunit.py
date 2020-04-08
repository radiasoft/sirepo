# -*- coding: utf-8 -*-
u"""Support for unit tests

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import flask
import flask.testing
import json
import re
from pykern.pkcollections import PKDict


#: Default "app"
MYAPP = 'myapp'

#: import sirepo.server
server = None

#: app result from server.init
app = None

#: Matches javascript-redirect.html
_JAVASCRIPT_REDIRECT_RE = re.compile(r'window.location = "([^"]+)"')

#: set by conftest.py
CONFTEST_ALL_CODES = None


def flask_client(cfg=None, sim_types=None, job_run_mode=None):
    """Return FlaskClient with easy access methods.

    Creates a new run directory every test file so can assume
    sharing of state on the server within a file (module).

    Two methods of interest: `sr_post` and `sr_get`.

    Args:
        cfg (dict): extra configuration for reset_state_for_testing
        sim_types (str): value for SIREPO_FEATURE_CONFIG_SIM_TYPES [CONFTEST_ALL_CODES]

    Returns:
        FlaskClient: for local requests to Flask server
    """
    global server, app

    a = 'srunit_flask_client'
    if not cfg:
        cfg = PKDict()
    t = sim_types or CONFTEST_ALL_CODES
    if t:
        if isinstance(t, (tuple, list)):
            t = ':'.join(t)
        cfg['SIREPO_FEATURE_CONFIG_SIM_TYPES'] = t
    if not (server and hasattr(app, a)):
        from pykern import pkconfig

        # initialize pkdebug with correct values
        pkconfig.reset_state_for_testing(cfg)

        from pykern import pkunit
        with pkunit.save_chdir_work() as wd:
            from pykern import pkio
            cfg['SIREPO_SRDB_ROOT'] = str(pkio.mkdir_parent(wd.join('db')))
            pkconfig.reset_state_for_testing(cfg)
            from sirepo import server as s

            server = s
            app = server.init()
            app.config['TESTING'] = True
            app.test_client_class = _TestClient
            setattr(app, a, app.test_client(job_run_mode=job_run_mode))
    return getattr(app, a)


def init_auth_db():
    """Force a request that creates a user in db with just myapp"""
    fc = flask_client(sim_types=MYAPP)
    fc.sr_login_as_guest()
    return fc, fc.sr_post('listSimulations', {'simulationType': fc.sr_sim_type})


def sim_data(sim_name=None, sim_type=None, sim_types=CONFTEST_ALL_CODES, cfg=None):
    """Get simulation data

    Args:
        sim_name (str): full name of simulation
        sim_type (str): app [defaults to myapp]
        sim_types (str): `SIREPO_FEATURE_CONFIG_SIM_TYPES` value
    Returns:
        PKDict: simulation data
        object: flask client
    """
    fc = flask_client(sim_types=sim_types or [sim_type or MYAPP], cfg=cfg)
    fc.sr_login_as_guest()
    return fc.sr_sim_data(sim_name=sim_name, sim_type=sim_type), fc


def test_in_request(op, cfg=None, before_request=None, headers=None, want_cookie=True, want_user=True, **kwargs):
    fc = flask_client(cfg, **kwargs)
    try:
        from pykern import pkunit
        from pykern import pkcollections

        if before_request:
            before_request(fc)
        setattr(
            server._app,
            server.SRUNIT_TEST_IN_REQUEST,
            PKDict(op=op, want_cookie=want_cookie, want_user=want_user),
        )
        from sirepo import uri_router
        r = fc.get(
            uri_router.srunit_uri,
            headers=headers,
        )
        pkunit.pkeq(200, r.status_code, 'FAIL: unexpected status={}', r.status)
        if r.mimetype == 'text/html':
            m = _JAVASCRIPT_REDIRECT_RE.search(str(r.data))
            if m:
                pkunit.pkfail('unexpected redirect={}', m.group(1))
            pkunit.pkfail('unexpected html response={}', r.data)
        d = pkcollections.json_load_any(r.data)
        pkunit.pkeq('ok', d.get('state'), 'FAIL: expecting state=ok, but got data={}', d)
    finally:
        try:
            delattr(server._app, server.SRUNIT_TEST_IN_REQUEST)
        except AttributeError:
            pass
    return r


def wrap_in_request(*args, **kwargs):
    """Decorator for calling functions in `test_in_request`

    Examples:
        # note that the parens are required
        @srunit.wrap_in_request()
        def test_simple():
            inside request context

        @srunit.wrap_in_request(cfg={'SIREPO_AUTH_METHODS': 'github:guest'})
        def test_myapp():
            inside a request context here

    Args:
        func (callable): function to be wrapped
        kwargs (dict): passed to test_in_request

    Returns:
        callable: replacement function
    """
    def _decorator(func):
        def _wrapper(*ignore_args, **ignore_kwargs):
            return test_in_request(lambda: func(), **kwargs)
        return _wrapper

    return _decorator


class _TestClient(flask.testing.FlaskClient):

    SR_SIM_TYPE_DEFAULT = MYAPP

    def __init__(self, *args, **kwargs):
        self.sr_job_run_mode = kwargs.pop('job_run_mode')
        super(_TestClient, self).__init__(*args, **kwargs)
        self.sr_sbatch_logged_in = False
        self.sr_sim_type = None
        self.sr_uid = None

    def sr_animation_run(self, sim_name, compute_model, reports, **kwargs):
        from pykern import pkunit
        from pykern.pkcollections import PKDict
        from pykern.pkdebug import pkdp, pkdlog
        import re

        data = self.sr_sim_data(sim_name)
        run = self.sr_run_sim(data, compute_model, **kwargs)
        for r, a in reports.items():
            if 'runSimulation' in a:
                f = self.sr_run_sim(data, r)
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

            s = sirepo.sim_data.get_class(self.sr_sim_type)
            for i in c:
                pkdlog('frameIndex={} frameCount={}', i, run.get('frameCount'))
                f = self.sr_get_json(
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

    def sr_auth_state(self, **kwargs):
        """Gets authState and prases

        Returns:
            dict: parsed auth_state
        """
        from pykern import pkunit
        import pykern.pkcollections

        m = re.search(r'(\{.*\})', str(self.sr_get('authState').data))
        s = pykern.pkcollections.json_load_any(m.group(1))
        for k, v in kwargs.items():
            pkunit.pkeq(
                v,
                s[k],
                'key={} expected={} != actual={}: auth_state={}',
                k,
                v,
                s[k],
                s,
            )
        return s

    def sr_get(self, route_or_uri, params=None, query=None, **kwargs):
        """Gets a request to route_or_uri to server

        Args:
            route_or_uri (str): string name of route or uri if contains '/' (http:// or '/foo')
            params (dict): optional params to route_or_uri

        Returns:
            flask.Response: reply object
        """
        return self.__req(route_or_uri, params, query, self.get, raw_response=True, **kwargs)

    def sr_get_json(self, route_or_uri, params=None, query=None, headers=None, **kwargs):
        """Gets a request to route_or_uri to server

        Args:
            route_or_uri (str): identifies route in schema-common.json
            params (dict): optional params to route_or_uri

        Returns:
            object: Parsed JSON result
        """
        return self.__req(
            route_or_uri,
            params,
            query,
            lambda r: self.get(r, headers=headers),
            raw_response=False,
            **kwargs
        )

    def sr_get_root(self, sim_type=None, **kwargs):
        """Gets root app for sim_type

        Args:
            sim_type (str): app name ['myapp' or default type]

        Returns:
            flask.Response: reply object
        """
        self.sr_sim_type_set(sim_type)
        return self.__req(
            'root',
            {'simulation_type': self.sr_sim_type},
            None,
            self.get,
            raw_response=True,
            **kwargs
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
        self.sr_get('authState')
        self.sr_get('authGuestLogin', {'simulation_type': self.sr_sim_type})
        self.sr_uid = self.sr_auth_state(needCompleteRegistration=False, isLoggedIn=True).uid
        return self.sr_uid


    def sr_logout(self):
        """Logout but leave cookie in place

        Returns:
            object: self
        """
        self.sr_uid = None
        self.sr_get('authLogout', PKDict(simulation_type=self.sr_sim_type))
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
        op = lambda r: self.post(r, data=json.dumps(data), content_type='application/json')
        return self.__req(route_or_uri, params, {}, op, raw_response=raw_response, **kwargs)

    def sr_post_form(self, route_or_uri, data, params=None, raw_response=False, file=None, **kwargs):
        """Posts form data to route_or_uri to server with data

        Args:
            route_or_uri (str): identifies route in schema-common.json
            data (dict): will be formatted as JSON
            params (dict): optional params to route_or_uri
            file (object): if str, will look in data_dir, else assumed py.path

        Returns:
            object: Parsed JSON result
        """
        from pykern import pkunit, pkconfig

        if file:
            p = file
            if isinstance(p, pkconfig.STRING_TYPES):
                p = pkunit.data_dir().join(p)
            data.file = (open(str(p), 'rb'), p.basename)
        return self.__req(
            route_or_uri,
            params,
            PKDict(),
            lambda r: self.post(r, data=data),
            raw_response=raw_response,
            **kwargs
        )

    def sr_run_sim(
            self,
            data,
            model,
            expect_completed=True,
            timeout=10,
            **post_args
    ):
        from pykern import pkunit
        from pykern.pkdebug import pkdlog, pkdexc
        import time

        if self.sr_job_run_mode:
            data.models[model].jobRunMode = self.sr_job_run_mode

        cancel = None
        try:
            r = self.sr_post(
                'runSimulation',
                PKDict(
                    models=data.models,
                    report=model,
                    simulationId=data.models.simulation.simulationId,
                    simulationType=data.simulationType,
                ).pkupdate(**post_args),
            )
            if r.state == 'completed':
                return r
            cancel = r.get('nextRequest')
            for _ in range(timeout):
                if r.state in ('completed', 'error'):
                    pkdlog(r.state)
                    cancel = None
                    break
                r = self.sr_post('runStatus', r.nextRequest)
                time.sleep(1)
            else:
                pkunit.pkok(not expect_completed, 'did not complete: runStatus={}', r)
            if expect_completed:
                pkunit.pkeq('completed', r.state)
            return r
        finally:
            if cancel:
                pkdlog('runCancel')
                self.sr_post('runCancel', cancel)
            import subprocess
            o = str(subprocess.check_output(['ps', 'axww'], stderr=subprocess.STDOUT))
            o = filter(lambda x: 'mpiexec' in x, o.split('\n'))
            if o:
                pkdlog('found "mpiexec" after cancel in ps={}', '\n'.join(o))
                # this exception won't be seen because in finally
                raise AssertionError('cancel failed')

    def sr_sbatch_animation_run(self, sim_name, compute_model, reports, **kwargs):
        from pykern.pkunit import pkexcept

        d = self.sr_sim_data(sim_name)
        if not self.sr_sbatch_logged_in:
            with pkexcept('SRException.*no-creds'):
                # Must try to run sim first to seed job_supervisor.db
                self.sr_run_sim(d, compute_model, expect_completed=False)
            self.sr_sbatch_login(compute_model, d)
            self.sr_sbatch_logged_in = True
        self.sr_animation_run(sim_name, compute_model, reports, **kwargs)

    def sr_sbatch_login(self, compute_model, data):
        import getpass

        p = getpass.getuser()
        self.sr_post(
            'sbatchLogin',
            PKDict(
                password=p,
                report=compute_model,
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
                username=p,
            )
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
            sim_name = 'Scooby Doo'
        d = self.sr_post(
            'listSimulations',
            PKDict(
                simulationType=self.sr_sim_type,
                search=PKDict({'simulation.name': sim_name}),
            )
        )
        assert 1 == len(d), \
            'listSimulations name={} returned count={}'.format(sim_name, len(d))
        d = d[0].simulation
        res = self.sr_get_json(
            'simulationData',
            PKDict(
                simulation_type=self.sr_sim_type,
                pretty='0',
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
        self.sr_sim_type = sim_type or self.sr_sim_type or self.SR_SIM_TYPE_DEFAULT
        return self

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
        import pykern.pkjson
        import sirepo.http_reply
        import sirepo.uri
        import sirepo.util

        redirects = kwargs.setdefault('__redirects', 0) + 1
        assert redirects <= 5
        kwargs['__redirects'] = redirects

        u = None
        r = None
        try:
            u = sirepo.uri.server_route(route_or_uri, params, query)
            pkdc('uri={}', u)
            r = op(u)
            pkdc(
                'status={} data={}',
                r.status_code,
                '<snip-file>' if 'download-data-file' in u else r.data,
            )
            # Emulate code in sirepo.js to deal with redirects
            if r.status_code == 200 and r.mimetype == 'text/html':
                m = _JAVASCRIPT_REDIRECT_RE.search(str(r.data))
                if m:
                    if m.group(1).endswith('#/error'):
                        raise sirepo.util.Error(
                            PKDict(error='server error uri={}'.format(m.group(1))),
                        )
                    if kwargs.get('redirect', True):
                        # Execute the redirect
                        return self.__req(
                            m.group(1),
                            None,
                            None,
                            self.get,
                            raw_response,
                            __redirects=redirects,
                        )
                    return flask.redirect(m.group(1))
            if r.status_code in (301, 302, 303, 305, 307, 308):
                if kwargs.get('redirect', True):
                    # Execute the redirect
                    return self.__req(
                        r.headers['Location'],
                        None,
                        None,
                        self.get,
                        raw_response,
                        __redirects=redirects,
                    )
                return r
            if raw_response:
                return r
            # Treat SRException as a real exception (so we don't ignore them)
            d = pykern.pkjson.load_any(r.data)
            if (
                isinstance(d, dict)
                and d.get('state') == sirepo.http_reply.SR_EXCEPTION_STATE
            ):
                raise sirepo.util.SRException(
                    d.srException.routeName,
                    d.srException.params,
                )
            return d
        except Exception as e:
            if not isinstance(e, (sirepo.util.Reply)):
                pkdlog(
                    'Exception: {}: msg={} uri={} status={} data={} stack={}',
                    type(e),
                    e,
                    u,
                    r and r.status_code,
                    r and r.data,
                    pkdexc(),
                )
            raise
