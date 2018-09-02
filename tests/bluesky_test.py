# -*- coding: utf-8 -*-
u"""test sirepo.bluesky

:copyright: Copyright (c) 2018 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_auth_hash(monkeypatch):
    from pykern import pkconfig

    pkconfig.reset_state_for_testing({
        'SIREPO_FEATURE_CONFIG_API_MODULES': 'bluesky',
        'SIREPO_BLUESKY_AUTH_SECRET': 'a simple string is fine',
    })
    from sirepo import bluesky
    from pykern import pkcollections
    from pykern.pkunit import pkexcept, pkre
    import time
    import werkzeug.exceptions

    monkeypatch.setattr(bluesky, '_AUTH_NONCE_REPLAY_SECS', 1)
    req = pkcollections.Dict(
        simulationType='xyz',
        simulationId='1234',
    )
    bluesky.auth_hash(req)
    bluesky.auth_hash(req, verify=True)
    time.sleep(2)
    with pkexcept(werkzeug.exceptions.NotFound):
        bluesky.auth_hash(req, verify=True)


def test_auth_hash_copy():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing({
        'SIREPO_FEATURE_CONFIG_API_MODULES': 'bluesky',
        'SIREPO_BLUESKY_AUTH_SECRET': 'anything',
    })
    from pykern import pkcollections
    from pykern.pkunit import pkeq
    from sirepo import bluesky
    import base64
    import hashlib
    import numconv
    import random
    import time

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
            bluesky.cfg.auth_secret,
        ]),
    )
    req['authHash'] = 'v1:' + base64.urlsafe_b64encode(h.digest())
    bluesky.auth_hash(pkcollections.Dict(req), verify=True)


def test_auth_login():
    from pykern import pkcollections
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq
    from sirepo import sr_unit

    fc = sr_unit.flask_client({
        'SIREPO_FEATURE_CONFIG_API_MODULES': 'bluesky',
        'SIREPO_BLUESKY_AUTH_SECRET': '3SExmbOzn1WeoCWeJxekaE6bMDUj034Pu5az1hLNnvENyvL1FAJ1q3eowwODoa3f',
    })
    from sirepo import simulation_db
    from sirepo import bluesky
    from sirepo import cookie

    fc.get('/srw')
    data = fc.sr_post(
        'listSimulations',
        {'simulationType': 'srw', 'search': {'simulationName': 'Bending Magnet Radiation'}},
    )
    fc.cookie_jar.clear()
    data = data[0].simulation
    req = pkcollections.Dict(
        simulationType='srw',
        simulationId=data.simulationId,
    )
    bluesky.auth_hash(req)
    resp = fc.sr_post('blueskyAuth', req)
    pkeq('ok', resp['state'])
    pkeq(req.simulationId, simulation_db.parse_sid(resp['data']))
    pkeq('srw', resp['schema']['simulationType'])
