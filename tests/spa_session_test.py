# -*- coding: utf-8 -*-
"""test if spa_session is working

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_begin(fc):
    from pykern import pkunit, pkio, pkdebug
    import time

    # see job_driver.local
    p = fc.sr_user_dir().join("agent-local", "*")
    pkunit.pkeq([], pkio.sorted_glob(p))
    fc.sr_sim_data()
    for _ in range(fc.timeout_secs()):
        if len(pkio.sorted_glob(p)) > 0:
            break
        time.sleep(1)
    else:
        pkunit.pkfail("agent_dir={} is empty so agent never started", p)
