# -*- coding: utf-8 -*-
u"""test missing cookies

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_srw_missing_cookies(fc):
    from pykern.pkunit import pkeq, pkre, pkexcept
    from sirepo import srunit
    import json

    fc.cookie_jar.clear()
    with pkexcept('missingCookies'):
        fc.sr_post('/simulation-list', {'simulationType': fc.sr_sim_type})
