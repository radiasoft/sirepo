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

    # Check if the py3 environment is set up
    py3_env = dict(os.environ)
    py3_env['PYENV_VERSION'] = 'py3'
    returncode = subprocess.call(
        ['pyenv', 'exec', 'sirepo', '--help'], env=py3_env
    )
    # if 'sirepo' isn't found, returncode == 127
    if returncode != 1:
        pytest.skip('py3 environment not configured')

    from sirepo import srunit
    from pykern import pkunit
    from pykern import pkio

    fc = srunit.flask_client()

    from sirepo import srdb
    print(srdb.runner_socket_path())

    pkio.unchecked_remove(srdb.runner_socket_path())

    runner_env = dict(py3_env)
    runner_env['SIREPO_SRDB_ROOT'] = str(srdb.root())
    runner = subprocess.Popen(
        ['pyenv', 'exec', 'sirepo', 'runner', 'start'], env=runner_env
    )
    try:
        # Wait for the server to have started up
        while not srdb.runner_socket_path().exists():
            time.sleep(0.1)

        fc.get('/myapp')
        data = fc.sr_post(
            'listSimulations',
            {'simulationType': 'myapp',
             'search': {'simulationName': 'heightWeightReport'}},
        )
        print(data)
        data = data[0].simulation
        print(data)
        data = fc.sr_get(
            'simulationData',
            params=dict(
                pretty='1',
                simulation_id=data.simulationId,
                simulation_type='myapp',
            ),
        )
        print(data)
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
        print(run)
        for _ in range(10):
            run = fc.sr_post(
                'runStatus',
                run.nextRequest
            )
            print(run)
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
