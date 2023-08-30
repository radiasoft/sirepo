# -*- coding: utf-8 -*-
"""more server tests

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_user_alert(fc):
    from pykern.pkunit import pkeq, pkre
    from pykern.pkdebug import pkdp
    from sirepo import srunit

    d = fc.sr_sim_data()
    d.models.dog.breed = "user_alert=user visible text"
    r = fc.sr_run_sim(d, "heightWeightReport", expect_completed=False)
    pkeq("error", r.state)
    pkeq("user visible text", r.error)
