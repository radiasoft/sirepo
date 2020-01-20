# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog, pkdexc
from sirepo import job
from sirepo import job_driver
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

_MAX_RETRIES = 10

# can be anything that is globally unique
_RETRY_FLAG = object()


class Awaited(Exception):
    """An await occurred, restart operation"""
    pass


def init():
    global _DB_DIR, cfg, _NEXT_REQUEST_SECONDS
    if _DB_DIR:
        return
    job.init()
    job_driver.init()
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
            return 'ServerReq({})'.format(self)
        return 'ServerReq(api={}, jid={})'.format(
            c.get('api'),
            c.get('computeJid'),
        )


async def terminate():
    await job_driver.terminate()


class _ComputeJob(PKDict):

    instances = PKDict()

    def __init__(self, req, **kwargs):
        super().__init__(ops=[], **kwargs)
        self.pksetdefault(db=lambda: self.__db_init(req))

    def destroy_op(self, op):
        if op in self.ops:
            self.ops.remove(op)

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

    def ops_valid_in_protocol(self):
        """Ensures that only one op per type runs simultaneously

        This limits running multiple job_cmds such as OP_ANALYSIS or
        OP_RUN so it is a bit of fair scheduling.

        Returns:
            list: one of each available type
        """
        def get_ops_pending_done_types():
            d = collections.defaultdict(int)
            for v in self.ops_pending_done.values():
                d[v.msg.opName] += 1
            return d

        if there is a cancel or analysis, and
        is_set
             op
need to check if ready in with send allocation

        r = []
        t = get_ops_pending_done_types()
        for o in self.ops_pending_send:
            if t.get(o.msg.opName, 0) > 0:
                continue
            that are not just ready to send
                o.send_ready.set()
            assert o.opId not in self.ops_pending_done
            t[o.msg.opName] += 1
            r.append(o)
        return r

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
        finally:
            req.task = None

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
            self._req_is_valid(req)
            or self.db.status not in _RUNNING_PENDING
        ):
            # job is not relevant, but let the user know it isn't running
            return r
        c = False
        for o in self.ops:
            if self.db.isParallel and o.opName == job.OP_ANALYSIS:
                continue
            o.set_canceled()
            if o.opName == job.OP_RUN and o.driver.op_was_sent(o):
                c = True
        await self.driver_ready()
        self.db.status = job.CANCELED
        self.__db_write()
        if c:
todo: could throw awaited
            await self._send_with_single_reply(job.OP_CANCEL, req)
        return r

    async def _receive_api_runSimulation(self, req):
        f = req.content.get('forceRun')
        if self.db.status == _RUNNING_PENDING:
            if f or not self._req_is_valid(req)
                return PKDict(state=job.ERROR, error='another browser is running the simulation')
            return PKDict(state=self.db.status)
        if (f
            or not self._req_is_valid(req)
            or self.db.status != job.COMPLETED
        ):
            o = None
            try:
                o = self._create_op(
                    job.OP_RUN,
                    req,
                    jobCmd='compute',
                    nextRequestSeconds=self.db.nextRequestSeconds,
                )
                await self.driver_ready(req)
                await o.ready_send()
                self.__db_init(req, prev_db=self.db)
                self.db.computeJobSerial = int(time.time())
                self.db.pkupdate(status=job.PENDING)
                self.__db_write()
                o.make_lib_dir_symlink()
                o.send()
lock needs to be held(?)
                o.task = None
                tornado.ioloop.IOLoop.current().add_callback(self._run, req, o)
            except Exception:
                # _run destroys in the happy path (never got to _run here)
                if o:
                    o.destroy()
TODO: the ready next op that is in the queue that has not been sent
                raise
        # Read this first https://github.com/radiasoft/sirepo/issues/2007
        return await self._receive_api_runStatus(req)

    async def _receive_api_runStatus(self, req):
        def res(**kwargs):
            r = PKDict(**kwargs)
            if self.db.error:
                r.error = self.db.error
            if self.db.isParallel:
                r.update(self.db.parallelStatus)
                r.computeJobHash = self.db.computeJobHash
                r.computeJobSerial = self.db.computeJobSerial
                r.elapsedTime = r.lastUpdateTime - self.db.computeJobStart
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
        await self.driver_ready()
        return await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobCmd='sequential_result',
        )

    async def _receive_api_sbatchLogin(self, req):
        return await self._send_with_single_reply(job.OP_SBATCH_LOGIN, req)

    async def _receive_api_simulationFrame(self, req):
