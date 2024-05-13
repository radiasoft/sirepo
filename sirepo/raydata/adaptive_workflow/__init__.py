"""Interaction with RunEngine and QServer adaptive workflows.

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
import asyncio
import bluesky_queueserver_api.zmq.aio
import importlib

_ADAPTIVE_WORKFLOW_HANDLERS = PKDict()
_cfg = None


class Base(PKDict):
    pass


class _QSserverClient:
    _WAIT_TIMEOUT_SECS = 30

    def __init__(self):
        self._client = bluesky_queueserver_api.zmq.aio.REManagerAPI()
        self._lock = asyncio.Lock()

    async def stop_current_plan(self):
        """Immediately stop the currently executing plan.

        The plan will finish with a "success" completed state.
        """

        def _idle_condition(status):
            return status["manager_state"] == "idle"

        async with self._lock:
            try:
                if (await self._client.status())["manager_state"] != "executing_queue":
                    # Reduce log noise. Only try to stop if currently running.
                    return
                # TODO(e-carlin): It is possible for `re_pause` to
                # raise an error if the queue is transitioning between
                # runs. This would result in the queue not being
                # stopped.
                await self._client.re_pause(option="immediate")
                await self._client.wait_for_idle_or_paused(
                    timeout=self._WAIT_TIMEOUT_SECS
                )
                await self._client.re_stop()
                await self._client.wait_for_condition(
                    condition=_idle_condition, timeout=self._WAIT_TIMEOUT_SECS
                )
            except Exception as e:
                pkdlog("error={} stack={}", e, pkdexc())


async def run_engine_event_callback(req_data):
    def _init():
        global _ADAPTIVE_WORKFLOW_HANDLERS, _cfg
        if _cfg:
            return
        _cfg = pkconfig.init(
            catalog_names=(
                frozenset(),
                set,
                "list of catalog names (beamlines) that support adaptive workflows",
            ),
        )
        q = _QSserverClient()
        for n in _cfg.catalog_names:
            _ADAPTIVE_WORKFLOW_HANDLERS[n] = getattr(
                importlib.import_module(f"sirepo.raydata.adaptive_workflow.{n}"),
                n.upper(),
            )(_qserver_client=q)

    # Need to initialize lazily. Both asyncio.locks.Lock and
    # bluesky_queueserver_api.zmq.aio.REManagerAPI get the running
    # event loop which needs to be that of the running server.
    _init()
    await getattr(
        _ADAPTIVE_WORKFLOW_HANDLERS[req_data.catalogName],
        f"run_engine_event_callback_{req_data.method}",
    )(req_data.documentData)
