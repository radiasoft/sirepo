# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import job
import asyncio
import contextlib
import os
import pykern.pkio
import sirepo.http_reply
import sirepo.simulation_db
import sirepo.srdb
import sirepo.util
import time
import tornado.ioloop
import tornado.locks
import tornado.queues


#: where supervisor state is persisted to disk
_DB_DIR = None

#: where job db is stored under srdb.root
_DB_SUBDIR = 'supervisor-job'

_NEXT_REQUEST_SECONDS = None

_RUNNING_PENDING = (job.RUNNING, job.PENDING)

_HISTORY_FIELDS = frozenset((
    'computeJobSerial',
    'computeJobStart',
    'error',
    'jobRunMode',
    'lastUpdateTime',
    'status',
))

_PARALLEL_STATUS_FIELDS = frozenset((
    'computeJobHash',
    'elapsedTime',
    'frameCount',
    'lastUpdateTime',
    'percentComplete',
    'computeJobStart',
))

_UNTIMED_OPS = frozenset((job.OP_ALIVE, job.OP_CANCEL, job.OP_ERROR, job.OP_KILL, job.OP_OK))
cfg = None

#: conversion of cfg.<kind>.max_hours
_MAX_RUN_SECS = PKDict()

#: how many times restart request when Awaited() raised
_MAX_RETRIES = 100


class Awaited(Exception):
    """An await occurred, restart operation"""
    pass


def init():
    global _DB_DIR, cfg, _NEXT_REQUEST_SECONDS, job_driver
    if _DB_DIR:
        return
    job.init()
    from sirepo import job_driver

    job_driver.init(pkinspect.this_module())
    _DB_DIR = sirepo.srdb.root().join(_DB_SUBDIR)
    cfg = pkconfig.init(
        parallel=dict(
            max_hours=(1, float, 'maximum run-time for parallel job (except sbatch)'),
        ),
        sbatch_poll_secs=(60, int, 'how often to poll squeue and parallel status'),
        sequential=dict(
            max_hours=(.1, float, 'maximum run-time for sequential job'),
        ),
    )
    for k in job.KINDS:
        _MAX_RUN_SECS[k] = int(cfg[k].max_hours * 3600)
    _NEXT_REQUEST_SECONDS = PKDict({
        job.PARALLEL: 2,
        job.SBATCH: cfg.sbatch_poll_secs,
        job.SEQUENTIAL: 1,
    })
    if sirepo.simulation_db.user_dir_name().exists():
        if not _DB_DIR.exists():
            pkdlog('calling upgrade_runner_to_job_db path={}', _DB_DIR)
            import subprocess
            subprocess.check_call(
                (
                    'pyenv',
                    'exec',
                    'sirepo',
                    'db',
                    'upgrade_runner_to_job_db',
                    _DB_DIR,
                ),
                env=PKDict(os.environ).pkupdate(
                    PYENV_VERSION='py2',
                    SIREPO_AUTH_LOGGED_IN_USER='unused',
                ),
            )
    else:
        pykern.pkio.mkdir_parent(_DB_DIR)


