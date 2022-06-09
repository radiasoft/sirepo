# -*- coding: utf-8 -*-
u"""Test sirepo.uri_router

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
pytest.importorskip('srwl_bl')


def test_error_for_bots():
    from pykern import pkcompat
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq, pkexcept, pkok, pkre
    from sirepo import http_request
    from sirepo import srunit

    fc = srunit.flask_client()
    fc.sr_login_as_guest()

    uri = '/get-application-data'
    d = PKDict(simulationType='srw', method='NO SUCH METHOD')

    # "Real" browsers get redirected to an error page with a 200 status
    for a in (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.128 Safari/537.36 OPR/75.0.3969.250',
    ):
        r = fc.post( uri, environ_base=PKDict(HTTP_USER_AGENT=a), json=d)
        pkeq(200, r.status_code)
        pkre('/error', r.data)

    for a in (
        'python-requests/1.3',
        'python-requests/2.0',
    ):
        r = fc.post(uri, environ_base=PKDict(HTTP_USER_AGENT=a), json=d)
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
        pkeq('/', uri_router.uri_for_api('root', params={}, external=False))

    srunit.test_in_request(t)
