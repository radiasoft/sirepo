# -*- coding: utf-8 -*-
u"""decorators for API permissions and the permissions themselves

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern import pkinspect
import aenum

#: decorator sets this attribute with an APIPerm
ATTR = 'api_perm'


class APIPerm(aenum.Flag):
    ALLOW_VISITOR = aenum.auto()
    REQUIRE_USER = aenum.auto()
    ALLOW_COOKIELESS_USER = aenum.auto()
    ALLOW_LOGIN = aenum.auto()


def _init():
    def _new(e):
        def _decorator(func):
            setattr(func, ATTR, e)
            return func

        return _decorator

    m = pkinspect.this_module()
    for e in iter(APIPerm):
        setattr(m, e.name.lower(), _new(e))


_init()
