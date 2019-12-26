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


def init():
    global _DB_DIR, cfg, _NEXT_REQUEST_SECONDS
    if _DB_DIR:
        return
    job.init()
    job_driver.init()
    _DB_DIR = sirepo.srdb.root().join(_DB_SUBDIR)
    pykern.pkio.mkdir_parent(_DB_DIR)
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


class ServerReq(PKDict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uid = self.content.uid
        self._response = None
        self._response_received = tornado.locks.Event()

    async def receive(self):
        s = self.content.pkdel('serverSecret')
        # no longer contains secret so ok to log
        assert s, \
            'no secret in message: {}'.format(self.content)
        assert s == sirepo.job.cfg.server_secret, \
            'server_secret did not match'.format(self.content)
        self.handler.write(await _ComputeJob.receive(self))


async def terminate():
    await job_driver.terminate()


class _ComputeJob(PKDict):

    instances = PKDict()

    def __init__(self, req, **kwargs):
        super().__init__(_ops=[], _sent_run=False, **kwargs)
        self.pksetdefault(db=lambda: self.__db_init(req))

    def destroy_op(self, op):
        pkdlog('destroy_op={}', op.opId)
        self._ops.remove(op)
        op.destroy()

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
        pkdlog('{} jid={}', req.content.api, req.content.get('computeJid'))
        try:
            return await getattr(
                cls.get_instance(req),
                '_receive_' + req.content.api,
            )(req)
        except Exception as e:
            pkdlog('error={} stack={}', e, pkdexc())
            if isinstance(e, sirepo.util.Reply):
                return sirepo.http_reply.gen_tornado_exception(e)
            raise

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
        )

    async def _receive_api_runCancel(self, req):
        r = PKDict(state=job.CANCELED)
        if (
            self.db.computeJobHash != req.content.computeJobHash
            or self.db.computeJobSerial != req.content.computeJobSerial
        ):
            # not our job, but let the user know it isn't running
            return r
        if self._sent_run:
            await self._send_with_single_reply(
                job.OP_CANCEL,
                req,
            )
        self.db.status = job.CANCELED
        for o in self._ops:
            if o.msg.computeJid == req.content.computeJid:
                o.set_canceled()
        self.__db_write()
        return r

    async def _receive_api_runSimulation(self, req):
        f = req.content.get('forceRun')
        if not f and self.db.status == _RUNNING_PENDING:
            if self.db.computeJobHash != req.content.computeJobHash:
#TODO(robnagler) need to deal with double clicks
#TODO(robnagler) do transient/sequential sims runSim without a cancel? I think we
#  should require the GUI to cancel before running so would return an error here
                raise AssertionError('FIXME')
            return PKDict(state=job.RUNNING)
        if (f
            or self.db.computeJobHash != req.content.computeJobHash
            or self.db.status != job.COMPLETED
        ):
            self.__db_init(req, prev_db=self.db)
            self.db.computeJobSerial = int(time.time())
            self.db.pkupdate(status=job.PENDING)
            self.__db_write()
            o = await self._create_op(
                job.OP_RUN,
                req,
                jobCmd='compute',
                nextRequestSeconds=self.db.nextRequestSeconds,
            )
            try:
                o.lib_dir_symlink()
                await o.send()
                self._sent_run = True
                tornado.ioloop.IOLoop.current().add_callback(self._run, req, o)
            except Exception:
                # _run destroys in the happy path
                self.destroy_op(o)
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
        return await self._send_with_single_reply(
            job.OP_ANALYSIS,
            req,
            jobCmd='sequential_result',
        )

    async def _receive_api_sbatchLogin(self, req):
        return await self._send_with_single_reply(job.OP_SBATCH_LOGIN, req)

    async def _receive_api_simulationFrame(self, req):
        # retry if we get a canceled
        for i in range(2):
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
            r = await self._send_with_single_reply(
                job.OP_ANALYSIS,
                req,
                'get_simulation_frame'
            )
            if r.get('state') != sirepo.job.CANCELED:
                return r
        return r

