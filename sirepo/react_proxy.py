# -*- coding: utf-8 -*-
"""proxy react for development

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkconfig
import re
import tornado.httpclient
import tornado.web
import urllib

cfg = None


def routes():
    if not pykern.pkconfig.channel_in("dev"):
        return []
    _init()
    if not cfg.uri:
        return []
    p = [
        "/manifest.json",
        "/static/js/bundle.js",
        "/static/js/bundle.js.map",
    ]
    for x in cfg.sim_types:
        x = "/" + x
        p.append(x)
        p.append(f"{x}-schema.json")
    return [("(?:" + "|".join(map(re.escape, p)) + ")", _Request)]


class _Request(tornado.web.RequestHandler):
    async def get(self, *args, **kwargs):
        p = self.request.uri[1:]
        if p in cfg.sim_types:
            p = ""
        r = await tornado.httpclient.AsyncHTTPClient().fetch(cfg.uri + p)
        self.set_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.set_header("Pragma", "no-cache")
        for x in "Content-Length", "Content-Type":
            d = r.headers.get(x)
            if d is not None:
                self.set_header(x, d)
        self.write(r.body)

    def on_connection_close(self):
        pass


def _init():
    def _uri(value):
        if value is None:
            return None
        u = urllib.parse.urlparse(value)
        if (
            u.scheme
            and u.netloc
            and u.path == "/"
            and len(u.params + u.query + u.fragment) == 0
        ):
            return value
        pykern.pkconfig.raise_error(f"invalid url={value}, must be http://netloc/")

    global cfg
    if cfg:
        return
    cfg = pykern.pkconfig.init(
        uri=(None, _uri, "Base URL of npm start server"),
        sim_types=(("myapp",), set, "React apps"),
    )
