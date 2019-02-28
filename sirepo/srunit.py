# -*- coding: utf-8 -*-
u"""Support for unit tests

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdp, pkdc, pkdexc, pkdlog, pkdpretty
import flask
import flask.testing
import json
import re
try:
    # py2
    from urllib import urlencode
except ImportError:
    # py3
    from urllib.parse import urlencode


#: import sirepo.server
server = None


def flask_client(cfg=None):
    """Return FlaskClient with easy access methods.

    Creates a new run directory every test file so can assume
    sharing of state on the server within a file (module).

    Two methods of interest: `sr_post` and `sr_get`.

    Args:
        cfg (dict): extra configuration for reset_state_for_testing

    Returns:
        FlaskClient: for local requests to Flask server
    """
    global server

    a = 'srunit_flask_client'
    if not cfg:
        cfg = {}
    wd = pkunit.work_dir()
    cfg['SIREPO_SRDB_ROOT'] = str(pkio.mkdir_parent(wd.join('db')))
    if not (server and hasattr(server.app, a)):
        with pkio.save_chdir(wd):
            pkconfig.reset_state_for_testing(cfg)
            from sirepo import server as s

            server = s
            server.app.config['TESTING'] = True
            server.app.test_client_class = _TestClient
            server.init()
            setattr(server.app, a, server.app.test_client())
    return getattr(server.app, a)


def init_user_db():
    """Force a request that creates a user in db"""
    fc = flask_client()
    fc.get('/hellweg')
    fc.sr_post(
        'listSimulations',
        {'simulationType': 'hellweg', 'search': {}},
    )


def file_as_stream(filename):
    """Returns the file contents as a (text, stream) pair.
    """
    try:
        import StringIO
    except:
        from io import StringIO
    res = filename.read(mode='rb')
    return res, StringIO.StringIO(res)


def test_in_request(op, cfg=None, before_request=None, headers=None, want_cookie=True):
    fc = flask_client(cfg)
    try:
        if before_request:
            before_request(fc)
        setattr(
            server.app,
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
        delattr(server.app, server.SRUNIT_TEST_IN_REQUEST)
    return resp


class _TestClient(flask.testing.FlaskClient):

    def sr_post(self, route_name, data, params=None, raw_response=False):
        """Posts JSON data to route_name to server

        File parameters are posted as::

        Args:
            route_name (str): identifies route in schema-common.json
            data (object): will be formatted as form data
            params (dict): optional params to route_name

        Returns:
            object: Parsed JSON result
        """
        op = lambda r: self.post(r, data=json.dumps(data), content_type='application/json')
        return _req(route_name, params, {}, op, raw_response=raw_response)

    def sr_post_form(self, route_name, data, params=None, raw_response=False):
        """Posts form data to route_name to server with data

        Args:
            route_name (str): identifies route in schema-common.json
            data (dict): will be formatted as JSON
            params (dict): optional params to route_name

        Returns:
            object: Parsed JSON result
        """
        op = lambda r: self.post(r, data=data)
        return _req(route_name, params, {}, op, raw_response=raw_response)

    def sr_get(self, route_name, params=None, query=None, raw_response=False):
        """Gets a request to route_name to server

        Args:
            route_name (str): identifies route in schema-common.json
            params (dict): optional params to route_name

        Returns:
            object: Parsed JSON result
        """
        return _req(route_name, params, query, self.get, raw_response=raw_response)

    def sr_sim_data(self, sim_type, sim_name):
        """Return simulation data by name

        Args:
            sim_type (str): app
            sim_name (str): case sensitive name

        Returns:
            dict: data
        """
        data = self.sr_post('listSimulations', {'simulationType': sim_type})
        for d in data:
            if d['name'] == sim_name:
                break
        else:
            pkunit.pkfail('{}: not found in ', sim_name, pkdpretty(data))
        return self.sr_get(
            'simulationData',
            {
                'simulation_type': sim_type,
                'pretty': '0',
                'simulation_id': d['simulationId'],
            },
        )


def _req(route_name, params, query, op, raw_response):
    """Make request and parse result

    Args:
        route_name (str): string name of route
        params (dict): parameters to apply to route
        op (func): how to request

    Returns:
        object: parsed JSON result
    """
    from sirepo import simulation_db

    uri = None
    resp = None
    try:
        uri = _uri(route_name, params, query)
        resp = op(uri)
        if raw_response:
            return resp
        return simulation_db.json_load(resp.data)
    except Exception as e:
        pkdlog('Exception: {}: msg={} uri={} resp={}', type(e), e, uri, resp)
        raise


def _uri(route_name, params, query):
    """Convert name to uri found in SCHEMA_COMMON.

    Args:
        route_name (str): string name of route
        params (dict): parameters to apply to route
        query (dict): query string values

    Returns:
        str: URI
    """
    from sirepo import simulation_db

    route = simulation_db.SCHEMA_COMMON['route'][route_name]
    if params:
        for k, v in params.items():
            k2 = r'\??<' + k + '>'
            new_route = re.sub(k2, v, route)
            assert new_route != route, \
                '{}: not found in "{}"'.format(k2, route)
            route = new_route
    route = re.sub(r'\??<[^>]+>', '', route)
    assert not '<' in route, \
        '{}: missing params'.format(route)
    if query:
        route += '?' + urlencode(query)
    return route
