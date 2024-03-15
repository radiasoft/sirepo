"""test for canceling a long running simulation due to a timeout

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_MAX_SECS_PARALLEL_PREMIUM = "4"


def setup_module(module):
    import os

    os.environ.update(
        SIREPO_JOB_SUPERVISOR_MAX_SECS_PARALLEL_PREMIUM=_MAX_SECS_PARALLEL_PREMIUM,
        SIREPO_JOB_SUPERVISOR_MAX_SECS_ANALYSIS="6",
        SIREPO_JOB_SUPERVISOR_MAX_SECS_IO="6",
    )


def test_srw(fc):
    from pykern.pkcollections import PKDict
    from pykern import pkunit, pkcompat
    from pykern.pkdebug import pkdlog, pkdexc
    import time

    m = "multiElectronAnimation"
    data = fc.sr_sim_data("Young's Double Slit Experiment")
    try:
        r = fc.sr_post(
            "runSimulation",
            PKDict(
                models=data.models,
                report=m,
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
            ),
        )
        if r.state == "completed":
            return r
        cancel = r.get("nextRequest")
        for _ in range(20):
            if r.state == "canceled":
                pkunit.pkeq(
                    int(_MAX_SECS_PARALLEL_PREMIUM),
                    r.canceledAfterSecs,
                )
                cancel = None
                break
            r = fc.sr_post("runStatus", r.nextRequest)
            time.sleep(1)
        else:
            pkunit.pkfail("did not cancel in time")
    finally:
        if cancel:
            fc.sr_post("runCancel", cancel)
        import subprocess

        o = pkcompat.from_bytes(
            subprocess.check_output(["ps", "axww"], stderr=subprocess.STDOUT),
        )
        o = list(filter(lambda x: "mpiexec" in x, o.split("\n")))
        if o:
            pkdlog('found "mpiexec" after cancel in ps={}', "\n".join(o))
            raise AssertionError("cancel failed")


def test_myapp_analysis(fc):
    from pykern.pkcollections import PKDict
    from pykern import pkunit
    from pykern.pkdebug import pkdp

    d = fc.sr_sim_data()
    # If a machine is slow, this might timeout on getting the heightWeightReport
    # in analysis when we want the timeout below.
    r = fc.sr_run_sim(d, "heightWeightReport", expect_completed=True)
    r = fc.sr_get(
        "downloadRunFile",
        PKDict(
            simulation_type=d.simulationType,
            simulation_id=d.models.simulation.simulationId,
            model="heightWeightReport",
            frame="-1",
            suffix="sr_long_analysis",
        ),
    )
    r.assert_http_status(413)
