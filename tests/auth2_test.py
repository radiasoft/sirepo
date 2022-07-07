# -*- coding: utf-8 -*-
u"""Test sirepo.auth

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_myapp_user_dir_deleted(fc):
    from pykern import pkunit, pkcompat
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    import sirepo.srdb

    sirepo.srdb.root().join(
        'user',
        fc.sr_auth_state().uid,
    ).remove(rec=1)
    r = fc.sr_post(
        'listSimulations',
        PKDict(simulationType=fc.sr_sim_type),
        raw_response=True,
    )
    pkunit.pkre('^<!DOCTYPE html.*class="landing', pkcompat.from_bytes(r.data))
    fc.sr_auth_state(displayName=None, isLoggedIn=False, method=None)
