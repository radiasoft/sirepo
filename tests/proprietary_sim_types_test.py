# -*- coding: utf-8 -*-
"""test proprietary_sim_types

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import os
import pytest


def setup_module(module):
    os.environ.update(
        SIREPO_FEATURE_CONFIG_PROPRIETARY_SIM_TYPES="myapp",
        SIREPO_FEATURE_CONFIG_SIM_TYPES="srw",
    )


def test_myapp(auth_fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdlog, pkdexc, pkdp
    import sirepo.pkcli.setup_dev
    import sirepo.pkcli.roles
    import sirepo.auth_role

    sirepo.pkcli.setup_dev.default_command()
    fc = auth_fc
    # POSIT: Guests get all roles
    fc.sr_login_as_guest()
    # no forbidden
    fc.sr_sim_data()
    fc.sr_logout()
    fc.sr_email_login("a@b.c")
    r = fc.sr_post(
        "listSimulations", {"simulationType": fc.sr_sim_type}, raw_response=True
    )
    r.assert_http_status(403)
    sirepo.pkcli.roles.add_roles(
        fc.sr_uid,
        sirepo.auth_role.for_sim_type(fc.sr_sim_type),
    )
    r = fc.sr_run_sim(fc.sr_sim_data(), "heightWeightReport")
    p = r.get("plots")
    pkunit.pkok(p, "expecting truthy r.plots={}", p)
