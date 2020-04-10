# -*- coding: utf-8 -*-
u"""test sirepo.bluesky

:copyright: Copyright (c) 2018 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_srw_auth_hash(monkeypatch):
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


def test_srw_auth_hash_copy():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing({
        'SIREPO_AUTH_BLUESKY_SECRET': 'anything',
        'SIREPO_AUTH_METHODS': 'bluesky',
        'SIREPO_FEATURE_CONFIG_SIM_TYPES': 'srw:myapp',
    })
    from pykern import pkcollections
    from pykern import pkcompat
    from pykern.pkdebug import pkdp
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
        pkcompat.to_bytes(
            ':'.join([
                req['authNonce'],
                req['simulationType'],
                req['simulationId'],
                bluesky.cfg.secret,
            ]),
        ),
    )
    req['authHash'] = 'v1:' + pkcompat.from_bytes(
        base64.urlsafe_b64encode(h.digest()),
    )
    bluesky.auth_hash(pkcollections.Dict(req), verify=True)
