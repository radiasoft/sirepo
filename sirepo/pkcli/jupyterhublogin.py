# -*- coding: utf-8 -*-
"""CLI for jupyterhublogin

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcli
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
import pyisemail
import sirepo.auth_db
import sirepo.auth_role
import sirepo.quest
import sirepo.sim_api.jupyterhublogin
import sirepo.template


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

    def maybe_create_sirepo_user(qcall, module, email, display_name):
        u = module.unchecked_user_by_user_name(qcall, email)
        if u:
            # Fully registered email user
            assert sirepo.auth_db.UserRegistration.search_by(
                uid=u
            ).display_name, f"uid={u} authorized AuthEmailUser record but no UserRegistration.display_name"
            return u
        m = module.UserModel.search_by(unverified_email=email)
        if m:
            # Email user that needs to complete registration (no display_name but have unverified_email)
            assert qcall.auth.need_complete_registration(
                m
            ), "email={email} has no display_name but does not need to complete registration"
            pkcli.command_error(
                "email={} needs complete registration but we do not have their uid (in cookie)",
                email,
            )
        # Completely new Sirepo user
        u = qcall.auth.create_user(module)
        qcall.auth.user_registration(uid=u, display_name=display_name)
        module.UserModel(
            unverified_email=email,
            uid=u,
            user_name=email,
        ).save()
        return u

    if not pyisemail.is_email(email):
        pkcli.command_error("invalid email={}", email)
    sirepo.template.assert_sim_type("jupyterhublogin")
    with sirepo.quest.start() as qcall:
        m = "email"
        u = maybe_create_sirepo_user(
            qcall,
            qcall.auth.get_module(m),
            email,
            display_name,
        )
        with qcall.auth.logged_in_user_set(u, method=m):
            n = sirepo.sim_api.jupyterhublogin.create_user(
                qcall,
                check_dir=True,
            )
            sirepo.auth_db.UserRole.add_roles(
                qcall,
                [sirepo.auth_role.for_sim_type("jupyterhublogin")],
            )
        return PKDict(email=email, jupyterhub_user_name=n)
