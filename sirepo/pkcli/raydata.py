# -*- coding: utf-8 -*-
"""CLI for raydata

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdlog
from sirepo.template import template_common


def run(cfg_dir):
    _run()
    template_common.write_sequential_result(PKDict())

def run_background(cfg_dir):
    _run()


def create_scans(num_scans, delay=True):
    from sirepo.template import raydata
    import bluesky
    import bluesky.plans
    import databroker
    import ophyd.sim
    import time

    num_scans = int(num_scans)
    assert num_scans > 0, \
        f'num_scans={num_scans} must be > 0'
    d = databroker.Broker.named(raydata.catalog().name)
    RE = bluesky.RunEngine({})
    RE.subscribe(d.insert)
    b = set(raydata.catalog())
    for i in range(num_scans):
        RE(bluesky.plans.count(
            [ophyd.sim.det1, ophyd.sim.det2],
            num=5,
            md={
                'T_sample_': i,
                'owner': 'foo',
                'sequence id': i,
            },
        ))
        a = set(raydata.catalog())
        b = a
        if delay:
            time.sleep(2)

def _run():
    template_common.exec_parameters()
