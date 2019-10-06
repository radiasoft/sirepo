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
from sirepo import job
from sirepo import job_supervisor
import asyncio
import os.path
import signal
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket


def default_command():
    cfg = pkconfig.init(
        debug=(pkconfig.channel_in('dev'), bool, 'whether or not to run the job server in debug mode'),
        ip=(job.DEFAULT_IP, str, 'ip address for the job server to listen to'),
        port=(job.DEFAULT_PORT, int, 'port for the job server to listen to'),
    )
    app = tornado.web.Application(
        [
            (job.AGENT_URI, _AgentMsg),
            (job.SERVER_URI, _ServerReq),
        ],
        debug=cfg.debug,
    )
    server = tornado.httpserver.HTTPServer(app)
    server.listen(cfg.port, cfg.ip)
    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)

    pkdlog('Server listening on {}:{}', cfg.ip, cfg.port)
    job_supervisor.init()
    tornado.ioloop.IOLoop.current().start()


class _AgentMsg(tornado.websocket.WebSocketHandler):
    sr_req_type = 'message'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialized by DriverBase.set_message_handler
        self.driver = None

    def check_origin(self, origin):
        return True

    def on_close(self):
        try:
            if self.driver:
                self.driver.on_close()
        except Exception as e:
            pkdlog('Error: {} \n{}', e, pkdexc())

    async def on_message(self, msg):
        await _process_incoming(msg, self)

    def open(self):
        pkdlog(self.request.uri)


async def _process_incoming(content, handler):
    await job_supervisor.process_incoming(
        pkjson.load_any(content),
        handler,
    )


class _ServerReq(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ["POST"]
    sr_req_type = 'request'

    def on_connection_close(self):
        # TODO(e-carlin): Handle this. This occurs when the client drops the connection.
        # See: https://github.com/tornadoweb/tornado/blob/master/demos/chat/chatdemo.py#L106
        # and: https://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.on_connection_close
        pass

    async def post(self):
        await _process_incoming(self.request.body, self)

    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json; charset="utf-8"')


def _sigterm(num, bar):
    tornado.ioloop.IOLoop.current().add_callback_from_signal(_terminate)


def _terminate():
    job_supervisor.terminate()
    tornado.ioloop.IOLoop.current().stop()
