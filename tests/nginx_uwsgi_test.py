# -*- coding: utf-8 -*-
"""Test using nginx proxy and uwsgi

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import pytest
import os
import shutil


pytestmark = pytest.mark.skipif(
    not bool(shutil.which("nginx")), reason="nginx not found"
)


def test_ping(uwsgi_module):
    import sirepo.util
    from pykern import pkunit

    r = uwsgi_module.sr_post("jobSupervisorPing", {})
    pkunit.pkeq("ok", r.state)
