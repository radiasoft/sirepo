"""Login SRException raised when user dir deleted

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_myapp_user_dir_deleted(fc):
    from pykern import pkjson, pkdebug, pkunit, pkcompat
    from pykern.pkcollections import PKDict
    import sirepo.srdb

    sirepo.srdb.root().join("user", fc.sr_uid).remove(rec=1)
    fc.assert_post_will_redirect(
        "^/$",
        "listSimulations",
        PKDict(simulationType=fc.sr_sim_type),
        redirect=False,
    )
    fc.sr_auth_state(displayName=None, isLoggedIn=False, method=None)
