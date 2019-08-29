# -*- coding: utf-8 -*-
"""The runner daemon.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import aenum
from functools import partial
from hypercorn.config import Config
from hypercorn.trio import serve
from pykern import pkjson
from pykern.pkdebug import pkdp
import queue
import trio


ACTION_START_REPORT_JOB = 'start_report_job'
ACTION_NO_OP = 'no_op'

_WORK_QUEUE = queue.Queue()

def main():
    for i in range(0, 50):
        _WORK_QUEUE.put(
            {
                'action': ACTION_START_REPORT_JOB if i%2 == 0  else  ACTION_NO_OP,
                'data': i,
            }
        )
    config = Config()
    config.bind = ['localhost:8080']
    trio.run(partial(serve, _app, config))


async def _app(scope, receive, send):
    scope_types = {
        'lifespan': _handle_scope_type_lifespan,
        'http': _handle_scope_type_http,
    }
    await scope_types[scope['type']](receive, send)

async def _process_request_body(body):
    pkdp(f'Received {body} from agent')
    async def _action_ready_for_work(data):
        # TODO: pop off queue
        pkdp(f'Agent is ready for work. Popping from work queue')
        if not _WORK_QUEUE.empty():
            return {
                'action': _WORK_QUEUE.get()['action'],
            }
        else:
            return {
                'action': ACTION_NO_OP,
            }
    async def _action_process_result(data):
        pkdp(f'Agent returned result. Processing it and telling them no-op')
        return {
            'action': ACTION_NO_OP
        }

    action_types = {
        'ready_for_work': _action_ready_for_work,
        'process_result': _action_process_result,

    }
    return await action_types[body['action']](body['data'])

async def _handle_scope_type_http(receive, send):
    request_body = await _http_receive(receive)
    response_body = await _process_request_body(request_body)
    await _http_send(response_body, send)


async def _handle_scope_type_lifespan(receive, send):
    async def _handle_startup():
        await send({'type': 'lifespan.startup.complete'})
    async def _hanlde_shutdown():
        await send({'type': 'lifespan.shutdown.complete'})

    # TODO(e-carlin): Understand this while True. W/o it we get trio.ClosedResourceError
    # on C-c kill of app. It seems that only the first "lifetime" event is passed
    # through _app(3). All subsequent lifetime events come trhough receive()
    while True:
        message = await receive()
        message_types = {
            'lifespan.startup': _handle_startup,
            'lifespan.shutdown': _hanlde_shutdown,
        }
        await message_types[message['type']]()


async def _http_receive(receive):
    body = b''
    more_body = True
    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)
    
    return pkjson.load_any(body)


async def _http_send(response_body, send):
    pkdp(f'body is {response_body}')
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'application/json'),
            # (b'content-length', b'500'), # TODO(e-carlin): Calculate this
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': pkjson.dump_bytes(response_body),
    })