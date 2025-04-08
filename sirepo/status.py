"""Sirepo web server status for remote monitoring

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkconfig
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp, pkdformat
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
            }
        )

    async def _run_tests(self):
        """Runs the SRW "Undulator Radiation" simulation's initialIntensityReport"""
        await self._validate_auth_state()
        simulation_type = _cfg.sim_type
        res = await self.call_api(
            "findByNameWithAuth",
            kwargs=PKDict(
                simulation_type=simulation_type,
                application_mode="default",
                simulation_name=_cfg.sim_name,
            ),
        )
        try:
            c = res.content_as_redirect()
        finally:
            res.destroy()
        m = re.search(r"/source/(\w+)$", c.uri)
        if not m:
            raise RuntimeError(f"failed to find sid in resp={c}")
        i = m.group(1)
        d = simulation_db.read_simulation_json(simulation_type, sid=i, qcall=self)
        try:
            d.models.electronBeam.current += random.random() / 10
        except AttributeError:
            assert (
                _cfg.sim_type == "myapp"
            ), f"{_cfg.sim_type} should be myapp or have models.electronBeam.current"
        d.simulationId = i
        d.report = _cfg.sim_report
        await self._run_sim(d)

    async def _run_sim(self, body):
        def _completed(reply):
            pkdlog("status=completed sid={}", body.simulationId)
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

        async def _first(body):
            rv = await self.call_api("runStatus", body=body)
            try:
                s = rv.content_as_object().state
            except:
                rv.destroy()
            if s not in sirepo.job.ACTIVE_STATUSES:
                rv.destroy()
                rv = await self.call_api("runSimulation", body=body)
            return rv

        def _next(reply, body):
            if reply.state == sirepo.job.ERROR:
                raise RuntimeError(f"state=error sid={body.simulationId} reply={reply}")
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
            r = await _first(body)
            for _ in range(_cfg.max_calls):
                if (body := _next(r.content_as_object(), body)) is None:
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
    pass


_cfg = pkconfig.init(
    max_calls=(30, int, "1 second calls"),
    # only used for srunit
    sim_name=("Undulator Radiation", str, "which sim"),
    sim_report=("initialIntensityReport", str, "which report"),
    sim_type=("srw", str, "which app to test"),
)
