"""Test that ops waiting in _agent_ready are canceled when agent start times out

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import os


def setup_module(module):
    os.environ.update(
        SIREPO_JOB_DRIVER_LOCAL_AGENT_STARTING_SECS="1",
    )


_REPORT = "heightWeightReport"


def test_myapp(fc):
    from pykern import pkunit

    d = fc.sr_sim_data()
    d.models.dog.favoriteTreat = "agent_start_delay=10"
    x = dict(
        forceRun=False,
        models=d.models,
        report=_REPORT,
        simulationId=d.models.simulation.simulationId,
        simulationType=d.simulationType,
    )
    fc.sr_thread_start("t1", _t1, sim_data=x)
    fc.sr_thread_join()


def _t1(fc, sim_data):
    from pykern import pkunit

    r = fc.sr_post("runSimulation", sim_data)
    pkunit.pkeq("canceled", r.state)
