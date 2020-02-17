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


def test_elegant(fc):
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
    pkunit.pkok('path' in r, "expected key 'path' in {}", r)
    r = fc.sr_post(
        'extractArchive',
        PKDict(
            simulationId=data.models.simulation.simulationId,
            simulationType=fc.sr_sim_type,
            path=r.path,
        ),
    )
    r = fc.sr_run_sim(r, m)
    pkunit.pkeq('completed',  r.state)
