# -*- coding: utf-8 -*-
"""Test ldap

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_happy_path():
    from sirepo import srunit
    from pykern.pkcollections import PKDict
    from pykern import pkinspect
    import sys

    sys.modules["ldap"] = pkinspect.this_module()

    with srunit.quest_start(cfg={"SIREPO_AUTH_METHODS": "ldap"}) as qcall:
        from pykern import pkunit
        from pykern import pkdebug

        r = qcall.call_api(
            "authLdapLogin",
            data=PKDict(
                simulationType="myapp",
                email="vagrant@xxxxradiasoft.net",
                password="vagrant",
            ),
        )
        pkunit.pkeq(200, r.status_as_int())
        pkunit.pkre("location.*/complete-registration", r.content_as_str())


def initialize(*args, **kwargs):
    """Simulate ldap.initialize"""
    from pykern.pkcollections import PKDict

    return PKDict(simple_bind_s=lambda x, y: None)