class ServerReq(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task = asyncio.current_task()

    async def receive(self):
        s = self.content.pkdel('serverSecret')
        # no longer contains secret so ok to log
        assert s, \
            'no secret in message: {}'.format(self.content)
        assert s == sirepo.job.cfg.server_secret, \
            'server_secret did not match'.format(self.content)
        self.handler.write(await _ComputeJob.receive(self))

    def __str__(self):
        c = self.get('content')
        if not c:
            return 'ServerReq(<no content>)'
        return f'ServerReq({c.api}, {c.computeJid})'


async def terminate():
    from sirepo import job_driver

    await job_driver.terminate()


class _ComputeJob(PKDict):

    instances = PKDict()

    def __init__(self, req, **kwargs):
        super().__init__(
            ops=[],
            run_op=None,
            run_dir_mutex=tornado.locks.Event(),
            **kwargs,
        )
        # At start we don't know anything about the run_dir so assume ready
        self.run_dir_mutex.set()
        self.run_dir_owner = None
        self.pksetdefault(db=lambda: self.__db_init(req))

    def destroy_op(self, op):
        if op in self.ops:
            self.ops.remove(op)
        if self.run_op == op:
            self.run_op = None
        if op == self.run_dir_owner:
            self.run_dir_release(self.run_dir_owner)

    @classmethod
    def get_instance(cls, req):
        j = req.content.computeJid
        self = cls.instances.pksetdefault(j, lambda: cls.__create(req))[j]
        # SECURITY: must only return instances for authorized user
        assert req.content.uid == self.db.uid, \
            'req.content.uid={} is not same as db.uid={} for jid={}'.format(
                req.content.uid,
                self.db.uid,
                j,
            )
        return self

    @classmethod
    async def receive(cls, req):
        pkdlog('{}', req)
        try:
            for i in range(_MAX_RETRIES):
                try:
                    return await getattr(
                        cls.get_instance(req),
                        '_receive_' + req.content.api,
                    )(req)
                except Awaited:
                    pass
                except asyncio.CancelledError:
                    return PKDict(state=job.CANCELED)
            raise AssertionError('too many retries {}'.format(req))
        except Exception as e:
            pkdlog('{} error={} stack={}', req, e, pkdexc())
            if isinstance(e, sirepo.util.Reply):
                return sirepo.http_reply.gen_tornado_exception(e)
            raise

    async def run_dir_acquire(self, owner):
        if self.run_dir_owner == owner:
            return
        e = None
        if not self.run_dir_mutex.is_set():
            await self.run_dir_mutex.wait()
            e = Awaited()
            if self.run_dir_owner:
                # some other op acquired it before this one
                raise e
        self.run_dir_mutex.clear()
        self.run_dir_owner = owner
        if e:
            raise e

    def run_dir_release(self, owner):
        assert owner == self.run_dir_owner, \
            'owner={} not same as releaser={}'.format(self.run_dir_owner, owner)
        self.run_dir_owner = None
        self.run_dir_mutex.set()

    @classmethod
    def __create(cls, req):
        try:
            d = pkcollections.json_load_any(
                cls.__db_file(req.content.computeJid),
            )
#TODO(robnagler) when we reconnet with running processes at startup,
#  we'll need to change this
            if d.status in _RUNNING_PENDING:
                d.status = job.CANCELED
            return cls(req, db=d)
        except Exception as e:
            if pykern.pkio.exception_is_not_found(e):
                return cls(req).__db_write()
            raise

    @classmethod
    def __db_file(cls, computeJid):
        return _DB_DIR.join(computeJid + '.json')

    def __db_init(self, req, prev_db=None):
        c = req.content
        self.db = PKDict(
            computeJid=c.computeJid,
            computeJobHash=c.computeJobHash,
            computeJobSerial=0,
            computeJobStart=0,
            error=None,
            history=self.__db_init_history(prev_db),
            isParallel=c.isParallel,
            jobRunMode=c.jobRunMode,
            lastUpdateTime=0,
            nextRequestSeconds=_NEXT_REQUEST_SECONDS[c.jobRunMode],
            simulationId=c.simulationId,
            simulationType=c.simulationType,
#TODO(robnagler) when would req come in with status?
            status=req.get('status', job.MISSING),
            uid=c.uid,
        )
        if self.db.isParallel:
            self.db.parallelStatus = PKDict(
                ((k, 0) for k in _PARALLEL_STATUS_FIELDS),
            )
        return self.db

    def __db_init_history(self, prev_db):
        if prev_db is None:
            return []
        return prev_db.history + [
            PKDict(((k, v) for k, v in prev_db.items() if k in _HISTORY_FIELDS)),
        ]

    def __db_write(self):
        sirepo.util.json_dump(self.db, path=self.__db_file(self.db.computeJid))
        return self

    async def _receive_api_downloadDataFile(self, req):
        return await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobCmd='get_data_file',
            dataFileKey=req.content.pop('dataFileKey')
        )

    async def _receive_api_runCancel(self, req):
        r = PKDict(state=job.CANCELED)
        if (
            not self._req_is_valid(req)
            or self.db.status not in _RUNNING_PENDING
        ):
            # job is not relevant, but let the user know it isn't running
            return r
        c = None
        try:
            if self.run_op:
