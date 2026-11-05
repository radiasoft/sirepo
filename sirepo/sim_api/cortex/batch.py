"""Run cortex sims for many materials as the batch user

The sims are run one at a time by the user configured with
`sirepo.feature_config` ``cortex.batch_uid``, so a user's own sims and
their quota are not affected. The results are imported for the material's owner.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import asyncio
import contextlib
import sirepo.auth
import sirepo.feature_config
import sirepo.quest
import sirepo.sim_api.cortex
import sirepo.sim_api.cortex.material_db
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.template.cortex
import sirepo.util

_SIM_DATA, SIM_TYPE, _ = sirepo.sim_data.template_globals(sim_type="cortex")

_POLL_SECS = 10

#: states of a job in `_Batch`
_CANCELED = "canceled"
_ERROR = "error"
_QUEUED = "queued"
_RUNNING = "running"
_COMPLETED = "completed"

#: states of a run which are not going to change
_RUN_DONE = frozenset(("canceled", "completed", "error", "missing"))

_batch = None


async def op(op_name, op_args):
    """Run an operation of the batch api

    Args:
        op_name (str): one of cancel, list_materials, run, status
        op_args (PKDict): arguments of the operation
    Returns:
        PKDict: reply
    """
    if op_name not in ("cancel", "list_materials", "run", "status"):
        raise AssertionError(f"invalid op_name={op_name}")
    return await globals()[f"_op_{op_name}"](op_args)


def _auth_method():
    # The batch user logs in with email, but dev servers may only allow guests
    return (
        sirepo.auth.METHOD_EMAIL
        if sirepo.auth.METHOD_EMAIL in sirepo.auth.valid_methods
        else sirepo.auth.METHOD_GUEST
    )


def _batch_uid():
    rv = sirepo.feature_config.cfg().cortex.batch_uid
    if not rv:
        raise sirepo.util.UserAlert(
            "The batch user is not configured", "cortex.batch_uid is not set"
        )
    return rv


def _material_ids(op_args):
    rv = [int(m) for m in op_args.material_ids]
    if not rv:
        raise sirepo.util.UserAlert("No materials selected", "no material_ids")
    return rv


async def _op_cancel(op_args):
    if _batch and _batch.is_running():
        _batch.is_canceled = True
    return _status()


async def _op_list_materials(op_args):
    return PKDict(rows=sirepo.sim_api.cortex.material_db.all_materials())


async def _op_run(op_args):
    global _batch

    if _batch and _batch.is_running():
        raise sirepo.util.UserAlert("A batch is already running", "batch is running")
    _batch = _Batch(
        _batch_uid(),
        [
            PKDict(material_id=m, report=r, state=_QUEUED, error=None)
            for m in _material_ids(op_args)
            for r in _reports(op_args)
        ],
    )
    _batch.start()
    return _status()


async def _op_status(op_args):
    return _status()


def _reports(op_args):
    rv = op_args.get("reports") or sorted(sirepo.template.cortex.SIM_VERSION)
    for r in rv:
        if r not in sirepo.template.cortex.SIM_VERSION:
            raise AssertionError(f"invalid report={r}")
    return rv


def _status():
    if not _batch:
        return PKDict(is_running=False, jobs=[])
    return PKDict(is_running=_batch.is_running(), jobs=_batch.jobs)


class _Batch:
    """Runs jobs, one at a time, in a task on the server's event loop"""

    def __init__(self, batch_uid, jobs):
        self.batch_uid = batch_uid
        self.is_canceled = False
        self.jobs = jobs
        self._task = None

    def is_running(self):
        return self._task is not None and not self._task.done()

    def start(self):
        self._task = asyncio.ensure_future(self._run())

    async def _run(self):
        for j in self.jobs:
            if self.is_canceled:
                j.state = _CANCELED
                continue
            j.state = _RUNNING
            try:
                await self._run_job(j)
            except Exception as e:
                pkdlog("job={} error={} stack={}", j, e, pkdexc())
                j.pkupdate(state=_ERROR, error=str(e))

    async def _run_job(self, job):
        """Run a report and import its results for the owner of the material"""

        owner = sirepo.sim_api.cortex.material_db.material_owner(job.material_id)
        with self._qcall() as q:
            s = await sirepo.sim_api.cortex.get_sim_data(
                q, job.material_id, create=True
            )
            # The sim is the batch user's, but the material is the owner's
            sirepo.sim_api.cortex.update_sim_from_material_detail(
                s,
                job.material_id,
                sirepo.sim_api.cortex.material_db.format_material_detail(
                    job.material_id, False, owner
                ),
            )
            s = sirepo.simulation_db.save_simulation_json(s, fixup=True, qcall=q)
            b = PKDict(
                report=job.report,
                models=s.models,
                simulationType=SIM_TYPE,
                simulationId=s.models.simulation.simulationId,
            )
            await q.call_api("runSimulation", body=b.copy().pkupdate(forceRun=True))
        while True:
            await asyncio.sleep(_POLL_SECS)
            if self.is_canceled:
                with self._qcall() as q:
                    await q.call_api("runCancel", body=b)
                job.state = _CANCELED
                return
            with self._qcall() as q:
                r = (await q.call_api("runStatus", body=b)).content_as_object()
            if r.state in _RUN_DONE:
                break
        if r.state != _COMPLETED:
            job.pkupdate(state=_ERROR, error=f"run state={r.state}")
            return
        with self._qcall() as q:
            # one summary is imported per call, until all are imported
            while await asyncio.to_thread(
                sirepo.sim_api.cortex.check_for_sim_summary, q, owner
            ):
                pass
        job.state = _COMPLETED

    @contextlib.contextmanager
    def _qcall(self):
        with sirepo.quest.start(in_pkcli=True) as q:
            with q.auth.logged_in_user_set(self.batch_uid, method=_auth_method()):
                yield q
