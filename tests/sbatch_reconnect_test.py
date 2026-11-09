"""test sbatch agent reconnecting after the supervisor closes its websocket

Separate from sbatch_test, because of the ping config.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import pytest

# Supervisor closes the websocket if the agent does not answer a ping. Not too
# short, because the agent is blocked for a few seconds when it starts a run.
pytestmark = pytest.mark.sirepo_args(
    fc_module=PKDict(
        cfg=PKDict(
            SIREPO_JOB_PING_INTERVAL_SECS="5",
            SIREPO_JOB_PING_TIMEOUT_SECS="5",
        ),
    ),
)


def test_srw_agent_reconnect(new_user_fc):
    """Agent that is alive reconnects by itself, no login required

    A stopped agent does not answer pings so the supervisor closes the websocket.
    The supervisor must keep what it needs (srdb_root) to use the agent when
    it reconnects after being continued. Without that, every op gets no-creds,
    and sbatchLogin says "ok" without doing anything, since the websocket is up.
    """
    from pykern.pkunit import pkeq, pkok
    import os
    import signal

    f = new_user_fc
    d, c = _srw_login(f)
    p = _agent_pid(f)
    pkok(_login_status(f, d, c).ready, "not ready after login")
    os.kill(p, signal.SIGSTOP)
    try:
        _wait_ready(f, d, c, False, "supervisor to close websocket")
    finally:
        # always resume, or the agent is left stopped
        os.kill(p, signal.SIGCONT)
    _wait_ready(f, d, c, True, "agent to reconnect")
    # Not a new agent
    pkeq(p, _agent_pid(f))
    # Raises SRException (no-creds) if the supervisor forgot srdb_root on close
    f.sr_run_sim(d, c, expect_completed=False, timeout=5)


def test_srw_op_waits_for_agent_reconnect(new_user_fc):
    """An op that arrives after the close and before the reconnect waits

    Otherwise, the op tries to start an agent, which needs credentials that are
    gone, so the user is asked to login even though the agent comes back.
    """
    from pykern.pkunit import pkeq, pkok
    import os
    import signal
    import threading

    f = new_user_fc
    d, c = _srw_login(f)
    p = _agent_pid(f)
    os.kill(p, signal.SIGSTOP)
    t = threading.Timer(3, os.kill, (p, signal.SIGCONT))
    try:
        _wait_ready(f, d, c, False, "supervisor to close websocket")
        t.start()
        # Agent is stopped for 3 more seconds. Op has to wait for it.
        f.sr_run_sim(d, c, expect_completed=False, timeout=5)
    finally:
        t.cancel()
        os.kill(p, signal.SIGCONT)
    pkeq(p, _agent_pid(f))
    pkok(_login_status(f, d, c).ready, "not ready after op")


def _agent_pid(fc):
    from pykern import pkio, pkjson, pkunit

    # POSIT: sirepo.srunit_servers._config_sbatch_supervisor_env srdb_root
    # and sirepo.pkcli.job_agent._PID_FILE
    return pkjson.load_any(
        pkio.py_path(
            pkunit.work_dir().join(
                fc.sr_sbatch_creds().sbatchCredentials.username,
                "sirepo",
                "job_agent.pid",
            )
        )
    ).pid


def _login_status(fc, data, compute_model):
    return fc.sr_post(
        "sbatchLoginStatus",
        PKDict(
            computeModel=compute_model,
            models=data.models,
            simulationId=data.models.simulation.simulationId,
            simulationType=data.simulationType,
        ),
    )


def _srw_login(fc):
    from pykern import pkunit
    from sirepo import util

    c = "multiElectronAnimation"
    d = fc.sr_sim_data("Young's Double Slit Experiment", compute_model=c)
    d.models.multiElectronAnimation.numberOfMacroElectrons = 50
    d.models.simulation.sampleFactor = 0.0001
    try:
        r = fc.sr_run_sim(d, c, expect_completed=False)
        pkunit.pkfail("did not raise SRException reply={}", r)
    except util.SRException:
        pass
    fc.sr_post(
        "sbatchLogin",
        fc.sr_sbatch_creds().pkupdate(
            computeModel=c,
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
    )
    return d, c


def _wait_ready(fc, data, compute_model, expect, desc, secs=60):
    from pykern import pkunit
    import time

    e = time.monotonic() + secs
    while time.monotonic() < e:
        if _login_status(fc, data, compute_model).ready == expect:
            return
        time.sleep(1)
    pkunit.pkfail("timeout secs={} waiting for {}", secs, desc)
