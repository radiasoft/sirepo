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

        driver_client = _get_driver_client(req.uid)
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


def _get_driver_client(uid):
    return _DRIVER_CLIENTS.get(uid) or _DriverClient(uid)


class _DriverClient():
    def __init__(self, uid):
        self._srserver_reqs= tornado.queues.Queue()
        self._srserver_responses = {} #TODO(e-carlin): I'd like to use pkcollections.Dict() but it prevents delete. Why is that?
        self._uid = uid
        
        #TODO(e-carlin): Make this way more robust
        tornado.process.Subprocess(['sirepo', 'job_driver', 'start', self._uid])
        _DRIVER_CLIENTS[self._uid] = self

    async def process_request(self, req, reply_writer):
        source = req.action.split('_')[0]
        await getattr(self, f'_process_{source}_request')(req, reply_writer)

    async def _process_driver_ready_for_work(self, req, write_to_driver):
            r = await self._srserver_reqs.get()
            pkdc('Received work item for driver. Sending to driver. Request: {}', r)
            #TODO(e-carlin): Handle errors.
            _http_send(r, write_to_driver)
            self._srserver_reqs.task_done()

    async def _process_driver_request(self, req, write_to_driver):
        pkdc('Processing driver request. Request: {}', req)

        action_dispatch = {
            job.ACTION_DRIVER_READY_FOR_WORK: self._process_driver_ready_for_work,
        }
        process_fn = action_dispatch.get(req.action) or self._process_driver_results
        await process_fn(req, write_to_driver)
        
    async def _process_driver_results(self, req, write_to_driver):
        pkdc('Sending driver results to server: {}', req)
        server_response = self._srserver_responses[req.id]
        _http_send(req, server_response.write_to_server)
        assert not server_response.reply_was_sent.is_set()
        server_response.reply_was_sent.set()
        _http_send({}, write_to_driver)
        
    async def _process_srserver_request(self, req, write_to_server):
        pkdc('Processing server request. Request: {}', req)
        req.id = str(uuid.uuid4())
        self._srserver_responses[req.id] = pkcollections.Dict({
            'write_to_server': write_to_server,
            'reply_was_sent': tornado.locks.Event(),
        })
        await self._srserver_reqs.put(req)
        await self._srserver_responses[req.id].reply_was_sent.wait()
        del self._srserver_responses[req.id]


def _http_send(body, write):
        write(pkjson.dump_bytes(body))

cfg = pkconfig.init(
    debug=(True, bool, 'whether or not to run the supervisor tornado server in debug mode'),
    ip=(job.DEFAULT_IP, str, 'ip address for the supervisor tornado server to listen to'),
    port=(job.DEFAULT_PORT, int, 'port for the supervisor tornado server to listen to')
)