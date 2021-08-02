# -*- coding: utf-8 -*-
u"""Using a sim type outside of Sirepo

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import contextlib
import pytest


def test_run():
    from pykern import pkunit
    from pykern.pkdebug import pkdp, pkdlog

    with _rsprivate():
        fc = _fc()
        r = fc.sr_login_as_guest()
        d = fc.sr_sim_data(sim_type='code1', sim_name='Secret sauce')
        pkunit.pkeq('green', d.models.sauce.color)


def _fc():
    from pykern.pkdebug import pkdp
    from pykern.pkcollections import PKDict
    from sirepo import srunit

    PKDict(
        SIREPO_FEATURE_CONFIG_DYNAMIC_SIM_TYPES='code1:rsprivate',
    )
    fc = srunit.flask_client(
        cfg=PKDict(
            SIREPO_FEATURE_CONFIG_DYNAMIC_SIM_TYPES='code1:rsprivate',
        ),
        no_chdir_work=True,
    )
    return fc


@contextlib.contextmanager
def _rsprivate():
    from pykern import pkunit, pkio
    from pykern.pkdebug import pkdp, pkdlog
    import importlib
    import pip
    import site
    import subprocess

    with pkunit.save_chdir_work() as d:
        pkunit.data_dir().join('rsprivate.tar.gz').copy(d)
        subprocess.run('tar xzf rsprivate.tar.gz', shell=True)
        with pkio.save_chdir('rsprivate'):
            try:
                pip.main(['install', '-e', '.'])
                # Makes rsprivate importable
                importlib.reload(site)
                yield
            finally:
                subprocess.run('pip uninstall -y rsprivate', shell=True)
