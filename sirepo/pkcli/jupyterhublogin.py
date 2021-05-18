# -*- coding: utf-8 -*-
"""CLI for jupyterhublogin

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcli
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog


def create_user(email, display_name):
    """Create a JupyterHubUser

    This is idempotent. It will create a Sirepo email user if none exists for
    the email before creating a jupyterhub user

    It will update the user's display_name if the one supplied is different than
    the one in the db.

    Args:
        email (str): Email of user to create.
        display_name (str): UserRegistration display_name

    Returns:
        user_name (str): The jupyterhub user_name of the user
    """
    import pyisemail
    import sirepo.auth
    import sirepo.auth_db
    import sirepo.server
    import sirepo.sim_api.jupyterhublogin
    import sirepo.template

    def maybe_create_sirepo_user(module, email, display_name):
        u = module.unchecked_user_by_user_name(email)
        if u:
            # Fully registered email user
            assert sirepo.auth_db.UserRegistration.search_by(uid=u).display_name, \
                f'uid={u} authorized AuthEmailUser record but no UserRegistration.display_name'
            return u
        m = module.AuthEmailUser.search_by(unverified_email=email)
        if m:
            # Email user that needs to complete registration (no display_name but have unverified_email)
            assert sirepo.auth.need_complete_registration(m), \
                'email={email} has no display_name but does not need to complete registration'
            pkcli.command_error(
                'email={} needs complete registration but we do not have their uid (in cookie)',
                email,
            )
        # Completely new Sirepo user
        u = sirepo.auth.create_new_user(
            lambda u: sirepo.auth.user_registration(u, display_name=display_name),
            module,
        )
        module.AuthEmailUser(
            unverified_email=email,
            uid=u,
            user_name=email,
        ).save()
        return u

    if not pyisemail.is_email(email):
        pkcli.command_error('invalid email={}', email)
    sirepo.server.init()
    sirepo.template.assert_sim_type('jupyterhublogin')
    with sirepo.auth_db.session_and_lock():
        u = maybe_create_sirepo_user(
            sirepo.auth.get_module('email'),
            email,
            display_name,
        )
        with sirepo.auth.set_user_outside_of_http_request(u):
            n = sirepo.sim_api.jupyterhublogin.create_user(check_dir=True)
            return PKDict(email=email, jupyterhub_user_name=n)
