# -*- coding: utf-8 -*-
"""The runner daemon.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import aenum
from collections import deque
from functools import partial
from hypercorn.config import Config
from hypercorn.trio import serve
from pykern import pkjson
from pykern.pkdebug import pkdp
import queue
from sirepo import simulation_db
from sirepo.template import template_common
import trio
import uuid

ACTION_NO_OP = 'no_op'

_WORK_QUEUE = deque([])

def start():
    config = Config()
    config.bind = ['localhost:8080']
    trio.run(partial(serve, _app, config))


async def _app(scope, receive, send):
    scope_types = {
        'lifespan': _handle_scope_type_lifespan,
        'http': _handle_scope_type_http,
    }
    await scope_types[scope['type']](receive, send)

async def _handle_scope_type_http(receive, send):
    request_body = await _http_receive(receive)
    response_body = await _process_request_body(request_body)
    await _http_send(response_body, send)


async def _handle_scope_type_lifespan(receive, send):
    async def _handle_complete(lifespan):
        await send({'type': f'{lifespan}.complete'})

    # TODO(e-carlin): Understand this while True. W/o it we get trio.ClosedResourceError
    # on C-c kill of app. It seems that only the first "lifetime" event is passed
    # through _app(3). All subsequent lifetime events come trhough receive()
    while True:
        message = await receive()
        message_type = message['type']
        message_types = {
            'lifespan.startup': _handle_complete,
            'lifespan.shutdown': _handle_complete,
        }

        await message_types[message_type](message_type)


async def _http_receive(receive):
    body = b''
    more_body = True
    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)
    
    return pkjson.load_any(body)


async def _http_send(response_body, send):
    pkdp(f'Sending to agent: {response_body}')
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


async def _process_request_body(body):
    action_types = {
        'ready_for_work': _action_ready_for_work,
        'start_report_job': _action_start_report_job,
    }
    return action_types[body['action']](body)

def _action_ready_for_work(body):
    pkdp(f'Agent is ready for work')
    if _WORK_QUEUE:
        action = _WORK_QUEUE.popleft()
        return action
    else:
        pkdp('Action is no_op')
        return {
            'action': ACTION_NO_OP,
        }

def _action_start_report_job(request_body):
    pkdp('Start report job requested')
    _WORK_QUEUE.append(request_body)
    return {}