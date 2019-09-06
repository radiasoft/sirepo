# -*- coding: utf-8 -*-
"""TODO(e-carlin): Doc

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


from pykern import pkcollections
from pykern import pkjson
from pykern.pkdebug import pkdp, pkdlog, pkdexc
import asyncio
import os.path
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.locks
import tornado.options
import tornado.queues
import tornado.web
import uuid


tornado.options.define("port", default=8888, help="run on the given port", type=int)
tornado.options.define("debug", default=True, help="run in debug mode")


_BROKERS = {}


class RequestHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ["POST"]

    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    async def post(self):
        body = pkcollections.Dict(pkjson.load_any(self.request.body))
        pkdlog(f'Received request: {body}')

        source_types = ['server', 'driver']
        assert body.source in source_types

        broker = _create_broker_if_not_found(body.uid)
        process_fn = getattr(broker, f'process_{body.source}_request')
        await process_fn(body, self.write)
        return

    def on_connection_close(self):
        #TODO(e-carlin): Handle this. This occurs when the client drops the connection.
        # See: https://github.com/tornadoweb/tornado/blob/master/demos/chat/chatdemo.py#L106
        # and: https://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.on_connection_close
        pass


def start():
    tornado.options.parse_command_line()
    app = tornado.web.Application(
        [
            (r"/", RequestHandler),
        ],
        debug=tornado.options.options.debug,
    )
    server = tornado.httpserver.HTTPServer(app)
    port = tornado.options.options.port
    server.listen(port)
    pkdlog('Server listening on port {}', port)
    tornado.ioloop.IOLoop.current().start()

class _Broker():
    def __init__(self):
        self._driver_work_q = tornado.queues.Queue()
        self._server_responses = {} #TODO(e-carlin): I'd like to use pkcollections.Dict() but it prevents delete. Why is that?

    async def process_driver_request(self, request, send_to_driver):
        pkdlog(f'Processing driver request. Request: {request}')

        # Driver is ready for work. Give it work when we have some.
        if request.action == 'ready_for_work':
            work_to_do = await self._driver_work_q.get()
            pkdlog('Received work item for driver. Sending to driver. Work: {!r}'.format(work_to_do))
            #TODO(e-carlin): Handle errors the message should be put on some other q to be handled
            _http_send(work_to_do, send_to_driver)
            self._driver_work_q.task_done()
            return

        # Driver has the results of work. Send them to the server.
        pkdlog(f'Sending driver results to server: {request}')
        server_reply = self._server_responses[request.request_id]
        _http_send(request, server_reply.send)
        assert not server_reply.reply_sent.is_set()
        server_reply.reply_sent.set()
        return

    async def process_server_request(self, request, send_to_server):
        pkdlog(f'Processing server request. Request: {request}')
        reply_sent = tornado.locks.Event()
        request.request_id = str(uuid.uuid4())
        work_to_do = pkcollections.Dict(request)
        self._server_responses[request.request_id] = pkcollections.Dict({
            'send': send_to_server,
            'reply_sent': reply_sent,
        })
        await self._driver_work_q.put(work_to_do)
        await reply_sent.wait()
        del self._server_responses[request.request_id]


def _create_broker_if_not_found(uid):
    assert uid == 'NwfZClof' #TODO(e-carlin): Remove. This is just to catch myself while testing
    if uid not in _BROKERS:
        #TODO(e-carlin): Actually start the driver client
        #TODO(e-carlin): What if two simultaneous requests come in to start the broker? Who wins?
        broker = _Broker()
        _BROKERS[uid] = broker

    return _BROKERS[uid]


def _http_send(body, write):
    try:
        write(pkjson.dump_bytes(body))
    except Exception as e:
        pkdlog('Error while writing to server. Casued by: {}'.format(e))
        pkdlog(pkdexc())
