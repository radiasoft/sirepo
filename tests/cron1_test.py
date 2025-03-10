"""cron task can run and be destroyed

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


@pytest.mark.asyncio(loop_scope="module")
def test_basic():
    import asyncio
    from pykern.pkcollections import PKDict
    from pykern import pkconfig, pkunit, pkconst, pkio, util, pkdebug

    async def _pre_start(params):
        from sirepo import srtime

        params.calls += 1
        if params.calls == 1:
            asyncio.create_task(_stop(params))
        srtime.adjust_time(days=1)

    async def _stop(params):
        try:
            p = params.calls
            params.stop_ok = False
            for i in range(10):
                await asyncio.sleep(0)
                if p == params.calls:
                    # Should always increment
                    break
                p == params.calls
                if params.calls >= 3:
                    params.cron_task.destroy()
                    params.stop_ok = True
        except Exception as e:
            pkdebug.pkdlog("{} error {}", e, pkdebug.pkdexc())
            params.stop_ok = False
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

    p = PKDict(calls=0)
    p.cron_task = cron.CronTask(24 * 60 * 60, _pre_start, p)
    service.server()
    pkunit.pkeq(3, p.calls)
    pkunit.pkok(p.stop_ok, "stop failed")
