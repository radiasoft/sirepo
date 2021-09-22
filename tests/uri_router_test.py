# -*- coding: utf-8 -*-
u"""Test sirepo.uri_router

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
pytest.importorskip('srwl_bl')


def test_error_for_bots():
    from pykern.pkunit import pkeq, pkexcept, pkre
    from pykern.pkcollections import PKDict
    from sirepo import srunit

    fc = srunit.flask_client()
    fc.sr_login_as_guest()

    uri = '/get-application-data'
    d = PKDict(simulationType='srw', method='NO SUCH METHOD')

    r = fc.post(uri, json=d)
    pkeq(200, r.status_code)

    r = fc.post(uri, environ_base={'HTTP_USER_AGENT': 'SPIDER'}, json=d)
    pkeq(500, r.status_code)


def test_not_found():
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq
    from sirepo import srunit

    fc = srunit.flask_client()
    for uri in ('/some random uri', '/srw/wrong-param', '/export-archive'):
        resp = fc.get(uri)
        pkeq(404, resp.status_code)


def test_uri_for_api():
    from sirepo import srunit

    def t():
        from pykern.pkdebug import pkdp
        from pykern.pkunit import pkeq, pkexcept, pkre, pkeq
        from sirepo import uri_router
        import re

        fc = srunit.flask_client()
        uri = uri_router.uri_for_api('homePage', params={'path_info': None})
        pkre('http://[^/]+/en$', uri)
        uri = uri_router.uri_for_api(
            'homePage',
            params={'path_info': 'terms.html'},
            external=False,
        )
        pkeq('/en/terms.html', uri)
        with pkexcept(KeyError):
            uri_router.uri_for_api('notAnApi')
        with pkexcept('missing parameter'):
            uri_router.uri_for_api('exportArchive', {'simulation_type': 'srw'})

    srunit.test_in_request(t)
