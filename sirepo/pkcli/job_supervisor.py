# -*- coding: utf-8 -*-
"""The runner daemon.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from collections import deque
from functools import partial
from hypercorn.config import Config
from hypercorn.trio import serve
from pykern import pkjson
from pykern import pkcollections
from pykern.pkdebug import pkdp, pkdlog, pkdexc
from sirepo import simulation_db
from sirepo.template import template_common
import aenum
import queue
import trio
import uuid


_BROKERS = {}
_NURSERY = None


def start():
    trio.run(_initialize)


async def _app(scope, receive, send):
    client = scope['client']
    pkdp(f'New call to _app. scope.client: {client}')
    scope_types = {
        'lifespan': _handle_scope_type_lifespan,
        'http': _handle_scope_type_http,
    }
    await scope_types[scope['type']](receive, send)


def _create_broker_if_not_found(uid, nursery):
    if uid not in _BROKERS:
        #TODO(e-carlin): Actually start the driver client
        broker = _Broker(nursery)
        broker.start()
        _BROKERS[uid] = broker

    return _BROKERS[uid]


async def _handle_scope_type_http(receive, send):
    request_body = await _http_receive(receive)
    await _process_request_body(request_body, send)


async def _handle_scope_type_lifespan(receive, send):
    async def _handle_complete(lifespan):
        await send({'type': f'{lifespan}.complete'})

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
    
    return pkcollections.Dict(pkjson.load_any(body))


async def _http_send(body, send):
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'application/json'),
            # (b'content-length', b'500'), # TODO(e-carlin): Calculate this
        ],
    })
    #TODO(e-carlin): What if the first send succeeds but this one fails?
    # How do we "rollback"?
    await send({
        'type': 'http.response.body',
        'body': pkjson.dump_bytes(body),
    })


async def _initialize():
    config = Config()
    config.bind = ['0.0.0.0:8080']
    config.keep_alive_timeout = 60 #TODO(e-carlin): This delays closing the connection in long-polling. Find the right number.
    global _NURSERY 
    async with trio.open_nursery() as _NURSERY:
        await serve(_app, config)

async def _process_request_body(body, send):
    source_types = ['server', 'driver']
    assert body.source in source_types

    broker = _create_broker_if_not_found(body.uid, _NURSERY)
    process_fn = getattr(broker, f'process_{body.source}_request')
    await process_fn(body, send)


class _Broker():
    def __init__(self, nursery):
        self._driver_queue = deque([])
        self._server_responses = {} #TODO(e-carlin): I'd like to use pkcollections.Dict() but it prevents delete. Why is that?
        self._nursery = nursery

    def start(self):
        self._nursery.start_soon(self._statisctics)

    async def _statisctics(self):
        while True:
            pkdp('##### BROKER STATS #####')
            pkdp(f'Driver queue len = {len(self._driver_queue)}')
            pkdp(f'Server responses dict len = {len(self._server_responses)}')
            pkdp('########################')
            await trio.sleep(5)

    async def process_driver_request(self, request, driver_send):
        pkdlog(f'Processing driver request. Request: {request}')
        if request.action == 'ready_for_work':
            while True:
                #TODO(e-carlin): This should start on its own. Not have to wait for driver request
                if self._driver_queue:
                    work_to_do = self._driver_queue.popleft()
                    pkdlog(f'Work found in driver queue. Sending to driver. Work: {work_to_do}')
                    await _http_send(work_to_do, driver_send)
                else:
                    pkdp('No work to do. Going to sleep..')
                    await trio.sleep(1) # Wait for some work to do before replying
        
        else: # We have some results
            reply = self._server_responses[request.request_id]
            pkdlog(f'Replying to server: {request}')
            await _http_send(request, reply.send)
            reply.reply_sent.set()

    async def process_server_request(self, request, server_send):
        pkdlog(f'Processing server request. Request: {request}')
        reply_sent = trio.Event()
        # request_id = str(uuid.uuid4())
        request_id = 'abc123' #TODO(e-carlin): Hardcoded for now for testing
        work_to_do = pkcollections.Dict({
            'request_id': request_id,
            'request': request,
        })
        self._driver_queue.append(work_to_do)
        self._server_responses[request_id] = pkcollections.Dict({
            'send': server_send,
            'reply_sent': reply_sent,
        })
        await reply_sent.wait()
        del self._server_responses[request_id]
