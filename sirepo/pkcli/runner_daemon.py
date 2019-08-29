# -*- coding: utf-8 -*-
"""The runner daemon.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

from functools import partial
from hypercorn.config import Config
from hypercorn.trio import serve
from pykern.pkdebug import pkdp
import trio


def main():
    config = Config()
    config.bind = ['localhost:8080']
    trio.run(partial(serve, _app, config))

async def _handle_scope_type_lifespan(receive, send):
    async def _handle_complete(action):
        await send({'type': f'{action}.complete'})

    message = await receive()
    message_type = message['type']
    message_types = {
        'lifespan.startup': _handle_complete,
        'lifespan.shutdown': _handle_complete,
    }

    await message_types[message_type](message_type)


async def _handle_scope_type_http(receive, send):
    pkdp('In http scope handler')
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'text/plain'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': b'evan',
    })
    pass

async def _app(scope, receive, send):
    pkdp(f'Scopes are {scope}')
    scope_types = {
        'lifespan': _handle_scope_type_lifespan,
        'http': _handle_scope_type_http,
    }
    await scope_types[scope['type']](receive, send)


def _build_response(request):
    pkdp('Server received: {!r}'.format(request))
    return b'hello'