#TODO(robnagler) need to assert that this is still our job
#TODO(robnagler) this is a general problem: after await: check ownership
    async def _run(self, req, op):
        try:
            if self.db.computeJobHash != req.content.computeJobHash:
                pkdlog(
                    'invalid computeJobHash self={} req={}',
                    self.db.computeJobHash,
                    req.content.computeJobHash
                )
                return
            try:
                while True:
                    r = await op.reply_ready()
                    if r.state == job.CANCELED:
                        break
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
            except Exception as e:
                pkdlog('error={} stack={}', e, pkdexc())
                self.db.status = job.ERROR
                self.db.error = e
        finally:
            self.destroy_op(op)

    async def _create_op(self, opName, req, jobCmd, **kwargs):
#TODO(robnagler) kind should be set earlier in the queuing process.
        req.kind = job.PARALLEL if self.db.isParallel and opName != job.OP_ANALYSIS \
            else job.SEQUENTIAL
        req.simulationType = self.db.simulationType
        # TODO(e-carlin): We need to be able to cancel requests waiting in this
        # state. Currently we assume that all requests get a driver and the
        # code does not block.
        d = await job_driver.get_instance(req, self.db.jobRunMode)
        o = _Op(
            driver=d,
            kind=req.kind,
            maxRunSecs=0 if opName in _UNTIMED_OPS else _MAX_RUN_SECS[req.kind],
            msg=PKDict(
                req.content
            ).pkupdate(
                jobCmd=jobCmd,
                **kwargs,
            ).pksetdefault(jobRunMode=self.db.jobRunMode),
            opName=opName,
        )
        self._ops.append(o)
        return o

    async def _send_with_single_reply(self, opName, req, jobCmd=None):
        o = await self._create_op(opName, req, jobCmd)
        try:
            await o.send()
            r = await o.reply_ready()
            assert 'state' not in r or r.state in job.EXIT_STATUSES
            return r
        finally:
            self.destroy_op(o)


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

    def destroy(self):
        if 'timer' in self:
            tornado.ioloop.IOLoop.current().remove_timeout(self.timer)
        if '_lib_dir_symlink' in self:
            pykern.pkio.unchecked_remove(self._lib_dir_symlink)
        self.driver.destroy_op(self)

    def lib_dir_symlink(self):
        if not self.driver.has_remote_agent():
            return
        m = self.msg
        d = pykern.pkio.py_path(m.simulation_lib_dir)
        self._lib_dir_symlink = sirepo.job.LIB_FILE_ROOT.join(
            sirepo.job.unique_key()
        )
        self._lib_dir_symlink.mksymlinkto(d, absolute=True)
        m.pkupdate(
            libFileUri=sirepo.job.LIB_FILE_ABS_URI +
            self._lib_dir_symlink.basename + '/',
            libFileList=[f.basename for f in d.listdir()],
        )

    def reply_put(self, msg):
        self._reply_q.put_nowait(msg)

    async def reply_ready(self):
        r = await self._reply_q.get()
        self._reply_q.task_done()
        return r

    def run_timeout(self):
        if self.canceled or self.errored:
            return
        pkdlog('opId={opId} opName={opName} maxRunSecs={maxRunSecs}', **self)
        self.set_canceled()

    def set_canceled(self):
        self.do_not_send = True
        self.reply_put(PKDict(state=job.CANCELED))
        self.send_ready.set()
        self.driver.cancel_op(self)

    def set_errored(self, error):
        self.do_not_send = True
        self.send_ready.set()
        self.reply_put(
            PKDict(state=job.ERROR, error=error),
        )
        self.send_ready.set()

    async def send(self):
        await self.driver.send(self)

    def start_timer(self):
        if not self.maxRunSecs:
            return
        self.timer = tornado.ioloop.IOLoop.current().call_later(self.maxRunSecs, self.run_timeout)
