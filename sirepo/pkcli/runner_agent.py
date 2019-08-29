# -*- coding: utf-8 -*-
"""The runner daemon.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import asks
from pykern import pkjson
from pykern.pkdebug import pkdp
from sirepo import runner_daemon
import trio

ACTION_READY_FOR_WORK = 'ready_for_work'
ACTION_PROCESS_RESULT = 'process_result'


def start():
    trio.run(_main)

async def _call_daemon(body):
    try:
        response = await asks.post('http://localhost:8080', json=body)
        return pkjson.load_any(response.content)
    except Exception as e:
        pkdp(f'Exception with _call_daemon(). Caused by: {e}')
        return {}

async def _call_daemon_ready_for_work():
    body = {
        'action': 'ready_for_work',
        'data': {},
    }
    return await _call_daemon(body)

async def _call_daemon_with_result(result):
    body = {
        'action': 'process_result',
        'data': result,
    }
    await _call_daemon(body) # TODO(e-carlin): Do nothing with response from this call?

async def _main():
    while True:
        daemon_request = await _call_daemon_ready_for_work()
        action = daemon_request.get('action', 'no_op')
        action_types = {
            'no_op': _perform_no_op,
            'start_report_job': _start_report_job,
        }
        await action_types[action](daemon_request)

async def _perform_no_op(daemon_request):
    pkdp('Daemon requested no_op. Going to sleep for a bit.')
    await trio.sleep(2) # TODO(e-carlin): Exponential backoff?

async def _start_report_job(daemon_request):
    pkdp(f'Daemon requested start_report_job {daemon_request}. ls -l instead.')
    await trio.open_process(['ls', '-l'])
    result = {
        'foo': 'bar'
    }
    await _call_daemon_with_result(result)


