"""Concurrency testing

This test does not always fail when there is a problem (false
positive), because it depends on a specific sequence of events
that can't be controlled by the test.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html

"""

import pytest


def test_myapp_cancel(fc):
    """https://github.com/radiasoft/sirepo/issues/2346"""
    from pykern import pkunit
    import time
    from pykern.pkdebug import pkdlog

    d1 = fc.sr_sim_data()
    d1.models.simulation.name = "srunit_long_run"
    d2 = fc.sr_post(
        "copySimulation",
        dict(
            simulationId=d1.models.simulation.simulationId,
            simulationType=fc.sr_sim_type,
            name="sim2",
            folder="/",
        ),
    )
    report = "heightWeightReport"

    def _t2(fc, sim_data):
        pkdlog("start 2")
        r2 = fc.sr_post(
            "runSimulation",
            dict(
                forceRun=False,
                models=sim_data.models,
                report=report,
                simulationId=sim_data.models.simulation.simulationId,
                simulationType=sim_data.simulationType,
            ),
        )
        pkdlog(r2)
        for _ in range(40):
            time.sleep(0.1)
            pkunit.pkok(r2.state != "error", "unexpected error state: {}")
            if r2.state == "running":
                pkdlog("running")
                break
            pkunit.pkeq("pending", r2.state)
            r2 = fc.sr_post("runStatus", r2.nextRequest)
        else:
            pkunit.pkfail("runStatus: failed to start running: {}", r2)
        return r2

    pkdlog("start 1")
    r1 = fc.sr_post(
        "runSimulation",
        dict(
            forceRun=False,
            models=d1.models,
            report=report,
            simulationId=d1.models.simulation.simulationId,
            simulationType=d1.simulationType,
        ),
    )
    for _ in range(100):
        pkdlog(r1)
        pkunit.pkok(r1.state != "error", "unexpected error state: {}")
        if r1.state == "running":
            break
        time.sleep(0.1)
        r1 = fc.sr_post("runStatus", r1.nextRequest)
    else:
        pkunit.pkfail("runStatus: failed to start running: {}", r1)
    fc.sr_thread_start("sim2", _t2, sim_data=d2)
    time.sleep(1)
    pkdlog("runCancel 1")
    fc.sr_post("runCancel", r1.nextRequest)
    pkunit.pkeq("canceled", fc.sr_post("runStatus", r1.nextRequest).state)
    r2 = fc.sr_thread_join().sim2
    fc.sr_post("runCancel", r2.nextRequest)
    pkunit.pkeq("canceled", fc.sr_post("runStatus", r2.nextRequest).state)


def test_elegant_concurrent_sim_frame(fc):
    """https://github.com/radiasoft/sirepo/issues/2474"""
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog, pkdp
    import sirepo.sim_data
    import time

    def _get_frames(fc):
        for i in range(3):
            f = fc.sr_get_json(
                "simulationFrame",
                PKDict(frame_id=s.frame_id(d, r1, "elementAnimation19-5", 0)),
            )
            pkunit.pkeq("completed", f.state)

    def _t2(fc):
        _get_frames(fc)

    d = fc.sr_sim_data(sim_name="Backtracking", sim_type="elegant")
    s = sirepo.sim_data.get_class(fc.sr_sim_type)
    r = "animation"
    r1 = PKDict()
    try:
        pkdlog("start 1")
        r1 = fc.sr_post(
            "runSimulation",
            dict(
                forceRun=False,
                models=d.models,
                report=r,
                simulationId=d.models.simulation.simulationId,
                simulationType=d.simulationType,
            ),
        )
        for _ in range(20):
            pkunit.pkok(r1.state != "error", "unexpected error state: {}")
            if r1.state == "completed":
                break
            time.sleep(1)
            r1 = fc.sr_post("runStatus", r1.nextRequest)
        else:
            pkunit.pkfail("runStatus: failed to complete: {}", r1)
        fc.sr_thread_start("t2", _t2)
        _get_frames(fc)
        fc.sr_thread_join()
    finally:
        if r1.get("nextRequest"):
            fc.sr_post("runCancel", r1.nextRequest)
