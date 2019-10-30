# -*- coding: utf-8 -*-
u"""Support for unit tests

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
import flask
import flask.testing
import json
import re


#: import sirepo.server
server = None

#: app result from server.init
app = None

#: Matches javascript-redirect.html
_JAVASCRIPT_REDIRECT_RE = re.compile(r'window.location = "([^"]+)"')

def flask_client(cfg=None, sim_types=None):
    """Return FlaskClient with easy access methods.

    Creates a new run directory every test file so can assume
    sharing of state on the server within a file (module).

    Two methods of interest: `sr_post` and `sr_get`.

    Args:
        cfg (dict): extra configuration for reset_state_for_testing
        sim_types (str): value for SIREPO_FEATURE_CONFIG_SIM_TYPES

    Returns:
        FlaskClient: for local requests to Flask server
    """
    global server, app

    a = 'srunit_flask_client'
    if not cfg:
        cfg = {}
    if sim_types:
        cfg['SIREPO_FEATURE_CONFIG_SIM_TYPES'] = sim_types
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
            setattr(app, a, app.test_client())
    return getattr(app, a)


def init_auth_db():
    """Force a request that creates a user in db with just myapp"""
    fc = flask_client(sim_types='myapp')
    fc.sr_login_as_guest('myapp')
    return fc, fc.sr_post('listSimulations', {'simulationType': 'myapp'})


def file_as_stream(filename):
    """Returns the file contents as a (text, stream) pair.
    """
    try:
        import StringIO
    except:
        from io import StringIO
    res = filename.read(mode='rb')
    return res, StringIO.StringIO(res)


def test_in_request(op, cfg=None, before_request=None, headers=None, want_cookie=True, **kwargs):
    fc = flask_client(cfg, **kwargs)
    try:
        from pykern import pkunit

        if before_request:
            before_request(fc)
        setattr(
            server._app,
            server.SRUNIT_TEST_IN_REQUEST,
            pkcollections.Dict(op=op, want_cookie=want_cookie),
        )
        from sirepo import uri_router
        resp = fc.get(
            uri_router.srunit_uri,
            headers=headers,
        )
        pkunit.pkeq(200, resp.status_code, 'FAIL: resp={}', resp.status)
    finally:
        try:
            delattr(server._app, server.SRUNIT_TEST_IN_REQUEST)
        except AttributeError:
            pass
    return resp


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

    def sr_auth_state(self, **kwargs):
        """Gets authState and prases

        Returns:
            dict: parsed auth_state
        """
        from pykern import pkunit

        m = re.search(r'(\{.*\})', self.sr_get('authState').data)
        s = pkcollections.json_load_any(m.group(1))
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
            sim_type (str): app name ['myapp']

        Returns:
            flask.Response: reply object
        """
        return self.__req(
            'root',
            {'simulation_type': sim_type or 'myapp'},
            None,
            self.get,
            raw_response=True,
            **kwargs
        )

    def sr_login_as_guest(self, sim_type='myapp'):
        """Setups up a guest login

        Args:
            sim_type (str): simulation type ['myapp']

        Returns:
            str: new user id
        """
        self.cookie_jar.clear()
        # Get a cookie
        self.sr_get('authState')
        self.sr_get('authGuestLogin', {'simulation_type': sim_type})
        return self.sr_auth_state(needCompleteRegistration=False, isLoggedIn=True).uid


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

    def sr_post_form(self, route_or_uri, data, params=None, raw_response=False, **kwargs):
        """Posts form data to route_or_uri to server with data

        Args:
            route_or_uri (str): identifies route in schema-common.json
            data (dict): will be formatted as JSON
            params (dict): optional params to route_or_uri

        Returns:
            object: Parsed JSON result
        """
        op = lambda r: self.post(r, data=data)
        return self.__req(route_or_uri, params, {}, op, raw_response=raw_response, **kwargs)

    def sr_sim_data(self, sim_type, sim_name):
        """Return simulation data by name

        Args:
            sim_type (str): app
            sim_name (str): case sensitive name

        Returns:
            dict: data
        """
        from pykern import pkunit
        from pykern.pkdebug import pkdpretty

        data = self.sr_post('listSimulations', {'simulationType': sim_type})
        for d in data:
            if d['name'] == sim_name:
                break
        else:
            pkunit.pkfail('{}: not found in ', sim_name, pkdpretty(data))
        return self.sr_get_json(
            'simulationData',
            {
                'simulation_type': sim_type,
                'pretty': '0',
                'simulation_id': d['simulationId'],
            },
        )


    def __req(self, route_or_uri, params, query, op, raw_response, **kwargs):
        """Make request and parse result

        Args:
            route_or_uri (str): string name of route or uri if contains '/' (http:// or '/foo')
            params (dict): parameters to apply to route
            op (func): how to request

        Returns:
            object: parsed JSON result
        """
        from pykern.pkcollections import PKDict
        from pykern.pkdebug import pkdlog, pkdexc, pkdc
        import sirepo.http_reply
        import sirepo.uri
        import sirepo.util

        u = None
        r = None
        try:
            u = sirepo.uri.server_route(route_or_uri, params, query)
            pkdc('uri={}', u)
            r = op(u)
            pkdc('status={} data={}', r.status_code, r.data)
            # Emulate code in sirepo.js to deal with redirects
            if r.status_code == 200 and r.mimetype == 'text/html':
                m = _JAVASCRIPT_REDIRECT_RE.search(r.data)
                if m:
                    if kwargs.get('redirect', True):
                        # Execute the redirect
                        return self.__req(m.group(1), None, None, self.get, raw_response)
                    return flask.redirect(m.group(1))
            if r.status_code in (301, 302, 303, 305, 307, 308):
                if kwargs.get('redirect', True):
                    # Execute the redirect
                    return self.__req(r.headers['Location'], None, None, self.get, raw_response)
                return r
            if raw_response:
                return r
            # Treat SRException as a real exception (so we don't ignore them)
            d = pkcollections.json_load_any(r.data)
            if (
                r.status_code == sirepo.http_reply.SR_EXCEPTION_STATUS
                    and r.mimetype == 'application/json'
            ):
                raise sirepo.util.SRException(
                    d.srException.routeName,
                    d.srException.params,
                )
            return d
        except Exception as e:
            if not isinstance(e, sirepo.util.SRException):
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
