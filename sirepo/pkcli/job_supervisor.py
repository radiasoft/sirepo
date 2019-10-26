# -*- coding: utf-8 -*-
"""Runs job supervisor tornado server

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdc
from sirepo import job
from sirepo import job_driver
from sirepo import job_supervisor
import asyncio
import signal
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket

cfg = None


def default_command():
    global cfg

    cfg = pkconfig.init(
        debug=(pkconfig.channel_in('dev'), bool, 'run supervisor in debug mode'),
        ip=(job.DEFAULT_IP, str, 'ip address to listen on'),
        port=(job.DEFAULT_PORT, int, 'what port to listen on'),
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
    pkdlog('ip={} port={}', cfg.ip, cfg.port)
    job_supervisor.init()
    tornado.ioloop.IOLoop.current().start()


class _AgentMsg(tornado.websocket.WebSocketHandler):
    sr_class = job_driver.AgentMsg

    def check_origin(self, origin):
        return True

    def on_close(self):
        try:
            d = getattr(self, 'sr_driver', None)
            if d:
                del self.sr_driver
                d.websocket_on_close()
        except Exception as e:
            pkdlog('error={} {}', e, pkdexc())

    async def on_message(self, msg):
        await _incoming(msg, self)

    def open(self):
        pkdlog(self.request.uri)

    def sr_driver_set(self, driver):
        self.sr_driver = driver


async def _incoming(content, handler):
    try:
        c = pkjson.load_any(content)
        pkdc('class={} content={}', handler.sr_class, job.LogFormatter(c))
        await handler.sr_class(handler=handler, content=c).receive()
    except Exception as e:
        pkdlog('exception={} handler={} content={}', e, content, handler)
        pkdlog(pkdexc())
        getattr(handler, 'close', handler.send_error)()


class _ServerReq(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ["POST"]
    sr_class = job_supervisor.ServerReq

    def on_connection_close(self):
        # TODO(e-carlin): Handle this. This occurs when the client drops the connection.
        # See: https://github.com/tornadoweb/tornado/blob/master/demos/chat/chatdemo.py#L106
        # and: https://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.on_connection_close
        pass

    async def post(self):
        await _incoming(self.request.body, self)

    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json; charset="utf-8"')


def _sigterm(signum, frame):
        tornado.ioloop.IOLoop.current().add_callback_from_signal(_terminate)


def _terminate():
    job_supervisor.terminate()
    tornado.ioloop.IOLoop.current().stop()