#TODO(robnagler) cancel run_op, not just by jid, which is insufficient (hash)
                c = self._create_op(job.OP_CANCEL, req)
                await c.prepare_send()
                # out of order from OP_ANALYSIS and OP_RUN, because we
                # want don't have to wait so block on prepare_send before
                # modifying global state (release)
                if self.run_dir_owner:
                    self.run_dir_release(self.run_dir_owner)
                await self.run_dir_acquire(c)
            for x in self.ops:
                if not (self.db.isParallel and x.opName == job.OP_ANALYSIS):
                    x.destroy(cancel=True)
            self.db.status = job.CANCELED
            self.__db_write()
            if c:
                c.send()
                await c.reply_get()
        finally:
            if c:
                c.destroy(cancel=False)
        return r

    async def _receive_api_runSimulation(self, req):
        f = req.content.data.get('forceRun')
        if self.db.status == _RUNNING_PENDING:
            if f or not self._req_is_valid(req):
                return PKDict(
                    state=job.ERROR,
                    error='another browser is running the simulation',
                )
            return PKDict(state=self.db.status)
        if (
            not f
            and self._req_is_valid(req)
            and self.db.status == job.COMPLETED
        ):
            # Valid, completed, transient simulation
            # Read this first https://github.com/radiasoft/sirepo/issues/2007
            return await self._receive_api_runStatus(req)
        # Forced or canceled/errored/missing/invalid so run
        o = self._create_op(
            job.OP_RUN,
            req,
            jobCmd='compute',
            nextRequestSeconds=self.db.nextRequestSeconds,
        )
        try:
            await self.run_dir_acquire(o)
            await o.prepare_send()
            self.run_op = o
            self.__db_init(req, prev_db=self.db)
            self.db.computeJobSerial = int(time.time())
            self.db.pkupdate(status=job.PENDING)
            self.__db_write()
            o.make_lib_dir_symlink()
            o.send()
            r = self._status_reply(req)
            assert r
            o.run_callback = tornado.ioloop.IOLoop.current().call_later(
                0,
                self._run,
                o,
            )
            o = None
            return r
        finally:
            # _run destroys in the happy path (never got to _run here)
            if o:
                o.destroy(cancel=False)

    async def _receive_api_runStatus(self, req):
        r = self._status_reply(req)
        if r:
            return r
        return await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobCmd='sequential_result',
        )

    async def _receive_api_sbatchLogin(self, req):
        return await self._send_with_single_reply(job.OP_SBATCH_LOGIN, req)

    async def _receive_api_simulationFrame(self, req):
        if not self._req_is_valid(req):
            sirepo.util.raise_not_found('invalid {}', req)
        return await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobCmd='get_simulation_frame'
        )

    def _create_op(self, opName, req, **kwargs):
#TODO(robnagler) kind should be set earlier in the queuing process.
        req.kind = job.PARALLEL if self.db.isParallel and opName != job.OP_ANALYSIS \
            else job.SEQUENTIAL
        req.simulationType = self.db.simulationType
        # TODO(e-carlin): We need to be able to cancel requests waiting in this
        # state. Currently we assume that all requests get a driver and the
        # code does not block.
        o = _Op(
#TODO(robnagler) don't like the camelcase. It doesn't actually work right because
# these values are never sent directly, only msg which can be camelcase
            computeJob=self,
            kind=req.kind,
            maxRunSecs=0 if opName in _UNTIMED_OPS else _MAX_RUN_SECS[req.kind],
            msg=PKDict(req.content).pksetdefault(jobRunMode=self.db.jobRunMode),
            opName=opName,
            task=asyncio.current_task(),
        )
        o.driver = job_driver.get_instance(req, self.db.jobRunMode, o)
        if 'dataFileKey' in kwargs:
            kwargs['dataFileUri'] = job.supervisor_file_uri(
                o.driver.get_supervisor_uri(),
                job.DATA_FILE_URI,
                kwargs.pop('dataFileKey'),
            )
        o.msg.pkupdate(**kwargs)
        self.ops.append(o)
        return o

    def _req_is_valid(self, req):
        return (
            self.db.computeJobHash == req.content.computeJobHash
            and (
                not req.content.computeJobSerial or
                self.db.computeJobSerial == req.content.computeJobSerial
            )
        )

    async def _run(self, op):
        op.task = asyncio.current_task()
        op.pkdel('run_callback')
        l = True
        try:
            while True:
                try:
                    r = await op.reply_get()
#TODO(robnagler) is this ever true?
                    if op != self.run_op:
                        return
                    # run_dir is in a stable state so don't need to lock
                    if l:
                        l = False
                        self.run_dir_release(op)
                    self.db.status = r.state
                    if self.db.status == job.ERROR:
                        self.db.error = r.get('error', '<unknown error>')
                    if 'computeJobStart' in r:
                        self.db.computeJobStart = r.computeJobStart
                    if 'parallelStatus' in r:
                        self.db.parallelStatus.update(r.parallelStatus)
                        self.db.lastUpdateTime = r.parallelStatus.lastUpdateTime
                    else:
                        # sequential jobs don't send this
                        self.db.lastUpdateTime = int(time.time())
