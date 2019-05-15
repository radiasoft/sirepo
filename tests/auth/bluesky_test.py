# -*- coding: utf-8 -*-
u"""test sirepo.bluesky

:copyright: Copyright (c) 2018 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

pytest.importorskip('srwl_bl')

def test_auth_hash(monkeypatch):
    from pykern import pkconfig

    pkconfig.reset_state_for_testing({
        'SIREPO_AUTH_METHODS': 'bluesky',
        'SIREPO_AUTH_BLUESKY_SECRET': 'a simple string is fine',
        'SIREPO_FEATURE_CONFIG_SIM_TYPES': 'srw:myapp',
    })
    from sirepo.auth import bluesky
    from pykern import pkcollections
    from pykern.pkunit import pkexcept, pkre
    import time
    import werkzeug.exceptions

    bluesky.init_apis()
    monkeypatch.setattr(bluesky, '_AUTH_NONCE_REPLAY_SECS', 1)
    req = pkcollections.Dict(
        simulationType='xyz',
        simulationId='1234',
    )
    bluesky.auth_hash(req)
    bluesky.auth_hash(req, verify=True)
    time.sleep(2)
    with pkexcept(werkzeug.exceptions.Unauthorized):
        bluesky.auth_hash(req, verify=True)


def test_auth_hash_copy():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing({
        'SIREPO_AUTH_BLUESKY_SECRET': 'anything',
        'SIREPO_AUTH_METHODS': 'bluesky',
        'SIREPO_FEATURE_CONFIG_SIM_TYPES': 'srw:myapp',
    })
    from pykern import pkcollections
    from pykern.pkunit import pkeq
    from sirepo.auth import bluesky
    import base64
    import hashlib
    import numconv
    import random
    import time
    bluesky.init_apis()

    req = dict(
        simulationType='xyz',
        simulationId='1234',
    )
    r = random.SystemRandom()
    req['authNonce'] = str(int(time.time())) + '-' + ''.join(
        r.choice(numconv.BASE62) for x in range(32)
    )
    h = hashlib.sha256()
    h.update(
        ':'.join([
            req['authNonce'],
            req['simulationType'],
            req['simulationId'],
            bluesky.cfg.secret,
        ]),
    )
    req['authHash'] = 'v1:' + base64.urlsafe_b64encode(h.digest())
    bluesky.auth_hash(pkcollections.Dict(req), verify=True)


def test_auth_login():
    from pykern import pkcollections
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq, pkexcept
    from sirepo import srunit

    fc = srunit.flask_client(cfg={
        'SIREPO_AUTH_BLUESKY_SECRET': '3SExmbOzn1WeoCWeJxekaE6bMDUj034Pu5az1hLNnvENyvL1FAJ1q3eowwODoa3f',
        'SIREPO_AUTH_METHODS': 'bluesky:guest',
        'SIREPO_FEATURE_CONFIG_SIM_TYPES': 'srw:myapp',
    })
    from sirepo import simulation_db
    from sirepo.auth import bluesky
    import werkzeug.exceptions

    sim_type = 'srw'
    uid = fc.sr_login_as_guest(sim_type)
    data = fc.sr_post(
        'listSimulations',
        {'simulationType': 'srw', 'search': {'simulationName': 'Bending Magnet Radiatin'}},
    )
    fc.cookie_jar.clear()
    fc.sr_get('authState')
    data = data[0].simulation
    req = pkcollections.Dict(
        simulationType='srw',
        simulationId=data.simulationId,
    )
    bluesky.auth_hash(req)
    resp = fc.sr_post('authBlueskyLogin', req)
    pkeq('ok', resp['state'])
    pkeq(req.simulationId, simulation_db.parse_sid(resp['data']))
    pkeq('srw', resp['schema']['simulationType'])
    req.authHash = 'not match'
    resp = fc.sr_post('authBlueskyLogin', req, raw_response=True)
    pkeq(401, resp.status_code)
