"""test sirepo.bluesky

:copyright: Copyright (c) 2018 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest
from pykern.pkcollections import PKDict


pytestmark = pytest.mark.sirepo_args(
    fc_module=PKDict(
        cfg=PKDict(
            {
                "SIREPO_AUTH_BLUESKY_SECRET": "3SExmbOzn1WeoCWeJxekaE6bMDUj034Pu5az1hLNnvENyvL1FAJ1q3eowwODoa3f",
                "SIREPO_AUTH_METHODS": "bluesky:guest",
                "SIREPO_FEATURE_CONFIG_SIM_TYPES": "srw:myapp",
            },
        ),
    ),
)


def test_srw_auth_login(fc):
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq, pkexcept
    from sirepo import srunit

    from sirepo import simulation_db
    from sirepo.auth import bluesky

    sim_type = "srw"
    uid = fc.sr_login_as_guest(sim_type)
    data = fc.sr_post(
        "listSimulations",
        {"simulationType": "srw"},
    )
    fc.cookie_jar.clear()
    fc.sr_get("authState")
    data = data[0].simulation
    req = PKDict(
        simulationType="srw",
        simulationId=data.simulationId,
    )
    bluesky.auth_hash(req)
    r = fc.sr_post("authBlueskyLogin", req)
    pkeq("ok", r["state"])
    pkeq(req.simulationId, r.data.models.simulation.simulationId)
    pkeq("srw", r["schema"]["simulationType"])
    req.authHash = "not match"
    r = fc.sr_post("authBlueskyLogin", req, raw_response=True)
    r.assert_http_status(401)
    # DEPRECATED
    fc.cookie_jar.clear()
    bluesky.auth_hash(req)
    r = fc.sr_post("blueskyAuth", req)
    pkeq("ok", r["state"])
    pkeq(req.simulationId, r.data.models.simulation.simulationId)
