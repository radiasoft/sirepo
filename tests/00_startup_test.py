"""run services in test process to verify they start

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_api_server():
    import os

    assert (
        0
    ), f"GITHUB_TOKEN={os.getenv('GITHUB_TOKEN')} SIREPO_FEATURE_CONFIG_PROPRIETARY_OAUTH_SIM_TYPES={os.getenv('SIREPO_FEATURE_CONFIG_PROPRIETARY_OAUTH_SIM_TYPES') }"

    _setup("SIREPO_PKCLI_SERVICE")

    from sirepo.pkcli import service

    service.server()


def test_job_supervisor():
    _setup("SIREPO_PKCLI_JOB_SUPERVISOR")

    from sirepo.pkcli import job_supervisor

    job_supervisor.default_command()


def test_quest_start():
    from sirepo import srunit

    with srunit.quest_start() as qcall:
        qcall.call_api_sync("authState")


def _setup(prefix):
    from pykern import pkunit, pkconfig, pkdebug, pkio
    import tornado

    pkconfig.reset_state_for_testing(
        {
            prefix + "_IP": pkunit.LOCALHOST_IP,
            prefix + "_PORT": str(pkunit.unbound_localhost_tcp_port(30000, 31000)),
            "SIREPO_SRDB_ROOT": str(pkio.mkdir_parent(pkunit.work_dir().join("db"))),
        }
    )
    i = tornado.ioloop.IOLoop.current()
    i.add_callback(i.stop)
