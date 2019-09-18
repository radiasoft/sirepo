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


async def _process_incoming(req_type, content, handler):
#rn name the thing as it is named in the code. Output before handling
# in case there is some type of issue with processing the json so you
# have more context to debug the error.
    pkdc('content={}', c)
    c = pkjson.load_any(content)
    # #TODO(e-carlin): This is ugly
#rn make a renderer object that's lightweight
#  class _DebugRenderer():
#      def __init__(self, obj):
#          self.obj = obj
#
#      def __str__(self):
#rn this defers all the decision making until it needs to be rendered
#          o = self.obj
#          if isinstance(obj, dict) and 'result' in o:
#               return str({x: c[x] for x in o if x not in ['result', 'arg']})
#          raise AssertionError('unknown object to render: {}', o)
#rn it's easier to read if you don't put too much text here. You'll get used to it.
    pkdlog('{}: {}', req_type,  {x: c[x] for x in c if x not in ['result', 'arg']})
#rn "process" is superfluous, could be "x". "r" is better, but in the end,
#  it's better not to hold the state. If you need to debug, say, what "r" is, just
# wrap it in pkdp, e.g. getattr()(pkdp(pkcollections.Dict(...)))
# pkdp returns its first argument if that's all it gets. It's a special case to
# allow you to get debug output without having to put values in an intermediate
# variable, which introduces the possibility of a state issue.
# I know a lot of python does it with lots of variabls, and I've copied that
# style, but I've thought more about it, and I prefer avoiding stateful code.
    await getattr(driver.DriverBase, f'process_{req_type}')(
        pkcollections.Dict({
            f'{req_type}_handler': handler,
            'content': c,
        },
    )


#rn what about just _Req
class _ReqHandler(tornado.web.RequestHandler):
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


#rn I think we might even call this _Message. Perhaps we shoudl
#   bind all classes to URIs. This would be clearer in some ways.
#   This could be _AgentMessage bound to /agent
#   The above could be _ServerReq bound to /server
#   As it is, we may have issues with robots hitting the address
#   and we would process a non-sensical message and get errors in the
#   the logs. We don't need to worry about proxying anything but
#   /agent and /server.
class _WSHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
#rn: it's simpler and will do the right thing
        pkdp(self.request.uri)

    def on_close(self):
        # TODO(e-carlin): Handle this
        # in on_message we should set some state about who we are (ex uid).
        # then when this is called we find the driver instance with that uid
        # and notify it that on_close was called.
#rn
        pkdp(self.request.uri)

    async def on_message(self, msg):
        await _process_incoming('message', msg, self)


#rn i'd like to see this inside start, because it is not needed until there
#  and there is only one invocation.
cfg = pkconfig.init(
    debug=(pkconfig.channel_in('dev'), bool, 'whether or not to run the supervisor tornado server in debug mode'),
    ip=(job.DEFAULT_IP, str, 'ip address for the supervisor tornado server to listen to'),
    port=(job.DEFAULT_PORT, int, 'port for the supervisor tornado server to listen to'),
#rn: this is a uri or "path_info", but uri makes more sense to me
# this doesn't need to be configurable. it's programmatically controlled
    ws_path=(job.DEFAULT_WS_PATH, str, 'path supervisor tornado sever accepts websockets requests on'),
)
