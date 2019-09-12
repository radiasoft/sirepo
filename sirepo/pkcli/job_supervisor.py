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
from sirepo import job
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
import uuid

from sirepo import driver
import tornado.websocket


class _ReqHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ["POST"]

    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    async def post(self):
        c = pkjson.load_any(self.request.body)
        #TODO(e-carlin): This is ugly
        pkdlog('Received request: {}',  {x: c[x] for x in c if x not in ['result', 'arg']})
        pkdc('Full request body: {}', c)

        r = pkcollections.Dict({
            'request_handler': self,
            'content': c,
        })

        await driver.DriverBase.process_request(r)

    def on_connection_close(self):
        #TODO(e-carlin): Handle this. This occurs when the client drops the connection.
        # See: https://github.com/tornadoweb/tornado/blob/master/demos/chat/chatdemo.py#L106
        # and: https://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.on_connection_close
        pass

class _WSHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        pkdp('open: {}', self.request.uri)
        driver.DriverBase.process_ws_open(self)

    def on_close(self):
        # TODO(e-carlin): Handle this 
        pkdp('on_close: {}', self.request.uri)

    def on_message(self, msg):
        pkdp('received {}', msg)
        self.write_message('received your message')
        pkdp('Done with write')

def start():
    app = tornado.web.Application(
        [   
            # Ordering of handlers is important. Should be most to least specific.
            ('/{}.*'.format(cfg.ws_path), _WSHandler),
            ('/.*', _ReqHandler),
        ],
        debug=cfg.debug,
    )
    server = tornado.httpserver.HTTPServer(app)
    server.listen(cfg.port, cfg.ip)
    pkdlog('Server listening on {}:{}', cfg.ip, cfg.port)
    tornado.ioloop.IOLoop.current().start()


cfg = pkconfig.init(
    debug=(True, bool, 'whether or not to run the supervisor tornado server in debug mode'),
    ip=(job.DEFAULT_IP, str, 'ip address for the supervisor tornado server to listen to'),
    port=(job.DEFAULT_PORT, int, 'port for the supervisor tornado server to listen to'),
    ws_path=(job.DEFAULT_WS_PATH, str, 'path supervisor tornado sever accepts websockets requests on'),
)
