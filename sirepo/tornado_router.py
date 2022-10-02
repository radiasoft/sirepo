# -*- coding: utf-8 -*-
"""UI session

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp


def routes():
    if not pykern.pkconfig.channel_in("dev"):
        return []
    p = [
        "/auth-guest-login(/.*)",
    ]
    return [("(?:" + "|".join(map(re.escape, p)) + ")", _Request)]


class _Request(tornado.web.RequestHandler):
    async def get(self, *args, **kwargs):
        # TODO(robnagler): Possibly only needs to be a login request.
        pass

    def on_connection_close(self):
        pass
