"""test token reuse

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_token_reuse(auth_fc):
    fc = auth_fc

    from pykern import pkconfig, pkunit, pkio
    from pykern.pkunit import pkok, pkre
    from pykern.pkdebug import pkdp

    r = fc.sr_post(
        "authEmailLogin",
        {"email": "reuse@b.c", "simulationType": fc.sr_sim_type},
    )
    fc.sr_email_confirm(r)
    s = fc.sr_auth_state(userName="reuse@b.c")
    fc.sr_logout()
    fc.sr_get(r.uri, redirect=False).assert_http_redirect("login-fail")
    fc.sr_auth_state(isLoggedIn=False)
