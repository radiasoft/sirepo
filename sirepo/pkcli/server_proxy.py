# -*- coding: utf-8 -*-
"""proxy requests to server

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkconfig
import signal
import sirepo.job
import sirepo.util
import tornado.autoreload
import tornado.httpserver
import tornado.ioloop
import tornado.web


_cfg = None


def default_command():
    global _cfg

    _cfg = pykern.pkconfig.init(
        debug=(pykern.pkconfig.channel_in("dev"), bool, "run supervisor in debug mode"),
        ip=(sirepo.job.DEFAULT_IP, str, "ip to listen on"),
        port=(sirepo.job.DEFAULT_PORT + 1, int, "what port to listen on"),
    )
    app = tornado.web.Application(
        [
            ("/.*", _HTTP),
            ("/react-ws", _WebSocket),
        ],
        debug=cfg.debug,
        websocket_max_message_size=sirepo.job.cfg().max_message_bytes,
        websocket_ping_interval=sirepo.job.cfg().ping_interval_secs,
        websocket_ping_timeout=sirepo.job.cfg().ping_timeout_secs,
    )
    if _cfg.debug:
        for f in sirepo.util.files_to_watch_for_reload("json", "py"):
            tornado.autoreload.watch(f)

    s = tornado.httpserver.HTTPServer(
        app,
        xheaders=True,
        max_buffer_size=sirepo.job.cfg().max_message_bytes,
    )
    s.listen(_cfg.port, _cfg.ip)
    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)
    pkdlog("ip={} port={}", _cfg.ip, _cfg.port)
    tornado.ioloop.IOLoop.current().start()

    # messages go to a session which tracks what the browser window is doing
    # could open multiple websockets to have big and small responses/requests
    # msgpack is necessary for binary; consider utf8 vs 16

    # write a client in python that makes requests for testing


class _HTTP(tornado.web.RequestHandler):
    # handles all requests and forwards them to the server
    # with cookie copy.

    # we do not need to look inside the cookie except to validate the
    # cookie on the web socket so we can get the uid. Perhaps that could
    # be gotten with authUserState request on the open to the websocket.

    # The websocket needs to be closed at some point if the user auth
    # changes (user deleted). Perhaps that's an inactivity thing.  Or
    # a session-based thing.
    pass


class _WebSocket(tornado.websocket.WebSocketHandler):
    sr_class = sirepo.job_driver.AgentMsg

    def check_origin(self, origin):
        return True

    def on_close(self):
        try:
            d = getattr(self, "sr_driver", None)
            if d:
                del self.sr_driver
                d.websocket_on_close()
        except Exception as e:
            pkdlog("error={} {}", e, pkdexc())

    async def on_message(self, msg):
        await _incoming(msg, self)

    def open(self):
        pkdlog(
            "uri={} remote_ip={} cookies={}",
            self.request.uri,
            self.request.remote_ip,
            self.request.cookies,
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


def _sigterm(signum, frame):
    tornado.ioloop.IOLoop.current().add_callback_from_signal(_terminate)
