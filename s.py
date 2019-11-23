class _SBatchComputeProcess(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._terminating = False


    def start(self):
        if self.msg.jobProcessCmd == 'compute':
            tornado.ioloop.IOLoop.current().add_callback(
                self._start_compute
            )

    async def start_compute(self):
        # 1. job process prepare_simulation
        #    this will setup the db and return the cmd we need
        cmd = await self._prepare_simulation()
        # 2. submit the job to sbatch
        await self._submit_compute_to_sbatch()
        # 3. wait for running in sbatch (need to be ready for a cancel)
        # 4. once running do background_percent_complete (also read for cancel)

    await def _submit_compute_to_sbatch(self):


    async def _prepare_simulation(self):
        _do_compute_command = None
        _on_exit = tornado.locks.Event()

        async def on_stdout_read(self, text):
            nonlocal _do_compute_command
            _do_compute_command = text

        async def on_exit(self, returncode):
            nonlocal _on_exit
            assert returncode == 0
            _on_exit.set()

        m = self.msg.copy()
        m.jobProcessCmd = 'prepare_simulation'
        p = _JobProcess(
                msg=self.msg.copy().update(
                    jobProcessCmd='prepare_simulation'
                ),
                on_stdout_read,
                on_exit,
            )
        await _on_exit.wait()
        return _do_compute_command



    async def _start(self):

        _submit_to_sbatch_subprocess = _Subprocess(
                self._sbatch_cmd_stdin_env,
                submit_to_sbacth_subprocess_on_stdout_read,
                msg=self.msg,
            )
        _submit_to_sbatch_subprocess.start()


    def _sbatch_cmd_stdin_env(self, msg_in_file):
        cmd =
        stdin =
        env = {}


















































# TODO(e-carlin): rename to cancel?
    def kill(self):
        # TODO(e-carlin): terminate?
        self._terminating = True
        self._subprocess.kill()

    def start(self):
        self._subprocess.start()
        tornado.ioloop.IOLoop.current().add_callback(
            self._on_exit
        )

    def _subprocess_cmd_stdin_env(self, in_file):
        return job.subprocess_cmd_stdin_env(
            ('sirepo', 'job_process', in_file),
            PKDict(
                PYTHONUNBUFFERED='1',
                SIREPO_AUTH_LOGGED_IN_USER=sirepo.auth.logged_in_user(),
                SIREPO_MPI_CORES=self.msg.mpiCores,
                SIREPO_SIM_LIB_FILE_URI=self.msg.get('libFileUri', ''),
                SIREPO_SRDB_ROOT=sirepo.srdb.root(),
            ),
            pyenv='py2',
        )

    async def _on_stdout_read(self, text):
        if self._terminating:
            return
        try:
            r = pkjson.load_any(text)
            if 'opDone' in r:
                del self.comm.processes[self.msg.computeJid]
            if self.msg.jobProcessCmd == 'compute':
                await self.comm.send(
                    self.comm.format_op(
                        self.msg,
                        job.OP_RUN,
                        reply=r,
                    )
                )
            else:
                await self.comm.send(
                    self.comm.format_op(
                        self.msg,
                        job.OP_ANALYSIS,
                        reply=r,
                    )
                )
        except Exception as exc:
            pkdlog('error=={}', exc)

    async def _on_exit(self):
        try:
            await self._subprocess.exit_ready()
            if self._terminating:
                await self.comm.send(
                    self.comm.format_op(
                        self.msg,
                        job.OP_OK,
                        reply=PKDict(state=job.CANCELED, opDone=True),
                    )
                )
                return
            e = self._subprocess.stderr.text.decode('utf-8', errors='ignore')
            if e:
                pkdlog('error={}', e)
            if self._subprocess.returncode != 0:
                await self.comm.send(
                    self.comm.format_op(
                        self.msg,
                        job.OP_ERROR,
                        opDone=True,
                        error=e,
                        reply=PKDict(
                            state=job.ERROR,
                            error='returncode={}'.format(self._subprocess.returncode)),
                    )
                )
        except Exception as exc:
            pkdlog('error={} returncode={}', exc, self._subprocess.returncode)
