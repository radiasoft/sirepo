class _SBatchProcess(PKDict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._terminating = False


    def start(self):
        tornado.ioloop.IOLoop.current().add_callback(
            self._start_compute
            if self.msg.jobProcessCmd == 'compute'
            else self._start_job_process
        )

    async def _start_job_process(self):
        _DockerJobProcess().start()

    # TODO(e-carlin): handling cancel throughout all of this is tricky
    # currently not implemented
    async def _start_compute(self):
        try:
            await self._await_job_completion_and_parallel_status(
                self._submit_compute_to_sbatch(
                    self._prepare_simulation()
                )
            )
        except Exception as e:
            # TODO(e-carlin): comm send this stuff don't return it
            return PKDict(state=job.ERROR, error=str(e), stack=pkdexc())
        return PKDict(state=job.COMPLETED)

    async def _await_job_completion_and_parallel_status(self, job_id):
        parallel_status_running = False
        while True:
            s = self._get_job_sbatch_state(job_id)
            assert s in ('running', 'pending', 'completed'), \
                'invalid state={}'.format(s)
            if s in ('running', 'completed'):
                if self.msg.isParallel and not parallel_status_running: # TODO(e-carlin): sbatch jobs are only parallel
                    self._begin_get_parallel_status()
            if s == 'completed':
                break
            await tornado.gen.sleep(2) # TODO(e-carlin): longer poll
            # TODO(e-carlin): need to wait for one more parallel status read
            # to make sure we got the status at 100%

    async def _begin_get_parallel_status(self):
        self._parallel_status_process = _GetSbatchParallelStatusDockerJobProcess(
            msg=self.msg.copy().update(jobProcessCmd='get_sbatch_parallel_status'),
        )


    def _get_job_sbatch_state(self, job_id):
        o = subprocess.check_output(
            ('scontrol', 'show', 'job', job_id)
        ).decode('utf-8')
        r = re.search(r'(?<=JobState=)(.*)(?= Reason)', o) # TODO(e-carlin): Make middle [A-Z]+
        assert r, 'output={}'.format(s)
        return r.group().lower()

    def _submit_compute_to_sbatch(self, cmd):
        s = self._get_sbatch_script(cmd)
        with open(self.msg.runDir.join('sbatch.job', 'w') as f:
            f.write(s)
            f.seek(0)
            o = subprocess.check_output(
                ('sbatch'),
                stind=f,
            )
            r = re.search(r'\d+$', o)
            assert r is not None, 'output={} did not cotain job id'.format(o)
            return r.group()


    def _get_sbatch_script(self, cmd):
        # TODO(e-carlin): configure the SBATCH* parameters
        return'''#!/bin/bash
#SBATCH --partition=compute
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --mem-per-cpu=128M
#SBATCH -e {}
#SBATCH -o {}
{}
EOF
'''.format(
            template_common.RUN_LOG,
            template_common.RUN_LOG,
            ' '.join(_docker_cmd_base(self.msg) + (cmd,)),
        )

    def _prepare_simulation(self):
        c, s, _ = _JobProcess(
            msg=self.msg.copy().update(jobProcessCmd='prepare_simulation')
        ).subprocess_cmd_stdin_env()
        r = subprocess.check_output(c, s)
        return pkjson.load_any(r).cmd
