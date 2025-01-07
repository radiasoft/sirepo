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
    from pykern import pkunit

    r = fc.sr_run_sim(
        fc.sr_sim_data("Young's Double Slit Experiment"),
        "multiElectronAnimation",
        expect_completed=False,
        timeout=20,
    )
    pkunit.pkeq("canceled", r.state)


def test_myapp_analysis(fc):
    from pykern.pkcollections import PKDict
    from pykern import pkunit
    from pykern.pkdebug import pkdp

    d = fc.sr_sim_data()
    # If a machine is slow, this might timeout on getting the heightWeightReport
    # in analysis when we want to get to the too large error (413) below.
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
