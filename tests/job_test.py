# -*- coding: utf-8 -*-
"""End to end test of running a job.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


import pytest
import os
import subprocess
import time
from pykern.pkdebug import pkdc, pkdp

def test_run_myapp():
    from sirepo import srdb
    from sirepo import srunit
    from pykern import pkunit
    from sirepo import job
    os.environ['SIREPO_FEATURE_CONFIG_RUNNER_DAEMON'] = '1'
    os.environ['PYTHONUNBUFFERED'] = '1'
    py3_env = _assert_py3()


    fc = srunit.flask_client(sim_types='myapp')
    fc.sr_login_as_guest()

    supervisor_env = dict(py3_env)
    supervisor_env['SIREPO_SRDB_ROOT'] = str(srdb.root())
    supervisor = subprocess.Popen(
        ['pyenv', 'exec', 'sirepo', 'job_supervisor', 'start'],
        env=supervisor_env,
    )

    try:
        for _ in range(30):
            if _server_up(job.server_cfg.supervisor_uri):
                break
            time.sleep(0.1)
        else:
            pkunit.pkfail('job supervisor did not start up')
        
        fc.get('/myapp')
        data = fc.sr_post(
            'listSimulations',
            {'simulationType': 'myapp',
             'search': {'simulationName': 'heightWeightReport'}},
        )
        pkdc(data)
        data = data[0].simulation
        pkdc(data)
        data = fc.sr_get_json(
            'simulationData',
            params=dict(
                pretty='1',
                simulation_id=data.simulationId,
                simulation_type='myapp',
            ),
        )
        pkdc(data)
        run = fc.sr_post(
            'runSimulation',
            dict(
                forceRun=False,
                models=data.models,
                report='heightWeightReport',
                simulationId=data.models.simulation.simulationId,
                simulationType=data.simulationType,
            ),
        )
        pkdc(run)
        for _ in range(10):
            if run.state == 'completed':
                break
            time.sleep(1)
            run = fc.sr_post(
                'runStatus',
                run.nextRequest
            )
            pkdc(run)
        else:
            pkunit.pkfail('runStatus: failed to complete: {}', run)
        # Just double-check it actually worked
        assert u'plots' in run
    finally:
        supervisor.terminate()
        supervisor.wait()


def _server_up(url):
    import requests
    try:
        r = requests.head(url)
        return r.status_code == 405
    except requests.ConnectionError:
        pass

def _assert_py3():
    """Check if the py3 environment is set up properly"""
    res = dict()
    for k, v in os.environ.items():
        if ('PYENV' in k or 'PYTHON' in k):
            continue
        if k in ('PATH', 'LD_LIBRARY_PATH'):
            v2 = []
            for x in v.split(':'):
                if x and 'py2' not in x:
                    v2.append(x)
            v = ':'.join(v2)
        res[k] = v
    res['PYENV_VERSION'] = 'py3'

    try:
        out = subprocess.check_output(
            ['pyenv', 'which', 'sirepo'],
            env=res,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        out = e.output
    from pykern import pkunit

    pkunit.pkok(
        '/py3/bin/sirepo' in out,
        'expecting sirepo in a py3: {}',
        out,
    )
    try:
        out = subprocess.check_output(
            ['pyenv', 'exec', 'sirepo', 'job_supervisor', '--help'],
            env=res,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        out = e.output
    pkunit.pkok(
        'job_supervisor ' in out,
        '"job_supervisor" not in help: {}',
        out,
    )

    try:
        out = subprocess.check_output(
            ['pyenv', 'exec', 'sirepo', 'job_driver', '--help'],
            env=res,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        out = e.output
    pkunit.pkok(
        'job_driver' in out,
        '"job_driver" not in help: {}',
        out,
    )
    return res