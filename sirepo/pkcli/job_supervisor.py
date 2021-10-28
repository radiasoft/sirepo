# -*- coding: utf-8 -*-
"""Runs job supervisor tornado server

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdc
import asyncio
import functools
import signal
import sirepo.events
import sirepo.job
import sirepo.job_driver
import sirepo.job_supervisor
import sirepo.sim_db_file
import sirepo.srdb
import sirepo.srtime
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket

cfg = None


def default_command():
    global cfg

    cfg = pkconfig.init(
        debug=(pkconfig.channel_in('dev'), bool, 'run supervisor in debug mode'),
        ip=(sirepo.job.DEFAULT_IP, str, 'ip to listen on'),
        port=(sirepo.job.DEFAULT_PORT, int, 'what port to listen on'),
    )
    sirepo.srtime.init()
    sirepo.job_supervisor.init()
    pkio.mkdir_parent(sirepo.job.DATA_FILE_ROOT)
    pkio.mkdir_parent(sirepo.job.LIB_FILE_ROOT)
    app = tornado.web.Application(
        [
            (sirepo.job.AGENT_URI, _AgentMsg),
            (sirepo.job.SERVER_URI, _ServerReq),
            (sirepo.job.SERVER_RUN_MULTI_URI, _ServerReqRunMulti),
            (sirepo.job.SERVER_PING_URI, _ServerPing),
            (sirepo.job.SERVER_SRTIME_URI, _ServerSrtime),
            (sirepo.job.DATA_FILE_URI + '/(.*)', _DataFileReq),
            (sirepo.job.SIM_DB_FILE_URI + '/(.+)', sirepo.sim_db_file.FileReq),
        ],
        debug=cfg.debug,
        static_path=sirepo.job.SUPERVISOR_SRV_ROOT.join(sirepo.job.LIB_FILE_URI),
        # tornado expects a trailing slash
        static_url_prefix=sirepo.job.LIB_FILE_URI + '/',
        websocket_max_message_size=sirepo.job.cfg.max_message_bytes,
        websocket_ping_interval=sirepo.job.cfg.ping_interval_secs,
        websocket_ping_timeout=sirepo.job.cfg.ping_timeout_secs,
    )
    server = tornado.httpserver.HTTPServer(
        app,
        xheaders=True,
        max_buffer_size=sirepo.job.cfg.max_message_bytes,
    )
    server.listen(cfg.port, cfg.ip)
    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)
    pkdlog('ip={} port={}', cfg.ip, cfg.port)
    tornado.ioloop.IOLoop.current().start()


class _AgentMsg(tornado.websocket.WebSocketHandler):
    sr_class = sirepo.job_driver.AgentMsg

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
        pkdlog(
            'uri={} remote_ip={} ',
            self.request.uri,
            self.request.remote_ip,
        )

    def sr_close(self):
        """Close socket and does not call on_close

        Unsets driver to avoid a callback loop.
        """
        if hasattr(self, 'sr_driver'):
            del self.sr_driver
        self.close()

    def sr_driver_set(self, driver):
        self.sr_driver = driver

    def sr_on_exception(self):
        self.on_close()
        self.close()


class _JsonPostRequestHandler(tornado.web.RequestHandler):

    def set_default_headers(self):
        self.set_header("Content-Type", 'application/json; charset="utf-8"')


class _ServerPing(_JsonPostRequestHandler):

    async def post(self):
        r = pkjson.load_any(self.request.body)
        self.write(r.pkupdate(state='ok'))


class _ServerReq(_JsonPostRequestHandler):
    sr_class = sirepo.job_supervisor.ServerReq

    def on_connection_close(self):
        # Nothing we can do with the request. Even if a user
        # closes a browser or laptop, we will want to continue with
        # the simulation run request. Only in specific cases would
        # we want to terminate processing, but that cancel problem is
        # quite hard, and not likely we are consuming too many resources.
        #
        # By not having a connection to supervisor (for on_close), we
        # avoid data structure loops.
        pass

    async def post(self):
        self.write(await _incoming(self.request.body, self))

    def sr_on_exception(self):
        self.send_error()
        self.on_connection_close()

class _ServerSrtime(_JsonPostRequestHandler):

    def post(self):
        assert pkconfig.channel_in_internal_test(), \
            'You can only adjust time in internal test'
        sirepo.srtime.adjust_time(pkjson.load_any(self.request.body).days)
        self.write(PKDict())


class _ServerReqRunMulti(_ServerReq):

    async def post(self):
        b = pkjson.load_any(self.request.body)
        futures = []
        for m in b.data:
            i = functools.partial(
                _incoming,
                m.pkupdate(serverSecret=b.serverSecret, api=m.data.api),
                self,
            )
            if m.data.get('awaitReply'):
                futures.append(i())
                continue
            tornado.ioloop.IOLoop.current().add_callback(i)
        r = PKDict()
        if futures:
            r.pkupdate(
                data=await asyncio.gather(*futures, return_exceptions=True),
            )
        self.write(r)


async def _incoming(content, handler):
    try:
        c = content
        if not isinstance(content, dict):
            c = pkjson.load_any(content)
        if c.get('api') != 'api_runStatus':
            pkdc(
                'class={} content={}',
                handler.sr_class,
                c,
            )
        return await handler.sr_class(handler=handler, content=c).receive()
    except Exception as e:
        pkdlog(
            'exception={} handler={} content={}',
            e,
            handler,
            content
        )
        pkdlog(pkdexc())
        try:
            handler.sr_on_exception()
        except Exception as e:
            pkdlog('sr_on_exception: exception={}', e)


def _sigterm(signum, frame):
    tornado.ioloop.IOLoop.current().add_callback_from_signal(_terminate)


class _DataFileReq(tornado.web.RequestHandler):

    async def put(self, path):
        # should be exactly two levels
        (d, f) = path.split('/')
        assert sirepo.job.UNIQUE_KEY_RE.search(d), \
            'invalid directory={}'.format(d)
        d = sirepo.job.DATA_FILE_ROOT.join(d)
        assert d.check(dir=True), \
            'directory does not exist={}'.format(d)
        # (tornado ensures no '..' and '.'), but a bit of sanity doesn't hurt
        assert not f.startswith('.'), \
            'invalid file={}'.format(f)
        d.join(f).write_binary(self.request.body)


async def _terminate():
    try:
        await sirepo.job_supervisor.terminate()
    except Exception as e:
        pkdlog('error={} stack={}', e, pkdexc())
    tornado.ioloop.IOLoop.current().stop()
