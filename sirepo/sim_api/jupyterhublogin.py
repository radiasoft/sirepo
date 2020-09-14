# -*- coding: utf-8 -*-
u"""API's for jupyterhublogin sim

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp
import sirepo.api_perm
import sirepo.http_reply

@sirepo.api_perm.require_user
def api_redirectJupyterHub():
    return sirepo.http_reply.gen_redirect('jupyterHub')

def init_apis(*args, **kwargs):
    pass
