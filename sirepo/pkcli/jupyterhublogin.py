"""CLI for jupyterhublogin

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcli
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
import pyisemail
import sirepo.auth
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

    def maybe_create_sirepo_user(qcall, email, display_name):
        m = qcall.auth_db.model("AuthEmailUser")
        u = m.unchecked_uid(user_name=email)
        if u:
            if qcall.auth.need_complete_registration(u):
                pkcli.command_error("email={} needs to complete registration", email)
            # Fully registered email user
            return u
        u = m.unchecked_search_by(unverified_email=email)
        if u:
            pkcli.command_error("email={} is not verified", email)
        # Completely new Sirepo user
        return qcall.auth.create_user_from_email(email=email, display_name=display_name)

    if not pyisemail.is_email(email):
        pkcli.command_error("invalid email={}", email)
    sirepo.template.assert_sim_type("jupyterhublogin")
    with sirepo.quest.start() as qcall:
        u = maybe_create_sirepo_user(
            qcall,
            email,
            display_name,
        )
        with qcall.auth.logged_in_user_set(u, method=sirepo.auth.METHOD_EMAIL):
            n = sirepo.sim_api.jupyterhublogin.create_user(
                qcall=qcall,
            )
            qcall.auth_db.model("UserRole").add_roles(
                roles=[sirepo.auth_role.for_sim_type("jupyterhublogin")],
            )
        return PKDict(email=email, jupyterhub_user_name=n)


def unknown_user_dirs():
    """Directory names for Jupyter users that are not in database.
    Excludes directories that begin with capital letter.

    Returns:
        list: directories for Jupyter users that are not in the database.
    """
    with sirepo.quest.start() as qcall:
        m = []
        r = frozenset(
            qcall.auth_db.model("JupyterhubUser").search_all_for_column("user_name")
        )
        for d in pkio.sorted_glob(
            sirepo.sim_api.jupyterhublogin.cfg().user_db_root_d.join("*")
        ):
            if not d.basename[0].isupper() and not d.basename in r:
                m.append(d)
        return m
