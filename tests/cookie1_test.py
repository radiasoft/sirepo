"""test missing cookies

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_missing_cookies(fc):
    from pykern.pkunit import pkeq, pkre
    from pykern.pkcollections import PKDict
    from pykern import pkdebug
    from sirepo import srunit

    d = fc.sr_sim_data()
    fc.cookie_jar.clear()
    fc.assert_post_will_redirect(
        "missing-cookies",
        "listSimulations",
        PKDict(
            simulationType=fc.sr_sim_type,
            search=PKDict({"simulation.nampe": srunit.SR_SIM_NAME_DEFAULT}),
        ),
        want_http=True,
        redirect=False,
    )
    # only needed for ui_websocket
    fc.assert_post_will_redirect(
        "login",
        "listSimulations",
        PKDict(
            simulationType=fc.sr_sim_type,
            search=PKDict({"simulation.name": srunit.SR_SIM_NAME_DEFAULT}),
        ),
        redirect=False,
    )
