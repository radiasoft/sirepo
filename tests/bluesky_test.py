# -*- coding: utf-8 -*-
u"""test sirepo.bluesky

:copyright: Copyright (c) 2018 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_auth_hash():
    from pykern import pkconfig

    pkconfig.reset_state_for_testing({
        'SIREPO_BLUESKY_AUTH_SECRET': 'a simple string is fine',
    })
    from sirepo import bluesky
    from pykern import pkcollections
    from pykern.pkunit import pkeq

    req = pkcollections.Dict(
        simulationType='xyz',
        simulationId='1234',
        authNonce='some random string',
    )
    bluesky.auth_hash(req)
    pkeq('v1:-TEGBNOAt9dCTtCCvRD0WHtL_XaZR_lHM37cy6PePwE=', req.authHash)


def test_auth_login():
    from pykern import pkcollections
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq
    from sirepo import sr_unit

    fc = sr_unit.flask_client(
        cfg=dict(
            SIREPO_BLUESKY_AUTH_SECRET='3SExmbOzn1WeoCWeJxekaE6bMDUj034Pu5az1hLNnvENyvL1FAJ1q3eowwODoa3f',
        ),
    )
    from sirepo import simulation_db
    from sirepo import bluesky

    fc.get('/srw')
    data = fc.sr_post(
        'listSimulations',
        {'simulationType': 'srw', 'search': {'simulationName': 'Bending Magnet Radiation'}},
    )
    data = data[0].simulation
    req = pkcollections.Dict(
        simulationType='srw',
        simulationId=data.simulationId,
    )
    bluesky.auth_hash(req)
    data = fc.sr_post('blueskyAuth', req)
    pkeq(req.simulationId, simulation_db.parse_sid(data['data']))
