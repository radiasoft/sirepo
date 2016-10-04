# -*- coding: utf-8 -*-
u"""Simple API test for app.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
pytest.importorskip('srwl_bl')

def test_basic():
    from sirepo import sr_unit
    fc = sr_unit.flask_client()
    resp = fc.get('/')
    assert 'LandingPageController' in resp.data, \
        'Top level document is the landing page'


def test_srw():
    from pykern import pkio
    from pykern.pkdebug import pkdpretty
    from sirepo import sr_unit
    import json

    fc = sr_unit.flask_client()
    resp = fc.get('/srw')
    assert '<!DOCTYPE html' in resp.data, \
        'Top level document is html'
    data = fc.sr_post(
        'listSimulations',
        {'simulationType': 'srw', 'search': ''},
    )
