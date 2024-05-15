# -*- coding: utf-8 -*-
"""Test auth_role.DISABLE and api_perm.require_not_disabled

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_disabled_user(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq, pkok
    import sirepo.auth_role
    import sirepo.pkcli.roles

    a = fc.sr_auth_state()
    pkok(
        sirepo.auth_role.ROLE_DISABLED not in fc.sr_auth_state().roles,
        "{} found in roles",
        sirepo.auth_role.ROLE_DISABLED,
    )
    fc.sr_post(
        "listSimulations", {"simulationType": fc.sr_sim_type}, raw_response=True
    ).assert_success()
    sirepo.pkcli.roles.add(fc.sr_uid, sirepo.auth_role.ROLE_DISABLED)
    pkok(
        sirepo.auth_role.ROLE_DISABLED in fc.sr_auth_state().roles,
        "{} not found in roles",
        sirepo.auth_role.ROLE_DISABLED,
    )
    fc.sr_post(
        "listSimulations", {"simulationType": fc.sr_sim_type}, raw_response=True
    ).assert_http_status(403)
    sirepo.pkcli.roles.delete(fc.sr_uid, sirepo.auth_role.ROLE_DISABLED)
    pkok(
        sirepo.auth_role.ROLE_DISABLED not in fc.sr_auth_state().roles,
        "{} found in roles",
        sirepo.auth_role.ROLE_DISABLED,
    )
