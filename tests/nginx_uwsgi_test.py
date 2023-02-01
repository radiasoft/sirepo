# -*- coding: utf-8 -*-
"""Test using nginx proxy and uwsgi

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest
import os
import shutil


pytestmark = pytest.mark.skipif(
    not bool(shutil.which("nginx"))
    or bool(os.environ.get("SIREPO_PKCLI_SERVICE_TORNADO")),
    reason="nginx not found or using tornado",
)


def test_ping(uwsgi_module):
    import sirepo.util
    from pykern import pkunit

    r = uwsgi_module.sr_post("jobSupervisorPing", {})
    pkunit.pkeq("ok", r.state)