#TODO(robnagler) will need final frame count
                    self.__db_write()
                    if r.state in job.EXIT_STATUSES:
                        break
                except Awaited:
                    pass
                except asyncio.CancelledError:
                    return
        except Exception as e:
            pkdlog('error={} stack={}', e, pkdexc())
            if op == self.run_op:
                self.db.status = job.ERROR
                self.db.error = 'server error'
                self.__db_write()
        finally:
            op.destroy(cancel=False)

    async def _send_with_single_reply(self, opName, req, **kwargs):
        o = self._create_op(opName, req, **kwargs)
        try:
            if opName == job.OP_ANALYSIS:
                await self.run_dir_acquire(o)
            await o.prepare_send()
            o.send()
            return await o.reply_get()
        finally:
            o.destroy(cancel=False)

    def _status_reply(self, req):
        def res(**kwargs):
            r = PKDict(**kwargs)
            if self.db.error:
                r.error = self.db.error
            if self.db.isParallel:
                r.update(self.db.parallelStatus)
                r.computeJobHash = self.db.computeJobHash
                r.computeJobSerial = self.db.computeJobSerial
                r.elapsedTime = self.db.lastUpdateTime - self.db.computeJobStart
            if self.db.status in _RUNNING_PENDING:
                c = req.content
                r.update(
                    nextRequestSeconds=self.db.nextRequestSeconds,
                    nextRequest=PKDict(
                        computeJobHash=self.db.computeJobHash,
                        computeJobSerial=self.db.computeJobSerial,
                        computeJobStart=self.db.computeJobStart,
                        report=c.analysisModel,
                        simulationId=self.db.simulationId,
                        simulationType=self.db.simulationType,
                    ),
                )
            return r
        if self.db.computeJobHash != req.content.computeJobHash:
            return PKDict(state=job.MISSING, reason='computeJobHash-mismatch')
        if (
            req.content.computeJobSerial and
            self.db.computeJobSerial != req.content.computeJobSerial
        ):
            return PKDict(state=job.MISSING, reason='computeJobSerial-mismatch')
        if self.db.isParallel or self.db.status != job.COMPLETED:
            return res(state=self.db.status)
        return None

    def __str__(self):
        d = self.get('db')
        if not d:
            return '_ComputeJob()'
        return '_ComputeJob({} {} ops={})'.format(
            d.get('computeJid'),
            d.get('status'),
            self.ops,
        )


class _Op(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(
            do_not_send=False,
            opId=job.unique_key(),
            _reply_q=tornado.queues.Queue(),
        )
        self.msg.update(opId=self.opId, opName=self.opName)

    def destroy(self, cancel=True, error=None):
        if cancel:
            if self.task:
                self.task.cancel()
                self.task = None
        for x in 'run_callback', 'timer':
            if x in self:
                tornado.ioloop.IOLoop.current().remove_timeout(self.pkdel(x))
        if 'lib_dir_symlink' in self:
            # lib_dir_symlink is unique_key so not dangerous to remove
            pykern.pkio.unchecked_remove(self.pkdel('lib_dir_symlink'))
        self.computeJob.destroy_op(self)
        self.driver.destroy_op(self)

    def make_lib_dir_symlink(self):
        self.driver.make_lib_dir_symlink(self)

    async def prepare_send(self):
        """Ensures resources are available for sending to agent

        To maintain consistency, do not modify global state before
        calling this method.
        """
        await self.driver.prepare_send(self)

    async def reply_get(self):
        # If we get an exception (cancelled), task is not done.
        # Had to look at the implementation of Queue to see that
        # task_done should only be called if get actually removes
        # the item from the queue.
        r = await self._reply_q.get()
        self._reply_q.task_done()
        return r

    def reply_put(self, reply):
        self._reply_q.put_nowait(reply)

    def run_timeout(self):
        pkdlog('{} maxRunSecs={maxRunSecs}', self, **self)
        self.destroy(error='timeout')

    def send(self):
        if self.maxRunSecs:
            self.timer = tornado.ioloop.IOLoop.current().call_later(
                self.maxRunSecs,
                self.run_timeout,
            )
        self.driver.send(self)

    def __str__(self):
        return f'_Op({self.opName}, {self.opId:.6})'
