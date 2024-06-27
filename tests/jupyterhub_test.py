"""JupyterHub tests

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest
import os


def setup_module(module):
    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES="jupyterhublogin",
        SIREPO_AUTH_ROLE_MODERATION_MODERATOR_EMAIL="x@x.x",
    )


def test_api_security_without_role(fc):
    from pykern.pkunit import pkok
    from sirepo.pkcli import roles
    import sirepo.auth_role

    x = sirepo.auth_role.for_sim_type("jupyterhublogin")
    roles.delete(fc.sr_uid, x)
    pkok(x not in fc.sr_auth_state().roles, "{} role should have been removed", x)
    fc.sr_get("checkAuthJupyterHub").assert_http_status(403)
    fc.sr_get("redirectJupyterHub", redirect=False).assert_http_status(403)
    roles.add(fc.sr_uid, x)
    pkok(x in fc.sr_auth_state().roles, "{} role should have been added", x)
    fc.sr_get("checkAuthJupyterHub").assert_success()
    fc.sr_get("redirectJupyterHub", redirect=False).assert_http_redirect("jupyterHub")


def test_check_auth_jupyterhub(fc):
    import sirepo.srdb
    from pykern import pkio
    from pykern.pkunit import pkeq, pkok

    def _get_num_jupyterhub_user_dirs():
        return len(pkio.sorted_glob(sirepo.srdb.root().join("jupyterhub/user/**"))) - 1

    def _jupyter_user_dir_exists(uid):
        return bool(
            len(
                pkio.sorted_glob(
                    sirepo.srdb.root().join("jupyterhub", "user", f"*{uid.lower()}*")
                )
            )
        )

    fc.sr_logout()
    n = _get_num_jupyterhub_user_dirs()
    fc.sr_get("checkAuthJupyterHub", redirect=False).assert_http_redirect("login")
    pkeq(n, _get_num_jupyterhub_user_dirs())
    fc.sr_login_as_guest()
    pkok(
        not _jupyter_user_dir_exists(fc.sr_uid), "Jupyter user dir should not exist yet"
    )
    fc.sr_get("checkAuthJupyterHub").assert_success()
    pkok(
        _jupyter_user_dir_exists(fc.sr_uid),
        "Jupyter user dir should exist after call to api_checkAuthJupyterHub",
    )
    n = _get_num_jupyterhub_user_dirs()
    fc.sr_get("checkAuthJupyterHub").assert_success()
    pkeq(n, _get_num_jupyterhub_user_dirs())


def test_jupyterhub_redirect(fc):
    fc.sr_get("redirectJupyterHub", redirect=False).assert_http_redirect("jupyterHub")


def test_logout(auth_fc):
    """Clears third party (jupyterhub) cookies"""
    from pykern.pkdebug import pkdp

    # TODO(e-carlin): https://github.com/radiasoft/sirepo/issues/7096
    # This test should verify that the cookie was actually removed.
    auth_fc.sr_login_as_guest()
    auth_fc.sr_get("checkAuthJupyterHub").assert_success()
    auth_fc.sr_logout()
