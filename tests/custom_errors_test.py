# -*- coding: utf-8 -*-
"""test custom errors

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


def test_custom_errors(fc):
    from pykern.pkunit import pkre
    import sirepo.simulation_db
    import sirepo.uri

    for k, v in sirepo.simulation_db.SCHEMA_COMMON.customErrors.items():
        r = fc.sr_get(sirepo.uri.local_route(fc.sr_sim_type, v.route))
        r.assert_success()
        with open(sirepo.resource.static("html", v.url), "r") as f:
            pkre(v.msg, f.read())
