# -*- coding: utf-8 -*-
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


def test_check_auth_jupyterhub(fc):
    import sirepo.srdb
    from pykern import pkio
    from pykern.pkunit import pkeq

    def _get_num_jupyterhub_user_dirs():
        return len(pkio.sorted_glob(sirepo.srdb.root().join("jupyterhub/user/**"))) - 1

    def _jupyter_user_dir_exists(uid):
        for x in [
            os.path.basename(d)
            for d in pkio.sorted_glob(sirepo.srdb.root().join("jupyterhub/user/**"))
        ]:
            if uid.lower() in x:
                return True
        return False

    fc.sr_logout()
    n = _get_num_jupyterhub_user_dirs()
    fc.sr_get("checkAuthJupyterHub")
    pkeq(n, _get_num_jupyterhub_user_dirs())
    fc.sr_login_as_guest()
    pkeq(False, _jupyter_user_dir_exists(fc.sr_uid))
    fc.sr_get("checkAuthJupyterHub").assert_success()
    pkeq(True, _jupyter_user_dir_exists(fc.sr_uid))
    n = _get_num_jupyterhub_user_dirs()
    fc.sr_get("checkAuthJupyterHub").assert_success()
    pkeq(n, _get_num_jupyterhub_user_dirs())


def test_jupyterhub_redirect(fc):
    fc.sr_get("redirectJupyterHub", redirect=False).assert_http_redirect("jupyterHub")
