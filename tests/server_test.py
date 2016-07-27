# -*- coding: utf-8 -*-
u"""Simple API test for app.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
pytest.importorskip('srwl_bl')

from pykern import pkio
from pykern import pkunit
import json

@pytest.yield_fixture(scope='module')
def client():
    from sirepo import server
    with pkunit.save_chdir_work():
        db = pkio.mkdir_parent('db')
        server.app.config['TESTING'] = True
        server.init(db)
        yield server.app.test_client()


def test_basic(client):
    resp = client.get('/')
    assert resp.status_code == 404, \
        'There should not be a / route'


def test_srw(client):
    resp = client.get('/srw')
    assert '<!DOCTYPE html' in resp.data, \
        'Top level document is html'
    resp = client.post(
        '/simulation-list',
        data=json.dumps({
            'simulationType': 'srw',
            'search': '',
        }),
        content_type='application/json',
    )
    pkio.write_text('list.json', pkunit.json_reformat(resp.data))
