"""Runs job supervisor tornado server

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc, pkdc
import asyncio
import signal
import sirepo.const
import sirepo.events
import sirepo.feature_config
import sirepo.global_resources.api
import sirepo.http_util
import sirepo.job
import sirepo.job_driver
import sirepo.job_supervisor
import sirepo.modules
import sirepo.sim_db_file
import sirepo.srdb
import sirepo.srtime
import sirepo.util
import tornado.autoreload
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.websocket

_cfg = None


def default_command():
    global _cfg

    _cfg = pkconfig.init(
        debug=(
            sirepo.feature_config.cfg().debug_mode,
            bool,
            "run supervisor in debug mode",
        ),
        ip=(sirepo.job.DEFAULT_IP, str, "ip to listen on"),
        port=(sirepo.const.PORT_DEFAULTS.supervisor, int, "what port to listen on"),
        use_reloader=(pkconfig.in_dev_mode(), bool, "use the server reloader"),
    )
    sirepo.modules.import_and_init("sirepo.job_supervisor")
    pkio.mkdir_parent(sirepo.job.DATA_FILE_ROOT)
    app = tornado.web.Application(
        [
            (sirepo.job.AGENT_URI, _AgentMsg),
            (sirepo.job.SERVER_URI, _ServerReq),
            (sirepo.job.SERVER_PING_URI, _ServerPing),
            (sirepo.job.SERVER_SRTIME_URI, _ServerSrtime),
            (sirepo.job.DATA_FILE_URI + "/(.*)", _DataFileReq),
            (sirepo.job.SIM_DB_FILE_URI + "/(.+)", sirepo.sim_db_file.SimDbServer),
            (sirepo.job.GLOBAL_RESOURCES_URI, sirepo.global_resources.api.Req),
        ],
        debug=_cfg.debug,
        websocket_max_message_size=sirepo.job.cfg().max_message_bytes,
        websocket_ping_interval=sirepo.job.cfg().ping_interval_secs,
        websocket_ping_timeout=sirepo.job.cfg().ping_timeout_secs,
    )
    if _cfg.use_reloader:
        for f in sirepo.util.files_to_watch_for_reload("json", "py"):
            tornado.autoreload.watch(f)
    server = tornado.httpserver.HTTPServer(
        app,
        xheaders=True,
        max_buffer_size=sirepo.job.cfg().max_message_bytes,
    )
    server.listen(_cfg.port, _cfg.ip)
    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)
    pkdlog("ip={} port={}", _cfg.ip, _cfg.port)
    tornado.ioloop.IOLoop.current().start()


class _AgentMsg(tornado.websocket.WebSocketHandler):
    sr_class = sirepo.job_driver.AgentMsg

    def on_close(self):
        try:
            d = getattr(self, "sr_driver", None)
            if d:
                del self.sr_driver
                d.websocket_on_close()
        except Exception as e:
            pkdlog("error={} {}", e, pkdexc())

    def on_message(self, msg):
        # WebSocketHandler only allows one on_message at a time.
        asyncio.create_task(_incoming(msg, self))

    def open(self):
        pkdlog(
            "uri={} remote_ip={} ",
            self.request.uri,
            sirepo.http_util.remote_ip(self.request),
        )

    def sr_close(self):
        """Close socket and does not call on_close

        Unsets driver to avoid a callback loop.
        """
        if hasattr(self, "sr_driver"):
            del self.sr_driver
        self.close()

    def sr_driver_set(self, driver):
        self.sr_driver = driver

    def sr_on_exception(self):
        self.on_close()
        self.close()


class _JsonPostRequestHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header("Content-Type", pkjson.CONTENT_TYPE)


class _ServerPing(_JsonPostRequestHandler):
    async def post(self):
        r = pkjson.load_any(self.request.body)
        self.write(r.pkupdate(state="ok"))


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
        if (r := await _incoming(self.request.body, self)) is not None:
            self.write(r)

    def sr_on_exception(self):
        self.send_error()
        self.on_connection_close()


class _ServerSrtime(_JsonPostRequestHandler):
    async def post(self):
        assert (
            pkconfig.channel_in_internal_test()
        ), "You can only adjust time in internal test"
        sirepo.srtime.adjust_time(pkjson.load_any(self.request.body).days)
        self.write(PKDict())


async def _incoming(content, handler):
    try:
        c = content
        if not isinstance(content, dict):
            c = pkjson.load_any(content)
        if c.get("api") != "api_runStatus":
            pkdc(
                "class={} content={}",
                handler.sr_class,
                c,
            )
        return await handler.sr_class(handler=handler, content=c).receive()
    except Exception as e:
        pkdlog("exception={} handler={} content={}", e, handler, content)
        pkdlog(pkdexc())
        try:
            handler.sr_on_exception()
        except Exception as e:
            pkdlog("sr_on_exception: exception={}", e)
        # sr_on_exception writes error
        return None


def _sigterm(signum, frame):
    tornado.ioloop.IOLoop.current().add_callback_from_signal(_terminate)


class _DataFileReq(tornado.web.RequestHandler):
    async def put(self, path):
        # should be exactly two levels
        (d, f) = path.split("/")
        assert sirepo.util.UNIQUE_KEY_RE.search(d), "invalid directory={}".format(d)
        d = sirepo.job.DATA_FILE_ROOT.join(d)
        assert d.check(dir=True), "directory does not exist={}".format(d)
        # (tornado ensures no '..' and '.'), but a bit of sanity doesn't hurt
        assert not f.startswith("."), "invalid file={}".format(f)
        d.join(f).write_binary(self.request.body)


async def _terminate():
    try:
        await sirepo.job_supervisor.terminate()
    except Exception as e:
        pkdlog("error={} stack={}", e, pkdexc())
    tornado.ioloop.IOLoop.current().stop()
