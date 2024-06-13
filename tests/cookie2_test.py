"""Test sirepo.cookie

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from sirepo import srunit
import pytest


def test_set_get():
    from sirepo import srunit

    with srunit.quest_start() as qcall:
        from pykern import pkunit, pkcompat
        from pykern.pkunit import pkeq
        from pykern.pkdebug import pkdp
        from sirepo import cookie

        with pkunit.pkexcept("KeyError"):
            qcall.cookie.get_value("hi1")
        qcall.cookie.set_value("hi2", "hello")
        pkeq("hello", qcall.cookie.unchecked_get_value("hi2"))
