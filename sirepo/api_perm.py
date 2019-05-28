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
    #: A user is required but there might not be a cookie yet
    ALLOW_COOKIELESS_REQUIRE_USER = aenum.auto()
    #: cookie.set_user can be called even if a cookie wasn't received
    ALLOW_COOKIELESS_SET_USER = aenum.auto()
    #: anybody can view this page, even without cookies
    ALLOW_VISITOR = aenum.auto()
    #: use basic auth authentication (only)
    REQUIRE_AUTH_BASIC = aenum.auto()
    #: a cookie has to have been returned, which might contain a user
    REQUIRE_COOKIE_SENTINEL = aenum.auto()
    #: a user will be created if necessary and auth may be necessary
    REQUIRE_USER = aenum.auto()


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
