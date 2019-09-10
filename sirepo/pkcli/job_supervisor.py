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

_DRIVER_CLIENTS = {} #TODO(e-carlin): What data structure should we really use?


class _ReqHandler(tornado.web.RequestHandler):
    SUPPORTED_METHODS = ["POST"]

    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json; charset="utf-8"')

    async def post(self):
        req = pkjson.load_any(self.request.body)
        #TODO(e-carlin): This is ugly
        pkdlog('Received request: {}',  {x: req[x] for x in req if x not in ['result', 'arg']})
        pkdc('Full request body: {}', req)

        driver_client = _create_driver_client_if_not_found(req.uid)
        await driver_client.process_request(req, self.write)

    def on_connection_close(self):
        #TODO(e-carlin): Handle this. This occurs when the client drops the connection.
        # See: https://github.com/tornadoweb/tornado/blob/master/demos/chat/chatdemo.py#L106
        # and: https://www.tornadoweb.org/en/stable/web.html#tornado.web.RequestHandler.on_connection_close
        pass


def start():
    app = tornado.web.Application(
        [
            (r"/", _ReqHandler),
        ],
        debug=cfg.debug,
    )
    server = tornado.httpserver.HTTPServer(app)
    server.listen(cfg.port, cfg.ip)
    pkdlog('Server listening on {}:{}', cfg.ip, cfg.port)
    tornado.ioloop.IOLoop.current().start()


def _create_driver(uid):
    #TODO(e-carlin): Make this way more robust
    cmd = ['sirepo', 'job_driver', 'start', uid]
    tornado.process.Subprocess(cmd)


def _create_driver_client_if_not_found(uid):
    if uid not in _DRIVER_CLIENTS:
        _create_driver(uid) #TODO(e-carlin): Creating driver should maybe be part of creating driver_client
        driver_client = _DriverClient()
        _DRIVER_CLIENTS[uid] = driver_client

    return _DRIVER_CLIENTS[uid]


class _DriverClient():
    def __init__(self):
        self._driver_work_q = tornado.queues.Queue()
        self._server_responses = {} #TODO(e-carlin): I'd like to use pkcollections.Dict() but it prevents delete. Why is that?

    async def process_request(self, req, reply_writer):
        source = req.action.split('_')[0]
        await getattr(self, f'process_{source}_request')(req, reply_writer)
        

    async def process_driver_request(self, request, send_to_driver):
        pkdc('Processing driver request. Request: {}', request)

        # Driver is ready for work. Give it work when we have some.
        if request.action == job.ACTION_DRIVER_READY_FOR_WORK:
            work_to_do = await self._driver_work_q.get()
            pkdc('Received work item for driver. Sending to driver. Work: {}', work_to_do)
            #TODO(e-carlin): Handle errors.
            _http_send(work_to_do, send_to_driver)
            self._driver_work_q.task_done()
            return

        # Driver has the results of work. Send them to the server.
        pkdc('Sending driver results to server: {}', request)
        server_reply = self._server_responses[request.request_id]
        _http_send(request, server_reply.send)
        assert not server_reply.reply_sent.is_set()
        server_reply.reply_sent.set()
        _http_send({}, send_to_driver)
        return

    async def process_srserver_request(self, request, send_to_server):
        pkdc('Processing server request. Request: {}', request)
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


def _http_send(body, write):
        write(pkjson.dump_bytes(body))

cfg = pkconfig.init(
    debug=(True, bool, 'whether or not to run the supervisor tornado server in debug mode'),
    ip=(job.DEFAULT_IP, str, 'ip address for the supervisor tornado server to listen to'),
    port=(job.DEFAULT_PORT, int, 'port for the supervisor tornado server to listen to')
)