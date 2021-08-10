# -*- coding: utf-8 -*-
u"""Using a sim type that lives in a package outside of sirepo.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import contextlib
import pytest


def test_run():
    from pykern import pkunit
    from pykern.pkdebug import pkdp, pkdlog

    with _install():
        fc = _fc()
        r = fc.sr_login_as_guest(sim_type='code1')
        d = fc.sr_sim_data(sim_type='code1', sim_name='Secret sauce')
        pkunit.pkeq('green', d.models.sauce.color)


def _fc():
    from pykern.pkdebug import pkdp
    from pykern.pkcollections import PKDict
    from sirepo import srunit

    fc = srunit.flask_client(
        cfg=PKDict(
            SIREPO_FEATURE_CONFIG_ROOT_PACKAGES='sirepo_test_root_packages',
        ),
        sim_types='code1',
        no_chdir_work=True,
    )
    return fc


@contextlib.contextmanager
def _install():
    from pykern import pkunit, pkio
    from pykern.pkdebug import pkdp, pkdlog
    import subprocess
    import sys

    with pkunit.save_chdir_work() as d:
        pkunit.data_dir().join('sirepo_test_root_packages.tar.gz').copy(d)
        subprocess.run('tar xzf sirepo_test_root_packages.tar.gz', shell=True)
        with pkio.save_chdir('sirepo_test_root_packages') as d:
            sys.path.append(str(d))
            yield
