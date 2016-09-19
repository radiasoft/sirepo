# -*- coding: utf-8 -*-
u"""Common PyTest fixtures

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import flask.testing
import json
import pytest


@pytest.yield_fixture(scope='function')
def sr_client():
    """Return Flask test_client fixture -6D2A(scope=module).

    Creates a new run directory every test file so can assume
    sharing of state on the server within a file (module).
    """
    from pykern import pkunit, pkio
    from sirepo import server
    with pkio.save_chdir(pkunit.work_dir()):
        db = pkio.mkdir_parent('db')
        server.app.config['TESTING'] = True
        server.app.test_client_class = _TestClient
        server.init(db)
        yield server.app.test_client()


class _TestClient(flask.testing.FlaskClient):

    def sr_post(self, route_name, data, params=None):
        """Posts a request to route_name to server with data

        Args:
            route_name (str): identifies route in schema-common.json
            data (object): will be formatted as JSON
            params (dict): optional params to route_name

        Returns:
            object: Parsed JSON result
        """
        op = lambda r: self.post(r, data=json.dumps(data), content_type='application/json')
        return _req(route_name, params, op)


    def sr_get(self, route_name, params=None):
        """Gets a request to route_name to server

        Args:
            route_name (str): identifies route in schema-common.json
            params (dict): optional params to route_name

        Returns:
            object: Parsed JSON result
        """
        return _req(route_name, params, self.get)


def _req(route_name, params, op):
    resp = op(_route(route_name, params))
    return json.loads(resp.data)


def _route(route_name, params):
    from sirepo import simulation_db
    route = simulation_db.SCHEMA_COMMON['route'][route_name]
    if params:
        for k, v in params.items():
            k2 = '<' + k + '>'
            new_route = route.replace(k2, v)
            assert new_route != route, \
                '{}: not found in "{}"'.format(k2, route)
            route = new_route
    assert not '<' in route, \
        '{}: missing params'.format(route)
    return route
