# -*- coding: utf-8 -*-
u"""Simple API test for app.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
pytest.importorskip('srwl_bl')

def test_basic(flask_client):
    resp = flask_client.get('/')
    assert resp.status_code == 404, \
        'There should not be a / route'


def test_srw(flask_client):
    from pykern import pkio
    from pykern.pkdebug import pkdpretty
    import json
    resp = flask_client.get('/srw')
    assert '<!DOCTYPE html' in resp.data, \
        'Top level document is html'
    data = flask_client.sr_post(
        'listSimulations',
        {'simulationType': 'srw', 'search': ''},
    )
    pkio.write_text('list.json', pkdpretty(data))
