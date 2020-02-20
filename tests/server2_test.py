# -*- coding: utf-8 -*-
u"""more server tests

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pytest


def test_user_alert(fc):
    from pykern.pkunit import pkeq, pkre
    from sirepo import srunit

    d = fc.sr_sim_data()
    d.models.dog.breed = 'user_alert=user visible text'
    r = fc.sr_run_sim(d, 'heightWeightReport', expect_completed=False)
    pkeq('error', r.state)
    pkeq('user visible text', r.error)
