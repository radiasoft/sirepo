# -*- coding: utf-8 -*-
u"""test running of animations through docker

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import os
import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get('SIREPO_FEATURE_CONFIG_JOB') != '1',
    reason='SIREPO_FEATURE_CONFIG_JOB != 1'
)


def xtest_elegant(fc):
    from pykern import pkunit
    n = 'Compact Storage Ring'
    m = 'twissReport'
    data = fc.sr_sim_data(n)
    r = fc.sr_run_sim(data, m)
    pkunit.pkeq('completed',  r.state)


def test_elegant_archive_simulation(fc):
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    n = 'Compact Storage Ring'
    m = 'twissReport'
    data = fc.sr_sim_data(n)
    r = fc.sr_run_sim(data, m)
    pkunit.pkeq('completed',  r.state)
    r = fc.sr_post(
        'archiveSimulation',
        PKDict(
            simulationId=data.models.simulation.simulationId,
            simulationType=fc.sr_sim_type,
        ),
    )
    pkunit.pkok('ok' in r.state, "expected state.ok r={}", r)
    r = fc.sr_post('/simulation-list', {'simulationType': fc.sr_sim_type})
    f = False
    for i, e in enumerate(r):
        if len(r[int(i)].archives) > 0:
            pkunit.pkok(not f, 'expecting only one simulation with archives r={}', r)
            f = True
            d = fc.sr_post('extractArchive', PKDict(r[i].archives[0]))
    pkunit.pkok(f, 'no archives found in r={}', r)
    r = fc.sr_run_sim(d, m)
    pkunit.pkeq('completed',  r.state)
