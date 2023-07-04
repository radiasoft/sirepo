# -*- coding: utf-8 -*-
"""Test uri_router websocket requests

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


@pytest.mark.asyncio
async def test_robots_txt(fc):
    from pykern import pkjson, pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from tornado import websocket, httpclient
    import asyncio
    import requests

    reply_event = asyncio.Event()

    def _msg(msg):
        m = pkjson.load_any(msg)
        pkunit.pkeq(1, m.req_seq)
        pkunit.pkre("/srw", m.content)
        reply_event.set()

    r = fc.sr_get("/")
    pkunit.pkeq(200, r.status_code)
    r = requests.Request(
        url=fc.http_prefix + "/ws",
    ).prepare()
    s = await websocket.websocket_connect(
        httpclient.HTTPRequest(
            url=r.url.replace("http", "ws"),
            headers=r.headers,
        ),
        on_message_callback=_msg,
    )
    await s.write_message(
        pkjson.dump_pretty(PKDict(req_seq=1, uri="/robots.txt")),
    )
    await asyncio.wait_for(reply_event.wait(), 2)


@pytest.mark.asyncio
async def test_existing_auth(fc):
    from pykern import pkjson, pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from tornado import websocket, httpclient
    import asyncio
    import requests
    from sirepo import srunit

    reply_event = asyncio.Event()

    def _msg(msg):
        if msg is None:
            # msg is None on close
            return
        m = pkjson.load_any(msg)
        pkunit.pkeq(1, m.req_seq)
        c = pkjson.load_any(m.content)
        pkunit.pkeq(srunit.SR_SIM_NAME_DEFAULT, c[0].name)
        reply_event.set()

    fc.sr_sim_data()
    r = requests.Request(
        url=fc.http_prefix + "/ws",
        cookies=fc.cookie_jar,
    ).prepare()
    s = await websocket.websocket_connect(
        httpclient.HTTPRequest(
            url=r.url.replace("http", "ws"),
            headers=r.headers,
        ),
        on_message_callback=_msg,
    )
    await s.write_message(
        pkjson.dump_pretty(
            PKDict(
                req_seq=1,
                uri="/simulation-list",
                content=PKDict(simulationType=fc.sr_sim_type),
            ),
        ),
    )
    try:
        await asyncio.wait_for(reply_event.wait(), 2)
    finally:
        s.close()
