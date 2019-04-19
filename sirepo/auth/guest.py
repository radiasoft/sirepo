# -*- coding: utf-8 -*-
u"""Email login support

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import api_perm
from sirepo import auth
import sirepo.template

AUTH_METHOD = 'guest'

#: User can see it
AUTH_METHOD_VISIBLE = True

#: module handle
this_module = pkinspect.this_module()


@api_perm.require_cookie_sentinel
def api_guestAuthLogin(simulation_type):
    """You have to be an anonymous or logged in user at this point"""
    t = sirepo.template.assert_sim_type(simulation_type)
    return auth.login(this_module, sim_type=t)
