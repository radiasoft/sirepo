# -*- coding: utf-8 -*-
"""CLI for jupyterhublogin

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pykern.pkcli


def create_user(email):
    """Create a JupyterHubUser

    Args:
        email (str): Email of user to create.

    Returns:
        user_name (str): The user_name of the newly created user or existing user
                        if email already exists.
    """
    import pyisemail
    import sirepo.auth
    import sirepo.server
    import sirepo.sim_api.jupyterhublogin
    import sirepo.template


    if not pyisemail.is_email(email):
        pykern.pkcli.command_error('invalid email={}', email)
    sirepo.server.init()
    sirepo.template.assert_sim_type('jupyterhublogin')
    u = sirepo.auth.get_module('email').unchecked_user_by_user_name(email)
    if not u:
        pykern.pkcli.command_error('no sirepo user with email={}', email)
    with sirepo.auth.set_user_outside_of_http_request(u):
        # TODO(e-carlin): locking
        n = sirepo.sim_api.jupyterhublogin.unchecked_jupyterhub_user_name(
            have_simulation_db=False,
        )
        if n:
            return n
        return sirepo.sim_api.jupyterhublogin.create_user(check_dir=True)
