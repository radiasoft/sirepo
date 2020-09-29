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
    # TODO(e-carlin): maybe use cookie for this instead?
    with sirepo.auth_db.thread_lock:
        # TODO(e-carlin): _get_or_create_user maybe should return the sql model?
        # TODO(e-carlin): make public if this is what I decide to use
        # Need to create user because may not exist
        sirepo.jupyterhub._get_or_create_user()
        u = sirepo.jupyterhub.JupyterhubUser.search_by(
            uid=sirepo.auth.logged_in_user(),
        )
        u.rs_migration_prompt_dimsissed = sirepo.http_request.parse_json().dismiss
        u.save()
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
