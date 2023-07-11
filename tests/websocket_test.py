# -*- coding: utf-8 -*-
"""Test uri_router websocket requests

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


@pytest.mark.asyncio
async def test_error_html(fc):
    from pykern import pkjson, pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from tornado import websocket, httpclient
    import asyncio
    import requests

    reply_event = asyncio.Event()

    def _msg(msg):
        m = pkjson.load_any(msg)
        pkunit.pkeq(1, m.reqSeq)
        pkunit.pkeq("text/html", m.contentType)
        pkunit.pkre("h1>not found", m.content)
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
        pkjson.dump_pretty(PKDict(reqSeq=1, uri="/not-found-thing")),
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
        pkunit.pkeq(1, m.reqSeq)
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
                reqSeq=1,
                uri="/simulation-list",
                content=PKDict(simulationType=fc.sr_sim_type),
            ),
        ),
    )
    try:
        await asyncio.wait_for(reply_event.wait(), 2)
    finally:
        s.close()


@pytest.mark.asyncio
async def test_javascript_redirect(fc):
    from pykern import pkjson, pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from tornado import websocket, httpclient
    import asyncio
    import requests
    from sirepo import uri

    reply_event = asyncio.Event()

    def _msg(msg):
        m = pkjson.load_any(msg)
        pkunit.pkeq(1, m.reqSeq)
        pkunit.pkeq("text/html", m.contentType)
        pkunit.pkre("window.location =", m.content)
        reply_event.set()

    d = fc.sr_sim_data()
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
    u = uri.server_route(
        "findByNameWithAuth",
        PKDict(
            simulation_type=d.simulationType,
            application_mode="default",
            simulation_name=d.models.simulation.name,
        ),
        query=None,
    )
    await s.write_message(
        pkjson.dump_pretty(PKDict(reqSeq=1, uri=u)),
    )
    try:
        await asyncio.wait_for(reply_event.wait(), 2)
    finally:
        s.close()


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
        pkunit.pkeq(1, m.reqSeq)
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
        pkjson.dump_pretty(PKDict(reqSeq=1, uri="/robots.txt")),
    )
    await asyncio.wait_for(reply_event.wait(), 2)


@pytest.mark.asyncio
async def test_srw_upload(fc):
    from pykern import pkjson, pkunit, pkcompat
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from sirepo import srunit, sim_data, uri
    from tornado import websocket, httpclient
    import asyncio
    import base64
    import requests

    reply_event = asyncio.Event()

    def _msg(msg):
        if msg is None:
            # msg is None on close
            return
        m = pkjson.load_any(msg)
        pkunit.pkeq(1, m.reqSeq)
        c = pkjson.load_any(m.content)
        pkunit.pkeq("sample.tif", c.filename)
        pkunit.pkeq("sample", c.fileType)
        pkunit.pkeq(d.models.simulation.simulationId, c.simulationId)
        reply_event.set()

    d = fc.sr_sim_data("Sample from Image")
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
    f = sim_data.get_class(fc.sr_sim_type).lib_file_resource_path("sample.tif")
    u = uri.server_route(
        "uploadFile",
        params=PKDict(
            simulation_type=fc.sr_sim_type,
            simulation_id=d.models.simulation.simulationId,
            file_type="sample",
        ),
        query=None,
    )
    pkunit.work_dir().join("any").write_binary(base64.b64encode(f.read_binary()))
    await s.write_message(
        pkjson.dump_pretty(
            PKDict(
                reqSeq=1,
                uri=u,
                content=PKDict(
                    confirm="1",
                    file=PKDict(
                        filename=f.basename,
                        base64=pkcompat.from_bytes(base64.b64encode(f.read_binary())),
                    ),
                ),
            ),
        ),
    )
    try:
        await asyncio.wait_for(reply_event.wait(), 2)
    finally:
        s.close()
