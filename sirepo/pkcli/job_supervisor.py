# -*- coding: utf-8 -*-
"""Supervisor to manage drivers and the execution of jobs on the drivers.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkjson
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdc
from sirepo import driver
from sirepo import job
from sirepo import job_scheduler
import asyncio
import os.path
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.locks
import tornado.options
import tornado.process
import tornado.queues
import tornado.web
import tornado.websocket
import uuid


def start():
    cfg = pkconfig.init(
        debug=(pkconfig.channel_in('dev'), bool, 'whether or not to run the supervisor tornado server in debug mode'),
        ip=(job.DEFAULT_IP, str, 'ip address for the supervisor tornado server to listen to'),
        port=(job.DEFAULT_PORT, int, 'port for the supervisor tornado server to listen to'),
    )
    app = tornado.web.Application(
        [
            ('/agent', _AgentMsg),
            ('/server', _ServerReq),
        ],
        debug=cfg.debug,
    )
    server = tornado.httpserver.HTTPServer(app)
    server.listen(cfg.port, cfg.ip)
    pkdlog('Server listening on {}:{}', cfg.ip, cfg.port)
    tornado.ioloop.IOLoop.current().start()


class _AgentMsg(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        pkdp(self.request.uri)

    def on_close(self):
        # TODO(e-carlin): Handle this
        # in on_message we should set some state about who we are (ex uid).
        # then when this is called we find the driver instance with that uid
        # and notify it that on_close was called.
        pkdp(self.request.uri)

    async def on_message(self, msg):
        await _process_incoming('message', msg, self)


class _DebugRenderer():
    def __init__(self, obj):
        self.obj = obj

    def __str__(self):
        o = self.obj
        if isinstance(o, pkcollections.Dict):
            return str({x: o[x] for x in o if x not in ['result', 'arg']})
        raise AssertionError('unknown object to render: {}', o)


async def _process_incoming(req_type, content, handler):
    pkdc('req_type={}, content={}', req_type, content)
    c = pkjson.load_any(content)
    pkdlog('{}: {}', req_type,  _DebugRenderer(c))
    await getattr(driver.DriverBase, f'incoming_{req_type}')(
        pkcollections.Dict({
            f'{req_type}_handler': handler,
            'content': c,
        },
    ))


class _ServerReq(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ["POST"]

    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    async def post(self):
        await _process_incoming('request', self.request.body, self)

    def on_connection_close(self):
        #TODO(e-carlin): Handle this. This occurs when the client drops the connection.
        # See: https://github.com/tornadoweb/tornado/blob/master/demos/chat/chatdemo.py#L106
        # and: https://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.on_connection_close
        pass
