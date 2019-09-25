# -*- coding: utf-8 -*-
"""# TODO(e-carlin): Doc 

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
# TODO(e-carlin): load dynamically
from sirepo.driver import local
import asyncio
import os.path
import signal
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
        debug=(pkconfig.channel_in('dev'), bool, 'whether or not to run the job server in debug mode'),
        ip=(job.DEFAULT_IP, str, 'ip address for the job server to listen to'),
        port=(job.DEFAULT_PORT, int, 'port for the job server to listen to'),
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
    signal.signal(signal.SIGTERM, _terminate)
    signal.signal(signal.SIGINT, _terminate)

    pkdlog('Server listening on {}:{}', cfg.ip, cfg.port)
    tornado.ioloop.IOLoop.current().start()

def _terminate(num, bar):
    if pkconfig.channel_in('dev'):
        for d in driver.DriverBase.driver_for_agent.values():
            if type(d) == local.LocalDriver and d.agent_started:
                d.terminate_agent()
    tornado.ioloop.IOLoop.current().stop()

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
        try:
            await _process_incoming('message', msg, self)
        except Exception as e:
            # TODO(e-carlin): More handling. Ex restart agent
            pkdlog('Error: {}', e)
            pkdp(pkdexc())
            raise


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
        try:
            await _process_incoming('request', self.request.body, self)
        except Exception as e:
            # TODO(e-carlin): More handling.
            pkdlog('Error: {}', e)
            pkdp(pkdexc())
            raise

    def on_connection_close(self):
        #TODO(e-carlin): Handle this. This occurs when the client drops the connection.
        # See: https://github.com/tornadoweb/tornado/blob/master/demos/chat/chatdemo.py#L106
        # and: https://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.on_connection_close
        pass
