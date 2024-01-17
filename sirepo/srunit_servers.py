"""start servers for unit tests

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import contextlib

# limit sirepo/pykern global imports


@contextlib.contextmanager
def api_and_supervisor(pytest_req, fc_args):
    from pykern import pkunit, pkjson
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog, pkdp
    from sirepo import srunit
    import time, requests, subprocess

    fc_args.pksetdefault(
        cfg=PKDict,
        sim_types=None,
        append_package=None,
        empty_work_dir=True,
    )

    def _config_sbatch_supervisor_env(env):
        from pykern.pkcollections import PKDict
        import os
        import pykern.pkio
        import pykern.pkunit
        import re
        import socket

        h = socket.gethostname()
        k = pykern.pkio.py_path("~/.ssh/known_hosts").read()
        m = re.search("^{}.*$".format(h), k, re.MULTILINE)
        assert bool(m), "You need to ssh into {} to get the host key".format(h)

        env.pkupdate(
            SIREPO_JOB_DRIVER_MODULES="local:sbatch",
            SIREPO_JOB_DRIVER_SBATCH_CORES=os.getenv(
                "SIREPO_JOB_DRIVER_SBATCH_CORES",
                "2",
            ),
            SIREPO_JOB_DRIVER_SBATCH_HOST=h,
            SIREPO_JOB_DRIVER_SBATCH_HOST_KEY=m.group(0),
            SIREPO_JOB_DRIVER_SBATCH_SIREPO_CMD="sirepo",
            SIREPO_JOB_DRIVER_SBATCH_SRDB_ROOT=str(
                pykern.pkunit.work_dir().join("/{sbatch_user}/sirepo")
            ),
            SIREPO_JOB_SUPERVISOR_SBATCH_POLL_SECS="2",
        )

    def _ping_supervisor(uri):

        l = None
        for _ in range(100):
            try:
                r = requests.post(uri, json=None)
                r.raise_for_status()
                d = pkjson.load_any(r.text)
                if d.state == "ok":
                    return
                raise RuntimeError(f"state={r.get('state')}")
            except Exception as e:
                l = e
                time.sleep(0.3)
        pkunit.restart_or_fail("start failed uri={} exception={}", uri, l)

    def _port():
        from pykern import pkunit
        from sirepo import const

        return str(
            pkunit.unbound_localhost_tcp_port(
                const.TEST_PORT_RANGE.start, const.TEST_PORT_RANGE.stop
            ),
        )

    def _subprocess(cmd):
        p.append(subprocess.Popen(cmd, env=env, cwd=wd))

    def _subprocess_setup(pytest_req, fc_args):
        """setup the supervisor"""
        import os
        from pykern.pkcollections import PKDict

        sbatch_module = "sbatch" in pytest_req.module.__name__
        env = PKDict(os.environ)
        cfg = fc_args.cfg
        from pykern import pkunit, pkio

        p = _port()
        cfg.pkupdate(
            PYKERN_PKDEBUG_WANT_PID_TIME="1",
            SIREPO_PKCLI_JOB_SUPERVISOR_IP=pkunit.LOCALHOST_IP,
            SIREPO_PKCLI_JOB_SUPERVISOR_PORT=p,
            SIREPO_PKCLI_SERVICE_IP=pkunit.LOCALHOST_IP,
            SIREPO_SRDB_ROOT=str(pkio.mkdir_parent(pkunit.work_dir().join("db"))),
        )
        cfg.SIREPO_PKCLI_SERVICE_PORT = _port()
        for x in "DRIVER_LOCAL", "DRIVER_DOCKER", "API", "DRIVER_SBATCH":
            cfg[f"SIREPO_JOB_{x}_SUPERVISOR_URI"] = f"http://{pkunit.LOCALHOST_IP}:{p}"
        if sbatch_module:
            cfg.pkupdate(SIREPO_SIMULATION_DB_SBATCH_DISPLAY="testing@123")
        env.pkupdate(**cfg)

        from sirepo import srunit

        c = None
        u = [env.SIREPO_PKCLI_JOB_SUPERVISOR_PORT]
        c = srunit.http_client(
            env=env,
            empty_work_dir=fc_args.empty_work_dir,
            job_run_mode="sbatch" if sbatch_module else None,
            sim_types=fc_args.sim_types,
            port=env.SIREPO_PKCLI_SERVICE_PORT,
        )
        u.append(c.port)
        t = fc_args.sim_types
        if isinstance(t, (tuple, list)):
            t = ":".join(t)
        cfg.SIREPO_FEATURE_CONFIG_SIM_TYPES = t
        for i in u:
            subprocess.run(
                ["kill -9 $(lsof -t -i :" + i + ") >& /dev/null"], shell=True
            )
        if sbatch_module:
            # must be performed after fc initialized so work_dir is configured
            _config_sbatch_supervisor_env(env)
        return (env, c)

    env, c = _subprocess_setup(pytest_req, fc_args)
    wd = pkunit.work_dir()
    p = []
    try:
        for k in sorted(env.keys()):
            if k.endswith("_PORT"):
                pkdlog("{}={}", k, env[k])
        _subprocess(("sirepo", "service", "server"))
        # allow db to be created
        time.sleep(0.5)
        _subprocess(("sirepo", "job_supervisor"))
        _ping_supervisor(c.http_prefix + "/job-supervisor-ping")
        from sirepo import template
        from pykern import pkio

        if template.is_sim_type("srw"):
            pkio.unchecked_remove(
                "~/src/radiasoft/sirepo/sirepo/package_data/template/srw/predefined.json"
            )
            template.import_module("srw").get_predefined_beams()
        yield c
    finally:
        import sys

        for x in p:
            x.terminate()
            x.wait()
