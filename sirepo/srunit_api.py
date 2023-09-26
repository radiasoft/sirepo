# -*- coding: utf-8 -*-
"""Support for sirepo.srunit tests

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import datetime
import sirepo.quest


class API(sirepo.quest.API):
    @sirepo.quest.Spec("allow_visitor", filename="SimFileName")
    async def api_srUnitCase(self):
        req = self.parse_post(filename=True, type=False)
        if "serialization" in req.filename:
            return self.reply_dict(
                PKDict(date_does_not_marshall=datetime.datetime.utcnow())
            )
        raise AssertionError("invalid request={}", req)


def init_apis(*args, **kwargs):
    pass
