# -*- coding: utf-8 -*-
u"""API's for jupyterhublogin sim

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import sirepo.api_perm
import sirepo.auth
import sirepo.auth_db
import sirepo.http_reply
import sirepo.http_request
import sirepo.jupyterhub
import sirepo.uri_router


@sirepo.api_perm.require_user
def api_dismissJupyterhubDataMovePrompt():
    sirepo.jupyterhub.set_rs_migration_prompt_dismissed(
        sirepo.http_request.parse_json().dismiss
    )
    return sirepo.http_reply.gen_json_ok()


@sirepo.api_perm.require_user
def api_migrateRsJupyterhubData(simulation_type):
    return sirepo.uri_router.call_api(
            'authGithubLogin',
            kwargs=PKDict(simulation_type=simulation_type),
        )


@sirepo.api_perm.require_user
def api_redirectJupyterHub():
    return sirepo.http_reply.gen_redirect('jupyterHub')


def init_apis(*args, **kwargs):
    pass
