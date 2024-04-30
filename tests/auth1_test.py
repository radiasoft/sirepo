"""Test sirepo.auth

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_login():
    from sirepo import srunit

    with srunit.quest_start() as qcall:
        from pykern import pkunit, pkcompat, pkdebug
        from pykern.pkunit import pkeq, pkok, pkre, pkfail, pkexcept
        from sirepo import util
        from sirepo.auth import guest

        r = qcall.call_api_sync("authState")
        pkre('LoggedIn": false.*Registration": false', r.content_as_str())
        r.destroy()
        r = None
        with pkunit.pkexcept("SRException.*routeName=login"):
            qcall.auth.logged_in_user()
        with pkexcept("SRException.*routeName=login"):
            qcall.auth.require_user()
        qcall.cookie.set_sentinel()
        try:
            r = qcall.auth.login("guest", sim_type="myapp")
            pkfail("expecting sirepo.util.SReplyExc")
        except util.SReplyExc as e:
            r = e.sr_args.sreply
        a = r.content_as_object().authState
        pkeq(True, a.isLoggedIn)
        pkeq(False, a.needCompleteRegistration)
        u = qcall.auth.logged_in_user()
        pkok(u, "user should exist")
        # guests do not require completeRegistration
        qcall.auth.require_user()
