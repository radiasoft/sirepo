# -*- coding: utf-8 -*-
"""test uri

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_secure_filename():
    from sirepo import util
    from pykern import pkunit

    pkunit.pkeq("file", util.secure_filename(""))
    pkunit.pkeq("file", util.secure_filename("/"))
    pkunit.pkeq("a_b", util.secure_filename("/a/b"))
    pkunit.pkeq("b", util.secure_filename(".b."))


def test_validate_path():
    from sirepo import util
    from pykern import pkunit

    with pkunit.pkexcept("empty uri"):
        util.validate_path("")
    with pkunit.pkexcept("illegal char"):
        util.validate_path("a*")
    with pkunit.pkexcept("empty component"):
        util.validate_path("a//b")
    with pkunit.pkexcept("empty component"):
        util.validate_path("/a")
    with pkunit.pkexcept("empty component"):
        util.validate_path("a/")
    with pkunit.pkexcept("dot prefix"):
        util.validate_path("a/../b")
    with pkunit.pkexcept("dot prefix"):
        util.validate_path(".a")
