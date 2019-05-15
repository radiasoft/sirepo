# -*- coding: utf-8 -*-
u"""End-to-end tests of the runner daemon feature.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import pytest
import time
import os
import subprocess
import sys


# Simple test that we can (1) run something (runSimulation), (2) get results
# (runStatus).
def test_runner_myapp():
    os.environ['SIREPO_FEATURE_CONFIG_RUNNER_DAEMON'] = '1'
    os.environ['PYTHONUNBUFFERED'] = '1'
    py3_env = _assert_py3()

    from pykern import pkio
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp
    from sirepo import srunit

    fc = srunit.flask_client(sim_types='myapp')
    fc.sr_login_as_guest()

    from sirepo import srdb
    pkdc(srdb.runner_socket_path())

    pkio.unchecked_remove(srdb.runner_socket_path())

    runner_env = dict(py3_env)
    runner_env['SIREPO_SRDB_ROOT'] = str(srdb.root())
    runner = subprocess.Popen(
        ['pyenv', 'exec', 'sirepo', 'runner', 'start'],
        env=runner_env,
    )
    try:
        for _ in range(30):
            if srdb.runner_socket_path().exists():
                break
            time.sleep(0.1)
        else:
            pkunit.pkfail('runner daemon did not start up')

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
            run = fc.sr_post(
                'runStatus',
                run.nextRequest
            )
            pkdc(run)
            if run.state == 'completed':
                break
            time.sleep(1)
        else:
            pkunit.pkfail('runStatus: failed to complete: {}', run)
        # Just double-check it actually worked
        assert u'plots' in run
    finally:
        runner.terminate()
        runner.wait()


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
            ['pyenv', 'exec', 'sirepo', 'runner', '--help'],
            env=res,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        out = e.output
    pkunit.pkok(
        'runner daemon' in out,
        '"runner daemon" not in help: {}',
        out,
    )
    return res
