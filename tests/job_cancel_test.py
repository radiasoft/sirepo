"""test cancel of sim with agent_start_delay

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_REPORT = "heightWeightReport"


def test_myapp(fc):
    from pykern import pkunit

    from pykern.pkdebug import pkdc, pkdp, pkdlog
    from pykern.pkcollections import PKDict

    d = fc.sr_sim_data()
    # TODO(robnagler) this does not work see:
    # https://github.com/radiasoft/sirepo/issues/7400
    # d.models.dog.favoriteTreat = "agent_start_delay=5"
    x = dict(
        forceRun=False,
        models=d.models,
        report=_REPORT,
        simulationId=d.models.simulation.simulationId,
        simulationType=d.simulationType,
    )
    fc.sr_thread_start("t1", _t1, sim_data=x)
    fc.sr_thread_start("t2", _t2, sim_data=x)
    fc.sr_thread_join()
    # t2 already asserts canceled so must be true
    pkunit.pkeq("canceled", fc.sr_post("runStatus", x).state)
    r = fc.sr_run_sim(d, _REPORT)
    p = r.get("plots")
    pkunit.pkok(p, "expecting truthy r.plots={}", p)


def _t1(fc, sim_data):
    from pykern import pkunit

    fc.sr_post("runSimulation", sim_data)
    # t2 is operating asynchronously so just allow any of these
    _state_eq(fc, sim_data, ["pending", "running", "canceled"])


def _t2(fc, sim_data):
    import time
    from pykern import pkunit

    # Make sure pending or running before canceling
    _state_eq(fc, sim_data, ["pending", "running"])
    fc.sr_post("runCancel", sim_data)
    # runCancel changes job state immediately
    pkunit.pkeq("canceled", fc.sr_post("runStatus", sim_data).state)


def _state_eq(fc, req, expect):
    import time
    from pykern import pkunit

    for _ in range(5):
        time.sleep(1)
        r = fc.sr_post("runStatus", req)
        if r.state in expect:
            return r
    else:
        pkunit.pkfail("expect={} != actual={}", expect, r.state)
