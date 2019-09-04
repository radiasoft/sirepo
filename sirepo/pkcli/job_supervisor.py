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

ACTION_NO_OP = 'no_op'

_USER_TO_DRIVER_LOOKUP = {}
_DRIVER_CLIENTS = {}

_NURSERY = None

def start():
    trio.run(_initialize)

async def _initialize():
    config = Config()
    config.bind = ['0.0.0.0:8080']
    config.keep_alive_timeout = 20 #TODO(e-carlin): This delays closing the connection in long-polling. Find the right number.
    global _NURSERY 
    async with trio.open_nursery() as _NURSERY:
        await serve(_app, config)


async def _app(scope, receive, send):
    client = scope['client']
    pkdp(f'New call to _app. scope.client: {client}')
    scope_types = {
        'lifespan': _handle_scope_type_lifespan,
        'http': _handle_scope_type_http,
    }
    await scope_types[scope['type']](receive, send)

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

async def _process_request_body(body, send):
    source_types = {
        'server': _process_server_request,
        'driver': _process_driver_request,
    }

    await source_types[body['source']](body, send)

async def _process_driver_request(body, send):
    pkdlog(f'Processing request from driver. Body: {body}')
    driver_id = body.driver_id
    #TODO(e-carlin): Hmmm 
    if driver_id not in _DRIVER_CLIENTS:
        _create_driver_client(driver_id, _NURSERY)

    driver = _DRIVER_CLIENTS[driver_id]
    driver.send = send


async def _process_server_request(body, send):
    if body.uid not in _DRIVER_CLIENTS:
        #TODO(e-carlin): Actually start the driver 
        _create_driver_client(body.uid, _NURSERY)
    
    driver = _DRIVER_CLIENTS[body.uid]
    driver.driver_queue.append(body)
    await driver.wait_for_server_send.park()
    pkdp('Done with park')

def _action_ready_for_work(request):
    # pkdp(f'Agent is ready for work')
    # if _JOB_TRACKER['driver_request']
    # if _WORK_QUEUE:
    #     action = _WORK_QUEUE.popleft()
    #     return action
    # else:
    #     pkdp('Action is no_op')
    #     return {
    #         'action': ACTION_NO_OP,
    #     }
    pass

def _create_driver_client(uid, nursery):
    driver = _DriverClient(nursery)
    driver.start()
    _DRIVER_CLIENTS[uid] = driver

#TODO(e-carlin): Better name for this class
class _DriverClient():
    def __init__(self, nursery):
        self.driver_queue = deque([])
        self.server_queue = deque([])
        self.driver_send = None
        self.server_send = None
        self.wait_for_server_send = trio.hazmat.ParkingLot()

        self._nursery = nursery

    def start(self):
        self._nursery.start_soon(self._process_driver_queue)

    async def _process_driver_queue(self):
        while True:
            if self.driver_send and  self.driver_queue:
                work_to_do = self.driver_queue.popleft()
                try:
                    await self._send_to_driver(work_to_do)
                except Exception as e:
                    pkdlog(f'Exception while proccessing driver queue. Caused by: {e}')
                    pkdexc()
                    self.driver_queue.appendleft(work_to_do)
            await trio.sleep(1) #TODO(e-carlin): What should we really do in the case where there is nothing to do?

    async def _send_to_driver(self, body):
        #TODO(e-carlin): Same code as send_to_server. Abstract.
        pkdp(f'Sending to driver: {body}')
        await _http_send(body, self.driver_send)
        #TODO(e-carlin): Race condition. The self.driver_send could have been 
        # changed between _http_send() and this clear? Maybe not because we
        # are only holding one driver connection at a time
        self.driver_send = None # After send clear out the current send object so we wait for the next one
    

    
