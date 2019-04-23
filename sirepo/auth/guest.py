# -*- coding: utf-8 -*-
u"""Guest login

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import auth
from sirepo import http_request
import sirepo.template


AUTH_METHOD = 'guest'

#: User can see it
AUTH_METHOD_VISIBLE = True

#: module handle
this_module = pkinspect.this_module()


@api_perm.require_cookie_sentinel
def api_authGuestLogin():
    """You have to be an anonymous or logged in user at this point"""
    t = sirepo.template.assert_sim_type(http_request.parse_json().simulationType)
    return auth.login(this_module, sim_type=t)


def init_apis(*args, **kwargs):
    pass
