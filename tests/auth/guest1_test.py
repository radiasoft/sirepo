"""Test auth.guest

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_happy_path(auth_fc):
    fc = auth_fc

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre, pkeq
    from pykern.pkdebug import pkdp
    import re

    fc.sr_get("authGuestLogin", {"simulation_type": fc.sr_sim_type})
    fc.sr_post("listSimulations", {"simulationType": fc.sr_sim_type})
    fc.sr_auth_state(
        avatarUrl=None,
        displayName="Guest User",
        guestIsOnlyMethod=False,
        isGuestUser=True,
        isLoggedIn=True,
        method="guest",
        needCompleteRegistration=False,
        userName=None,
        visibleMethods=["email"],
    )