#TODO(robnagler) not found
        assert self.db.computeJobHash == req.content.computeJobHash, \
            'expected computeJobHash={} but got={}'.format(
                self.db.computeJobHash,
                req.content.computeJobHash,
            )
        # there has to be a computeJobSerial
        assert self.db.computeJobSerial == req.content.computeJobSerial, \
            'expected computeJobSerial={} but got={}'.format(
                self.db.computeJobSerial,
                req.content.computeJobSerial,
            )
        return await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobCmd='get_simulation_frame'
        )

    async def _run(self, req, op):
        try:
            op.task = asyncio.current_task()
            while True:
                try:
                    await self.driver_ready()
                    await op.ready_send()
                    r = await op.reply_ready()
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
                    break
            except Exception as e:
                pkdlog('error={} stack={}', e, pkdexc())
we do not own this necessarily own the job at this point
                self.db.status = job.ERROR
                self.db.error = e
        finally:
todo: run scheduler
            op.destroy()

    def _create_op(self, opName, req, **kwargs):
#TODO(robnagler) kind should be set earlier in the queuing process.
        req.kind = job.PARALLEL if self.db.isParallel and opName != job.OP_ANALYSIS \
            else job.SEQUENTIAL
        req.simulationType = self.db.simulationType
        # TODO(e-carlin): We need to be able to cancel requests waiting in this
        # state. Currently we assume that all requests get a driver and the
        # code does not block.
        d = job_driver.get_instance(req, self.db.jobRunMode)
        if 'dataFileKey' in kwargs:
            kwargs['dataFileUri'] = job.supervisor_file_uri(
                d.get_supervisor_uri(),
                job.DATA_FILE_URI,
                kwargs.pop('dataFileKey')
            )
        o = _Op(
#TODO(robnagler) don't like the camelcase. It doesn't actually work right because
# these values are never sent directly, only msg which can be camelcase
            computeJob=self,
            driver=d,
            kind=req.kind,
            maxRunSecs=0 if opName in _UNTIMED_OPS else _MAX_RUN_SECS[req.kind],
            msg=PKDict(
                req.content
            ).pkupdate(
                **kwargs,
            ).pksetdefault(jobRunMode=self.db.jobRunMode),
            opName=opName,
            task=asyncio.current_task(),
        )
        self.ops.append(o)
        return o

    def _req_is_valid(self, req):

        validate serial and hash

                pkdlog(
                    'invalid computeJobHash self={} req={}',
                    self.db.computeJobHash,
                    req.content.computeJobHash
                )

    async def _send_with_single_reply(self, opName, req, **kwargs):
        o = self._create_op(opName, req, **kwargs)
        try:
            await o.prepare_send()
            o.send()
            return await o.reply_ready()
        finally:
todo:            the ready next op that is in the queue that has not been sent
            op.destroy()


class _Op(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(
            do_not_send=False,
            opId=job.unique_key(),
            send_ready=tornado.locks.Event(),
            _reply_q=tornado.queues.Queue(),
        )
        self.msg.update(opId=self.opId, opName=self.opName)

    def destroy(self, error=None):
        if 'timer' in self:
            tornado.ioloop.IOLoop.current().remove_timeout(self.timer)
        if 'lib_dir_symlink' in self:
todo: need a lock on this; lib_dir_symlink is unique but....
            pykern.pkio.unchecked_remove(self.lib_dir_symlink)
        if self.computeJob:
            self.computeJob.destroy_op(self)
        if self.driver:
            self.driver.destroy_op(self)


this may not make sense, because it happens in websocket_free
todo:        run_scheduler

    def make_lib_dir_symlink(self):
        self.driver.make_lib_dir_symlink(self)

    def ready_to_send(self):
        if there are not ops ahead of me:
            return True
        self._op_queue.wait()
        return False


    def reply_put(self, reply):
        self._reply_q.put_nowait(reply)

    async def reply_ready(self):
        # If we get an exception (cancelled), task is not done
        r = await self._reply_q.get()
        self._reply_q.task_done()
        return r

    def run_timeout(self):
        if self.do_not_send:
            return
        pkdlog('opId={opId} opName={opName} maxRunSecs={maxRunSecs}', **self)
        self.set_canceled()

    def set_canceled(self):
        self.task.cancel()

todo
        self.do_not_send = True
        self.send_ready.set()
        self.reply_put(PKDict(state=job.CANCELED))

    def set_errored(self, error):
        self.do_not_send = True
        self.send_ready.set()
        self.reply_put(PKDict(state=job.ERROR, error=error))

    async def send(self):
        return await self.driver.send(self)

    def start_timer(self):
        if not self.maxRunSecs:
            return
        self.timer = tornado.ioloop.IOLoop.current().call_later(self.maxRunSecs, self.run_timeout)
