# -*- coding: utf-8 -*-
"""proxy test

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_1():
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc, pkdformat
    import tornado.gen
    import tornado.httpclient
    import tornado.websocket

    ws = await tornado.websocket.websocket_connect(
        tornado.httpclient.HTTPRequest(
            url=cfg.supervisor_uri,
            validate_cert=False,
        ),
    )
    ioloop = tornado.ioloop.IOLoop.current()
    send_queue = []
    expected_reads = []

    def _fail(msg):
        nonlocal error
        ioloop.stop()
        error = msg

    async def _reader():
        while True:
            r = await ws.read_message()
            if r is None:
                pkdlog("websocket closed")
                raise tornado.iostream.StreamClosedError()
            if r not in expected_reads:
                return _fail(ioloop, f"message={r} not expected_reads={expected_reads}")

    async def _sender():
        while send_queue and expected_reads:
            await ws.write_message(send_queue.pop(0))
            await tornado.gen.sleep(1)

    async def _watchdog():
        while True:
            await tornado.gen.sleep(1)
            if not send_queue and not expected_reads:
                # PASS
                ioloop.stop()
                return

    ioloop.spawn_callback(_reader)
    ioloop.spawn_callback(_sender)
    ioloop.spawn_callback(_watchdog)
    ioloop.start()
