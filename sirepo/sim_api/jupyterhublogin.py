# -*- coding: utf-8 -*-
"""API's for jupyterhublogin sim

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig, pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog, pkdexc
import re
import sirepo.api_perm
import sirepo.events
import sirepo.oauth
import sirepo.quest
import sirepo.srdb
import sirepo.uri
import sirepo.uri_router
import sirepo.util

_cfg = None

_HUB_USER_SEP = "-"

_JUPYTERHUB_LOGOUT_USER_NAME_ATTR = "jupyterhub_logout_user_name"

_SIM_TYPE = "jupyterhublogin"


class API(sirepo.quest.API):
    @sirepo.quest.Spec("require_user", sim_type=f"SimType const={_SIM_TYPE}")
    async def api_checkAuthJupyterHub(self):
        # TODO remove
        self.parse_params(type=_SIM_TYPE)
        u = _unchecked_jupyterhub_user_name(
            self,
            have_simulation_db=False,
        )
        if not u:
            u = create_user(self)
        return self.reply_ok(PKDict(username=u))

    @sirepo.quest.Spec("require_user", sim_type=f"SimType const={_SIM_TYPE}")
    async def api_redirectJupyterHub(self):
        # TODO remove
        self.parse_params(type=_SIM_TYPE)
        if not _unchecked_jupyterhub_user_name(self):
            create_user(self)
        return self.reply_redirect("jupyterHub")


def cfg():
    return _init()


def create_user(qcall, check_dir=False):
    """Create a Jupyter user

    Args:
        check_dir (bool): assert that an existing user does not have a dir with
                          the same name (before modifying the name to eliminate
                          conflicts)
    Returns:
        user_name (str): The user_name of the new user
    """

    def __handle_or_name_sanitized():
        return re.sub(
            r"\W+",
            _HUB_USER_SEP,
            # Get the local part of the email. Or in the case of another auth
            # method it won't have an '@' so it will just be their user name, handle, etc.
            qcall.auth.logged_in_user_name().split("@")[0],
        ).lower()

    def __user_name():
        n = __handle_or_name_sanitized()
        if qcall.auth_db.model("JupyterhubUser").unchecked_search_by(user_name=n):
            # The username already exists. Add some randomness to try and create
            # a unique user name.
            n += _HUB_USER_SEP + sirepo.util.random_base62(3).lower()
        return n

    n = _unchecked_jupyterhub_user_name(qcall)
    if n:
        return n
    u = __user_name()
    # POSIT: if two creates happen simultaneously, there may be an existence
    # collision, but the db will be consistent, because this call happens
    # first, before db insert.
    if check_dir and _user_dir(qcall, u).exists():
        raise AssertionError(f"existing user dir with same name={u}")
    qcall.auth_db.model(
        "JupyterhubUser",
        uid=qcall.auth.logged_in_user(),
        user_name=u,
    ).save()
    # POSIT: one transaction will rollback if two creates happen at the same time,
    # but that won't change the need for the directory.
    pkio.mkdir_parent(_user_dir(qcall))
    return u


def delete_user_dir(qcall):
    n = _unchecked_jupyterhub_user_name(qcall, have_simulation_db=False)
    if not n:
        return
    pkio.unchecked_remove(_user_dir(qcall, user_name=n))


def init_apis(*args, **kwargs):
    _init()
    sirepo.events.register(
        PKDict(
            auth_logout=_event_auth_logout,
            end_api_call=_event_end_api_call,
        )
    )


def _init():
    global _cfg

    if _cfg:
        return _cfg
    _cfg = pkconfig.init(
        user_db_root_d=(
            pkio.py_path(sirepo.srdb.root()).join("jupyterhub", "user"),
            pkio.py_path,
            "Jupyterhub user db",
        ),
        uri_root=("jupyter", str, "the root uri of jupyterhub"),
    )
    pkio.mkdir_parent(_cfg.user_db_root_d)
    return _cfg


def _event_auth_logout(qcall, kwargs):
    # We must set the uid here because in _event_end_api_call we won't
    # be able to retrieve it. The user is already logged out by the
    # time _event_end_api_call is called

    qcall.bucket_set(
        _JUPYTERHUB_LOGOUT_USER_NAME_ATTR, _unchecked_hub_user(qcall, kwargs.uid)
    )


def _event_end_api_call(qcall, kwargs):
    # We can't move this code into _event_auth_logout because we need
    # the response object.

    u = qcall.bucket_unchecked_get(_JUPYTERHUB_LOGOUT_USER_NAME_ATTR)
    if not u:
        return
    # Delete the JupyterHub cookies because we are logging out of Sirepo.
    # Trailing slash is required in paths
    kwargs.resp.delete_third_party_cookies(
        (
            PKDict(key="jupyterhub-hub-login", path=f"/{_cfg.uri_root}/hub/"),
            PKDict(key=f"jupyterhub-user-{u}", path=f"/{_cfg.uri_root}/user/{u}/"),
        )
    )


def _unchecked_hub_user(qcall, uid):
    u = qcall.auth_db.model("JupyterhubUser").unchecked_search_by(uid=uid)
    if u:
        return u.user_name
    return None


def _unchecked_jupyterhub_user_name(qcall, have_simulation_db=True):
    return _unchecked_hub_user(
        qcall, qcall.auth.logged_in_user(check_path=have_simulation_db)
    )


def _user_dir(qcall, user_name=None):
    if not user_name:
        user_name = _unchecked_jupyterhub_user_name(qcall)
        assert user_name, "must have user to get dir"
    return _cfg.user_db_root_d.join(user_name)
