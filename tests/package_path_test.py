"""Using a sim type that lives in a package outside of sirepo.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest
from pykern.pkcollections import PKDict

# Only one test function is possible


def _setup():
    from pykern import pkunit, pkio
    import subprocess
    import sys, os

    with pkunit.save_chdir_work() as d:
        p = "avoid_being_seen"
        t = d.join(p).ensure(dir=True)
        pkunit.data_dir().join(p).copy(t)
        t = str(t)
        sys.path.append(t)
        e = os.environ.get("PYTHONPATH", "")
        if e:
            e += ":"
        e += t
        os.environ["PYTHONPATH"] = e


pytestmark = pytest.mark.sirepo_args(
    fc_module=PKDict(
        cfg=PKDict(
            SIREPO_FEATURE_CONFIG_PACKAGE_PATH="sirepo_test_package_path:sirepo"
        ),
        sim_types="code1",
        setup_func=_setup,
        empty_work_dir=False,
    ),
)


def test_run(fc_module):
    from pykern import pkunit
    from pykern.pkdebug import pkdp, pkdlog

    r = fc_module.sr_login_as_guest(sim_type="code1")
    d = fc_module.sr_sim_data(sim_type="code1", sim_name="Secret sauce")
    pkunit.pkeq("green", d.models.sauce.color)
