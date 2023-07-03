# -*- coding: utf-8 -*-
"""Test simulationSerial

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_home_page_file(fc):
    from pykern.pkunit import pkeq, pkre
    from pykern.pkdebug import pkdp
    import asyncio

    r = fc.sr_get("/")
    pkeq(200, r.status_code)
    asyncio.run(_run(fc))


async def _run(fc):
    from pykern.pkdebug import pkdp
    from tornado import websocket, httpclient
    from pykern import pkjson
    import asyncio
    import requests

    def _msg(msg):
        pkdp(msg)

    r = requests.Request(
        method="GET",
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
            dict(
                uri="/robots.txt",
                method="GET",
            )
        ),
    ),
    await asyncio.sleep(3)
    assert 0
