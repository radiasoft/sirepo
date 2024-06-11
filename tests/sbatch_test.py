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
    d = fc.sr_sim_data(sim_name=sim_name, compute_model=compute_model)
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
    for _ in fc.iter_sleep("slurm", "runStatus"):
        pkok(
            r.state in ("running", "pending"),
            "runSimulation did not start: reply={}",
            r,
        )
        if r.state == "running" and _squeue_num_jobs() == 1:
            break
        r = fc.sr_post("runStatus", r.nextRequest)
    r = fc.sr_post("runCancel", r.nextRequest)
    for _ in fc.iter_sleep("slurm", "runCancel"):
        if _squeue_num_jobs() == 0:
            break


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
    # TODO(robnagler) jobRunMode needs to be set?
    # https://github.com/radiasoft/sirepo/issues/7093
    d = fc.sr_sim_data(a, compute_model=c)
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
        _warppba_login(new_user_fc, invalid_password=True)


def test_warppba_login(new_user_fc):
    from pykern import pkunit, pkdebug
    from pykern.pkcollections import PKDict

    d, c = _warppba_login(new_user_fc)
    new_user_fc.sr_run_sim(d, c, expect_completed=False, timeout=5)
    r = new_user_fc.sr_post(
        "sbatchLoginStatus",
        PKDict(
            computeModel=c,
            models=d.models,
            simulationId=d.models.simulation.simulationId,
            simulationType=d.simulationType,
        ),
    )
    pkunit.pkok(r.ready, "not ready response={}", r)


def test_warppba_no_creds(new_user_fc):
    from pykern.pkunit import pkexcept

    x = _warppba_login_setup(new_user_fc)
    with pkexcept("SRException.*no-creds"):
        new_user_fc.sr_run_sim(*x, expect_completed=False)


def _warppba_login(fc, invalid_password=False):
    from pykern.pkcollections import PKDict
    from pykern import pkunit, pkdebug
    from sirepo import util

    def _post_args(**kwargs):
        rv = fc.sr_sbatch_creds()
        if invalid_password:
            rv.sbatchCredentials.password = "invalid password"
        return rv.pkupdate(kwargs)

    d, c = _warppba_login_setup(fc)
    try:
        r = fc.sr_run_sim(d, c, expect_completed=False)
        pkunit.pkfail("did not raise SRException reply={}", r)
    except util.SRException as e:
        p = e.sr_args.params
    fc.sr_post(
        "sbatchLogin",
        _post_args(
            computeModel=p.computeModel,
            simulationId=p.simulationId,
            simulationType=d.simulationType,
        ),
    )
    return d, c


def _warppba_login_setup(fc):
    return fc.sr_sim_data("Laser Pulse", compute_model="animation"), "animation"
