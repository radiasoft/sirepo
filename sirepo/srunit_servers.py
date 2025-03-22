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
    import os, requests, subprocess, time

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

        h = "localhost"
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
        from requests.exceptions import ConnectionError

        for _ in range(
            int(os.environ.get("SIREPO_SRUNIT_SERVERS_PING_TIMEOUT", 20)) * 10
        ):
            d = None
            s = None
            try:
                r = requests.post(uri, json=None, allow_redirects=False)
            except ConnectionError as e:
                s = 0
            else:
                if (s := r.status_code) != 200:
                    break
                d = pkjson.load_any(r.text)
                if d.get("state") == "ok":
                    return
                if "unable to connect" not in d.get("error", ""):
                    break
            time.sleep(0.1)
        pkunit.restart_or_fail("uri={} status={} reply={}", uri, s, d)

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
            SIREPO_PKCLI_JOB_SUPERVISOR_USE_RELOADER="0",
            SIREPO_PKCLI_SERVICE_IP=pkunit.LOCALHOST_IP,
            SIREPO_PKCLI_SERVICE_USE_RELOADER="0",
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
        cfg.SIREPO_FEATURE_CONFIG_SIM_TYPES = _sim_types(fc_args)
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
        yield c
    finally:
        import sys

        for x in p:
            try:
                x.terminate()
                x.wait(timeout=4)
            except subprocess.TimeoutExpired:
                x.kill()
                x.wait(timeout=2)


@contextlib.contextmanager
def sim_db_file(pytest_req):
    from pykern import pkunit, pkio, pkdebug, pkconfig
    from pykern.pkcollections import PKDict
    import os, signal, time

    port = _port()
    # must match job.unique.key
    token = "a" * 32
    # must be valid uid
    uid = "simdbfil"
    # test won't pass if this is different from job.SIM_DB_FILE_URI
    uri = "/sim-db-file"

    def _server():
        from pykern import pkasyncio, pkunit
        from pykern.pkcollections import PKDict
        from tornado import websocket
        from sirepo import job, sim_db_file

        def _token_for_user(*args, **kwargs):
            return token

        _sim_dir()
        setattr(sim_db_file.SimDbServer, "token_for_user", token)
        setattr(sim_db_file.SimDbServer, "_TOKEN_TO_UID", PKDict({token: uid}))
        l = pkasyncio.Loop()
        l.http_server(
            PKDict(
                uri_map=((job.SIM_DB_FILE_URI + "/(.+)", sim_db_file.SimDbServer),),
                tcp_port=port,
                tcp_ip=pkunit.LOCALHOST_IP,
            )
        )
        l.start()

    def _setup(pytest_req):
        """setup the supervisor"""
        import os

        c = PKDict(
            PYKERN_PKDEBUG_WANT_PID_TIME="1",
            SIREPO_AUTH_LOGGED_IN_USER=uid,
            SIREPO_SIMULATION_DB_LOGGED_IN_USER=uid,
            SIREPO_SIM_DB_FILE_SERVER_TOKEN=token,
            SIREPO_SIM_DB_FILE_SERVER_URI=f"http://{pkunit.LOCALHOST_IP}:{port}{uri}/{uid}/",
            SIREPO_SRDB_ROOT=str(pkio.mkdir_parent(pkunit.work_dir().join("db"))),
        )
        os.environ.update(**c)
        pkconfig.reset_state_for_testing(c)

    def _sim_dir():
        from sirepo import simulation_db, quest, srunit

        stype = srunit.SR_SIM_TYPE_DEFAULT
        simulation_db.user_path_root().join(simulation_db._uid_arg()).ensure(dir=1)
        with quest.start(in_pkcli=True) as qcall:
            # create examples
            simulation_db.simulation_dir(stype, qcall=qcall)
        pkio.write_text(
            simulation_db.simulation_lib_dir(stype).join("hello.txt"),
            "xyzzy",
        )

    _setup(pytest_req)
    p = os.fork()
    if p == 0:
        try:
            pkdebug.pkdlog("start server")
            _server()
        except Exception as e:
            pkdebug.pkdlog("server exception={} stack={}", e, pkdebug.pkdexc())
        finally:
            os._exit(0)
    try:
        time.sleep(1)
        yield None

    finally:
        os.kill(p, signal.SIGKILL)


def _port():
    from pykern import pkunit
    from sirepo import const

    return str(
        pkunit.unbound_localhost_tcp_port(
            const.TEST_PORT_RANGE.start, const.TEST_PORT_RANGE.stop
        ),
    )


def _sim_types(fc_args):
    t = fc_args.sim_types
    if isinstance(t, (tuple, list)):
        return ":".join(t)
    return t
