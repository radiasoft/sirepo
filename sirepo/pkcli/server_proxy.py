# -*- coding: utf-8 -*-
"""proxy requests to server

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkconfig
import sirepo.job
import sirepo.util
import signal

cfg = None


def default_command():
    global cfg

    cfg = pykern.pkconfig.init(
        debug=(pkconfig.channel_in("dev"), bool, "run supervisor in debug mode"),
        ip=(sirepo.job.DEFAULT_IP, str, "ip to listen on"),
        port=(sirepo.job.DEFAULT_PORT + 1, int, "what port to listen on"),
    )
    app = tornado.web.Application(
        [
            ("/react-ws", _GUIMsg),
        ],
        debug=cfg.debug,
        websocket_max_message_size=sirepo.job.cfg.max_message_bytes,
        websocket_ping_interval=sirepo.job.cfg.ping_interval_secs,
        websocket_ping_timeout=sirepo.job.cfg.ping_timeout_secs,
    )
    if cfg.debug:
        for f in sirepo.util.files_to_watch_for_reload("json", "py"):
            tornado.autoreload.watch(f)

    s = tornado.httpserver.HTTPServer(
        app,
        xheaders=True,
        max_buffer_size=sirepo.job.cfg.max_message_bytes,
    )
    s.listen(cfg.port, cfg.ip)
    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)
    pkdlog("ip={} port={}", cfg.ip, cfg.port)
    tornado.ioloop.IOLoop.current().start()


def _sigterm(signum, frame):
    tornado.ioloop.IOLoop.current().add_callback_from_signal(_terminate)
