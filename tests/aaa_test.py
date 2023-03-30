# -*- coding: utf-8 -*-
"""simple test that fails

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_fail(fc):
    from pykern import pkunit

    pkunit.pkfail("always")
