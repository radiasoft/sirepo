"""Sirepo web server status for remote monitoring

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkconfig
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdformat, pkdpretty
from sirepo import simulation_db
import asyncio
import datetime
import random
import re
import sirepo.job
import sirepo.quest
import time


_SLEEP = 1


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_auth_basic")
    async def api_serverStatus(self):
        """Allow for remote monitoring of the web server status.

        The user must be an existing sirepo uid.  The status checks
        that a simple simulation can complete successfully within a
        short period of time.
        """
        await self._run_tests()
        return self.reply_ok(
            {
                "datetime": datetime.datetime.utcnow().isoformat(),
                "sentinel": _cfg.reply_sentinel,
            }
        )

    async def _run_tests(self):
        """Runs the SRW "Undulator Radiation" simulation's initialIntensityReport"""
        await self._validate_auth_state()
        simulation_type = _cfg.sim_type
        res = await self.call_api(
            "listSimulations",
            body=PKDict(
                simulationType=simulation_type,
                search=PKDict({"simulation.name": _cfg.sim_name}),
            ),
        )
        try:
            c = res.content_as_object()
        finally:
            res.destroy()
        if len(c) != 1:
            raise AssertionError(
                f"listSimulations name={sim_name} returned count={len(c)}"
            )
        d = simulation_db.read_simulation_json(
            simulation_type, sid=c[0].simulation.simulationId, qcall=self
        )
        d.report = _cfg.sim_report
        await self._run_sim(d, d.models.simulation.simulationId)

    async def _run_sim(self, body, sim_id):
        def _completed(reply):
            pkdlog("status=completed sid={}", sim_id)
            if "initialIntensityReport" != body.report:
                return
            m = 50
            if len(reply.z_matrix) < m:
                raise RuntimeError(
                    f"len(reply.z_matrix)={len(reply.z_matrix)} < {m} reply={reply}",
                )
            if len(reply.z_matrix[0]) < m:
                raise RuntimeError(
                    f"len(reply.z_matrix[0])={len(reply.z_matrix[0])} < {m} reply={reply}",
                )

        async def _first():
            rv = await self.call_api("runStatus", body=body)
            try:
                s = rv.content_as_object().state
            except:
                rv.destroy()
            if s in sirepo.job.ACTIVE_STATUSES:
                pkdlog("already running simulation={}", sim_id)
            else:
                rv.destroy()
                rv = await self.call_api("runSimulation", body=body)
            return rv

        def _next(reply):
            if reply.state == sirepo.job.ERROR:
                raise RuntimeError(f"state=error sid={sim_id} reply={reply}")
            if reply.state == sirepo.job.COMPLETED:
                _completed(reply)
                return None
            if (rv := reply.get("nextRequest")) is None:
                raise RuntimeError(
                    f"nextRequest missing state={reply.get('state')} reply={reply}"
                )
            return rv

        r = None
        try:
            async with sirepo.file_lock.AsyncFileLock(
                simulation_db.sim_data_file(body.simulationType, sim_id, qcall=self),
                qcall=self,
            ):
                r = await _first()
            for _ in range(_cfg.max_calls):
                if (body := _next(r.content_as_object())) is None:
                    return
                r.destroy()
                r = await self.call_api("runStatus", body=body)
                await asyncio.sleep(_SLEEP)
            raise RuntimeError(f"timeout={_cfg.max_calls * _SLEEP}s last resp={r}")
        finally:
            if r:
                r.destroy()
            try:
                if body is not None:
                    await self.call_api("runCancel", body=body)
            except Exception:
                pass

    async def _validate_auth_state(self):
        r = (await self.call_api("authState")).content_as_str()
        m = re.search(r"SIREPO.authState\s*=\s*(.*?);", r)
        assert m, pkdformat("no authState in response={}", r)
        assert pkjson.load_any(m.group(1)).isLoggedIn, pkdformat(
            "expecting isLoggedIn={}", m.group(1)
        )


def init_apis(*args, **kwargs):
    global _cfg

    _cfg = pkconfig.init(
        max_calls=(30, int, "1 second calls"),
        reply_sentinel=("any-string", str, "unique string for reply"),
        # only configured for srunit
        sim_name=("Undulator Radiation", str, "which sim"),
        sim_report=("initialIntensityReport", str, "which report"),
        sim_type=("srw", str, "which app to test"),
    )
