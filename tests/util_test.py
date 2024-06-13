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


def test_import_submodule():
    from pykern import pkunit, pkconfig
    from sirepo import util
    import sys

    t = str(pkunit.data_dir())
    sys.path.insert(0, t)
    pkconfig.reset_state_for_testing(
        dict(
            SIREPO_FEATURE_CONFIG_PACKAGE_PATH="pkg:sirepo",
            SIREPO_FEATURE_CONFIG_SIM_TYPES="appok:apperr:appmissing",
        ),
    )
    util.import_submodule("template", "appok")
    with pkunit.pkexcept("'not_found_module'"):
        util.import_submodule("template", "apperr")
    with pkunit.pkexcept("sim_type=appmissing"):
        util.import_submodule("template", "appmissing")
