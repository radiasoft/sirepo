# -*- coding: utf-8 -*-
"""Test sirepo.auth

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from pykern import pkcollections
from sirepo import srunit


def test_login():
    from sirepo import srunit

    with srunit.quest_start() as qcall:
        from pykern import pkunit, pkcompat
        from pykern.pkunit import pkeq, pkok, pkre, pkfail, pkexcept
        from sirepo import util
        from sirepo.auth import guest

        r = qcall.call_api("authState")
        pkre('LoggedIn": false.*Registration": false', pkcompat.from_bytes(r.data))
        with pkunit.pkexcept("SRException.*routeName=login"):
            qcall.auth.logged_in_user()
        with pkexcept("SRException.*routeName=login"):
            qcall.auth.require_user()
        qcall.cookie.set_sentinel()
        try:
            r = qcall.auth.login("guest", sim_type="myapp")
            pkfail("expecting sirepo.util.Response")
        except util.Response as e:
            r = e.sr_args.response
        pkre(r'LoggedIn":\s*true.*Registration":\s*false', pkcompat.from_bytes(r.data))
        u = qcall.auth.logged_in_user()
        pkok(u, "user should exist")
        # guests do not require completeRegistration
        qcall.auth.require_user()
