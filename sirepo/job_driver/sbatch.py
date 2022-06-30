# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
from sirepo import job
from sirepo import job_driver
from sirepo import util
import asyncssh
import datetime
import errno
import sirepo.job_supervisor
import sirepo.simulation_db
import sirepo.util
import tornado.gen
import tornado.ioloop


class SbatchDriver(job_driver.DriverBase):

    cfg = None

    _KNOWN_HOSTS = None

    __instances = PKDict()

    def __init__(self, op):
        def _op_queue_size(op_kind):
            return self.cfg.run_slots if op_kind == job.OP_RUN else 1

        super().__init__(op)
        self.pkupdate(
            # before it is overwritten by prepare_send
            _local_user_dir=pkio.py_path(op.msg.userDir),
            _srdb_root=None,
            # Allow self.cfg.run_slots and every other op type to
            # run (assume OP_RUN is one of SLOT_OPS). This
            # is essentially a no-op (sbatch constrains its own cpu
            # resources) but makes it easier to code the other cases.
            cpu_slot_q=sirepo.job_supervisor.SlotQueue(
                len(job_driver.SLOT_OPS)
                + self.cfg.run_slots
                - 1,
            ),
            op_slot_q={
                k: sirepo.job_supervisor.SlotQueue(maxsize=_op_queue_size(k))
                for k in job_driver.SLOT_OPS
            },
        )
        self.__instances[self.uid] = self

    async def kill(self):
        if not self._websocket:
            # if there is no websocket then we don't know about the agent
            # so we can't do anything
            return
        # hopefully the agent is nice and listens to the kill
        self._websocket.write_message(PKDict(opName=job.OP_KILL))

    @classmethod
    def get_instance(cls, op):
        u = op.msg.uid
        return cls.__instances.pksetdefault(u, lambda: cls(op))[u]

    @classmethod
    def init_class(cls, job_supervisor_module):
        global job_supervisor
        job_supervisor = job_supervisor_module
        cls.cfg = pkconfig.init(
            agent_log_read_sleep=(
                5,
                int,
                'how long to wait before reading the agent log on start',
            ),
            agent_starting_secs=(
                cls._AGENT_STARTING_SECS_DEFAULT * 3,
                int,
                'how long to wait for agent start',
            ),
            cores=(None, int, 'dev cores config'),
            host=pkconfig.Required(str, 'host name for slum controller'),
            host_key=pkconfig.Required(str, 'host key'),
            run_slots=(1, int, 'number of concurrent OP_RUN for each user'),
            shifter_image=(None, str, 'needed if using Shifter'),
            sirepo_cmd=pkconfig.Required(str, 'how to run sirepo'),
            srdb_root=pkconfig.Required(_cfg_srdb_root, 'where to run job_agent, must include {sbatch_user}'),
            supervisor_uri=job.DEFAULT_SUPERVISOR_URI_DECL,
        )
        cls._KNOWN_HOSTS = (
            cls.cfg.host_key if cls.cfg.host in cls.cfg.host_key
            else '{} {}'.format(cls.cfg.host, cls.cfg.host_key)
        ).encode('ascii')
        return cls

    def op_is_untimed(self, op):
        return True

    async def prepare_send(self, op):
        m = op.msg
        c = m.pkdel('sbatchCredentials')
        if self._srdb_root is None or c:
            if c:
                self._creds = c
            if not self.get('_creds') or 'username' not in self._creds:
                self._raise_sbatch_login_srexception('no-creds', m)
            self._srdb_root = self.cfg.srdb_root.format(
                sbatch_user=self._creds.username,
            )
        m.userDir = '/'.join(
            (
                str(self._srdb_root),
                sirepo.simulation_db.USER_ROOT_DIR,
                m.uid,
            )
        )
        m.runDir = '/'.join((m.userDir, m.simulationType, m.computeJid))
        if op.opName == job.OP_RUN:
            assert m.sbatchHours
            if self.cfg.cores:
                m.sbatchCores = min(m.sbatchCores, self.cfg.cores)
            m.mpiCores = m.sbatchCores
        m.shifterImage = self.cfg.shifter_image
        return await super().prepare_send(op)

    def _agent_env(self):
        return super()._agent_env(
            env=PKDict(
                SIREPO_SRDB_ROOT=self._srdb_root,
            )
        )

    async def _do_agent_start(self, op):
        log_file = 'job_agent.log'
        agent_start_dir = self._srdb_root
        script = f'''#!/bin/bash
{self._agent_start_dev()}
set -e
mkdir -p '{agent_start_dir}'
cd '{self._srdb_root}'
{self._agent_env()}
(/usr/bin/env; setsid {self.cfg.sirepo_cmd} job_agent start_sbatch) >& {log_file} &
disown
'''

        def write_to_log(stdout, stderr, filename):
            p = pkio.py_path(self._local_user_dir).join('agent-sbatch', self.cfg.host)
            pkio.mkdir_parent(p)
            f = p.join(f'{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}-{filename}.log')
            r = pkjson.dump_pretty(PKDict(stdout=stdout, stderr=stderr, filename=f), f)
            if pkconfig.channel_in('dev'):
                pkdlog(r)

        async def get_agent_log(connection, before_start=True):
            try:
                if not before_start:
                    await tornado.gen.sleep(self.cfg.agent_log_read_sleep)
                async with connection.create_process(
                    f'/bin/cat {agent_start_dir}/{log_file}'
                ) as p:
                    o, e = await p.communicate()
                    write_to_log(o, e, f"remote-{'before' if before_start else 'after'}-start")
            except sirepo.util.ASYNC_CANCELED_ERROR:
                raise
            except Exception as e:
                pkdlog(
                    '{} e={} stack={}',
                    self,
                    e,
                    pkdexc(),
                )
        try:
            async with asyncssh.connect(
                self.cfg.host,
                username=self._creds.username,
                password=self._creds.password + self._creds.otp if 'nersc' in self.cfg.host else self._creds.password,
                known_hosts=self._KNOWN_HOSTS,
            ) as c:
                async with c.create_process('/bin/bash --noprofile --norc -l') as p:
                    await get_agent_log(c, before_start=True)
                    o, e = await p.communicate(input=script)
                    if o or e:
                        write_to_log(o, e, 'start')
                self.driver_details.pkupdate(
                    host=self.cfg.host,
                    username=self._creds.username,
                )
                await get_agent_log(c, before_start=False)
        except asyncssh.misc.PermissionDenied:
            pkdlog('{}', pkdexc())
            self._srdb_root = None
            self._raise_sbatch_login_srexception('invalid-creds', op.msg)
        except asyncssh.misc.ProtocolError:
            pkdlog('{}', pkdexc())
            raise sirepo.util.UserAlert(
                f'Unable to connect to {self.cfg.host}. Please try again later.',
            )
        except OSError as e:
            pkdlog('{}', pkdexc())
            if e.errno == errno.EHOSTUNREACH:
                raise sirepo.util.UserAlert(
                    f'Host {self.cfg.host} unreachable. Please try again later.',
                )
            raise
        finally:
            self.pkdel('_creds')


    def _agent_start_dev(self):
        if not pkconfig.channel_in('dev'):
            return ''
        res = '''
scancel -u $USER >& /dev/null || true
'''
        if self.cfg.shifter_image:
            res += '''
(cd ~/src/radiasoft/sirepo && git pull -q) || true
(cd ~/src/radiasoft/pykern && git pull -q) || true
'''
        return res

    def _raise_sbatch_login_srexception(self, reason, msg):
        raise util.SRException(
            'sbatchLogin',
            PKDict(
                host=self.cfg.host,
                isModal=True,
                isGeneral=True,
                reason=reason,
                computeModel=msg.computeModel,
                simulationId=msg.simulationId,
                simulationType=msg.simulationType,
            ),
        )

    def _start_idle_timeout(self):
        """Sbatch agents should be kept alive as long as possible"""
        pass

    def _websocket_free(self):
        self._srdb_root = None


CLASS = SbatchDriver


def _cfg_srdb_root(value):
    assert '{sbatch_user}' in value, \
        'must include {sbatch_user} in string'
    return value
