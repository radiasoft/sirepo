"""test running of animations through sbatch

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# If you see: _timeout MAX_CASE_RUN_SECS=120 exceeded
# Run sinfo to see if slurmd is down for this node.
# https://github.com/radiasoft/sirepo/issues/2136
# sudo scontrol <<EOF
# update NodeName=debug State=DOWN Reason=undraining
# update NodeName=debug State=RESUME
# EOF


def test_srw_cancel(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq, pkfail, pkok
    import subprocess
    import time

    def _squeue_num_jobs():
        # slurm is a shared resource (not unique to each test) so this
        # has the potential to conflict with jobs users have started
        # outside of tests.
        # Will be fixed by https://github.com/radiasoft/sirepo/issues/7012
        # -1 to remove header line
        return int(subprocess.check_output("squeue | wc -l", shell=True)) - 1

    pkeq(0, _squeue_num_jobs())
    sim_name = "Young's Double Slit Experiment"
    compute_model = "multiElectronAnimation"
    fc.sr_sbatch_login(compute_model, sim_name)
    d = fc.sr_sim_data(sim_name=sim_name)
    d.models[compute_model].jobRunMode = fc.sr_job_run_mode
    r = fc.sr_post(
        "runSimulation",
        PKDict(
            models=d.models,
            report=compute_model,
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
        expect_completed=False,
    )

    for _ in range(5):
        pkok(
            r.state in ("running", "pending"),
            "runSimulation did not start: reply={}",
            r,
        )
        if r.state == "running" and _squeue_num_jobs() == 1:
            break
        time.sleep(5)
        r = fc.sr_post("runStatus", r.nextRequest)
    else:
        pkfail("failed to start running in sirepo and slurm reply={}", r)
    r = fc.sr_post("runCancel", r.nextRequest)
    for _ in range(5):
        if _squeue_num_jobs() == 0:
            break
        time.sleep(5)
    else:
        pkfail("runCancel: failed to cancel in slurm")


def test_srw_data_file(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq

    a = "Young's Double Slit Experiment"
    c = "multiElectronAnimation"
    fc.sr_sbatch_animation_run(
        a,
        c,
        PKDict(
            multiElectronAnimation=PKDict(
                # Prevents "Memory Error" because SRW uses computeJobStart as frameCount
                frame_index=0,
                expect_title="E=4240 eV",
            ),
        ),
        expect_completed=False,
    )
    d = fc.sr_sim_data(a)
    r = fc.sr_get(
        "downloadRunFile",
        PKDict(
            simulation_type=d.simulationType,
            simulation_id=d.models.simulation.simulationId,
            model=c,
            frame="0",
        ),
    )
    r.assert_http_status(200)


def test_warppba_invalid_creds(new_user_fc):
    from pykern.pkunit import pkexcept

    with pkexcept("SRException.*invalid-creds"):
        _warppba_login(new_user_fc, username="vagrant", password="incorrect password")


def test_warppba_login(new_user_fc):
    from pykern.pkunit import pkexcept

    x = _warppba_login(new_user_fc, username="vagrant", password="vagrant")
    new_user_fc.sr_run_sim(*x, expect_completed=False)


def test_warppba_no_creds(new_user_fc):
    from pykern.pkunit import pkexcept

    x = _warppba_login_setup(new_user_fc)
    with pkexcept("SRException.*no-creds"):
        new_user_fc.sr_run_sim(*x, expect_completed=False)


def _warppba_login(fc, username, password):
    from pykern.pkcollections import PKDict
    from pykern import pkunit
    from sirepo import util

    d, c = _warppba_login_setup(fc)
    try:
        r = fc.sr_run_sim(d, c, expect_completed=False)
        pkunit.pkfail("did not raise SRException reply={}", r)
    except util.SRException as e:
        p = e.sr_args.params
    fc.sr_post(
        "sbatchLogin",
        PKDict(
            password=password,
            computeModel=p.computeModel,
            simulationId=p.simulationId,
            simulationType=d.simulationType,
            username=username,
        ),
    )
    return d, c


def _warppba_login_setup(fc):
    return fc.sr_sim_data("Laser Pulse"), "animation"
