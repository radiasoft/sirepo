"""cron can run before and after startup

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


@pytest.mark.asyncio(loop_scope="module")
def test_complex():
    import asyncio
    from pykern.pkcollections import PKDict
    from pykern import pkconfig, pkunit, pkconst, pkio, util

    async def _post_start(params):
        params.post_calls += 1

    async def _pre_start(params):
        from sirepo import srtime, cron

        params.pre_calls += 1
        if params.pre_calls == 1:
            # Will only get one call, because sleep will be for 60 real seconds
            cron.CronTask(60, _post_start, params)
        srtime.adjust_time(days=1)
        if params.pre_calls >= 3:
            asyncio.get_running_loop().stop()

    p = str(util.unbound_localhost_tcp_port(10000, 30000))
    pkconfig.reset_state_for_testing(
        PKDict(
            SIREPO_PKCLI_SERVICE_IP=pkconst.LOCALHOST_IP,
            SIREPO_PKCLI_SERVICE_PORT=p,
            SIREPO_PKCLI_SERVICE_TORNADO_PRIMARY_PORT=p,
            SIREPO_SRDB_ROOT=str(pkio.mkdir_parent(pkunit.work_dir().join("db"))),
        )
    )

    from sirepo import cron
    from sirepo.pkcli import service

    p = PKDict(pre_calls=0, post_calls=0)
    cron.CronTask(24 * 60 * 60, _pre_start, p)
    service.server()
    pkunit.pkeq(3, p.pre_calls, "pre_calls")
    pkunit.pkeq(1, p.post_calls, "post_calls")
