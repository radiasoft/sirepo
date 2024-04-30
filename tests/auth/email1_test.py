"""Test auth.email

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import re


def test_different_email(auth_fc):
    fc = auth_fc

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp

    r = fc.sr_post(
        "authEmailLogin",
        {"email": "diff@b.c", "simulationType": fc.sr_sim_type},
    )
    s = fc.sr_auth_state(isLoggedIn=False)
    fc.sr_email_confirm(r)
    s = fc.sr_auth_state(isLoggedIn=True, needCompleteRegistration=True)
    fc.sr_post(
        "authCompleteRegistration",
        {
            "displayName": "abc",
            "simulationType": fc.sr_sim_type,
        },
    )
    t = fc.sr_auth_state(userName="diff@b.c", displayName="abc")
    fc.sr_logout()
    uid = fc.sr_auth_state(userName=None, isLoggedIn=False).uid
    r = fc.sr_post(
        "authEmailLogin", {"email": "x@y.z", "simulationType": fc.sr_sim_type}
    )
    fc.sr_email_confirm(r, "xyz")
    uid2 = fc.sr_auth_state(displayName="xyz", isLoggedIn=True, userName="x@y.z").uid
    pkok(uid != uid2, "did not get a new uid={}", uid)


def test_follow_email_auth_link_twice(auth_fc):
    fc = auth_fc

    from pykern import pkconfig, pkunit, pkio, pkcompat
    from pykern.pkunit import pkok, pkre, pkexcept
    from pykern.pkdebug import pkdp
    import json

    r = fc.sr_post(
        "authEmailLogin",
        {"email": "follow@b.c", "simulationType": fc.sr_sim_type},
    )
    # The link comes back in dev mode so we don't have to check email
    s = fc.sr_auth_state(isLoggedIn=False)
    fc.sr_email_confirm(r)
    # post to the url twice - should still be logged in, but not found
    fc.sr_get(r.uri, redirect=False).assert_http_redirect("/myapp#/simulations")
    fc.sr_logout()
    # now logged out, should see login fail for bad link
    fc.sr_get(r.uri, redirect=False).assert_http_redirect(
        "/login-fail/email/email-token"
    )


def test_force_login(auth_fc):
    fc = auth_fc

    from pykern import pkcollections
    from pykern import pkconfig, pkunit, pkio
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkok, pkre, pkeq, pkexcept
    from sirepo import util

    # login as a new user, not in db
    r = fc.sr_post(
        "authEmailLogin", {"email": "force@b.c", "simulationType": fc.sr_sim_type}
    )
    fc.sr_email_confirm(r)
    fc.sr_logout()
    fc.assert_post_will_redirect(
        "login", "listSimulations", {"simulationType": fc.sr_sim_type}, redirect=False
    )
    r = fc.sr_post(
        "authEmailLogin", {"email": "force@b.c", "simulationType": fc.sr_sim_type}
    )
    fc.sr_email_confirm(r)
    fc.sr_post(
        "authCompleteRegistration",
        {
            "displayName": "xyz",
            "simulationType": fc.sr_sim_type,
        },
    )
    d = fc.sr_post("listSimulations", {"simulationType": fc.sr_sim_type})
    pkeq(1, len(d))


def test_guest_merge(auth_fc):
    fc = auth_fc

    from pykern.pkunit import pkeq
    from pykern.pkdebug import pkdp

    # Start as a guest user
    fc.sr_login_as_guest(fc.sr_sim_type)
    d = fc.sr_post(
        "listSimulations",
        {"simulationType": fc.sr_sim_type},
    )
    pkeq(1, len(d), "expecting only one simulation: data={}", d)
    d = d[0].simulation
    # Copy a sim as a guest user
    d = fc.sr_post(
        "copySimulation",
        dict(
            simulationId=d.simulationId,
            simulationType=fc.sr_sim_type,
            name="guest-sim",
            folder="/",
        ),
    )
    guest_uid = fc.sr_uid

    # Convert to email user
    r = fc.sr_post(
        "authEmailLogin",
        {"email": "guest.merge@b.com", "simulationType": fc.sr_sim_type},
    )
    s = fc.sr_auth_state(isLoggedIn=True, method="guest")
    fc.sr_email_confirm(r)
    fc.sr_post(
        "authCompleteRegistration",
        {
            "displayName": "abc",
            "simulationType": fc.sr_sim_type,
        },
    )
    r = fc.sr_auth_state(method="email", uid=guest_uid)
    d = fc.sr_sim_data()
    # Copy sim as an email user
    d = fc.sr_post(
        "copySimulation",
        dict(
            simulationId=d.models.simulation.simulationId,
            simulationType=fc.sr_sim_type,
            name="email-sim",
            folder="/",
        ),
    )
    fc.sr_logout()

    # Login as email user
    r = fc.sr_post(
        "authEmailLogin",
        {"email": "guest.merge@b.com", "simulationType": fc.sr_sim_type},
    )
    fc.sr_email_confirm(r)
    d = fc.sr_post(
        "listSimulations",
        {"simulationType": fc.sr_sim_type},
    )
    # Sims from guest and email present
    pkeq(["Scooby Doo", "email-sim", "guest-sim"], sorted([x.name for x in d]))


def test_happy_path(auth_fc):
    fc = auth_fc

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp

    # login as a new user, not in db
    r = fc.sr_post(
        "authEmailLogin", {"email": "happy@b.c", "simulationType": fc.sr_sim_type}
    )
    fc.sr_email_confirm(r)
    fc.sr_post(
        "authCompleteRegistration",
        {
            "displayName": "abc",
            "simulationType": fc.sr_sim_type,
        },
    )
    fc.sr_post("listSimulations", {"simulationType": fc.sr_sim_type})
    uid = fc.sr_auth_state(
        avatarUrl="https://www.gravatar.com/avatar/6932801af90f249078f2a3677178ca51?d=mp&s=40",
        displayName="abc",
        isLoggedIn=True,
        userName="happy@b.c",
    ).uid
    r = fc.sr_logout()
    fc.sr_auth_state(
        displayName=None,
        isLoggedIn=False,
        needCompleteRegistration=False,
        uid=uid,
        userName=None,
    )


def test_multiple_unverified_users(auth_fc):
    fc = auth_fc

    for e in ("1@x.x", "2@x.x"):
        r = fc.sr_post(
            "authEmailLogin",
            {"email": e, "simulationType": fc.sr_sim_type},
        )
    fc.sr_email_confirm(r)
    fc.sr_auth_state(isLoggedIn=True)


def test_token_expired(auth_fc):
    fc = auth_fc

    r = fc.sr_post(
        "authEmailLogin",
        {"email": "expired@b.c", "simulationType": fc.sr_sim_type},
    )
    with fc.sr_adjust_time(1):
        r = fc.sr_email_confirm(r)
        fc.sr_auth_state(isLoggedIn=False)
