# -*- coding: utf-8 -*-
"""test cancel of sim with agent_start_delay

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest

_REPORT = "heightWeightReport"


def test_myapp(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp, pkdlog
    from pykern.pkcollections import PKDict

    d = fc.sr_sim_data()
    d.models.dog.favoriteTreat = "agent_start_delay=5"
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
    pkunit.pkeq("canceled", fc.sr_post("runStatus", x).state)
    r = fc.sr_run_sim(d, _REPORT)
    p = r.get("plots")
    pkunit.pkok(p, "expecting truthy r.plots={}", p)


def _t1(fc, sim_data):
    from pykern import pkunit

    fc.sr_post("runSimulation", sim_data)
    pkunit.pkeq("pending", fc.sr_post("runStatus", sim_data).state)


def _t2(fc, sim_data):
    import time
    from pykern import pkunit

    time.sleep(1)
    fc.sr_post("runCancel", sim_data)
    pkunit.pkeq("canceled", fc.sr_post("runStatus", sim_data).state)
