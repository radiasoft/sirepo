# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.srw`

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from pykern.pkcollections import PKDict


def test_srw_generate_all_optics(fc):
    from sirepo.template import srw
    from sirepo import srunit

    name = 'srw-all-optics'
    _generate_source(
        fc,
        fc.sr_post_form(
            'importFile',
            PKDict(folder='/generate_test'),
            PKDict(simulation_type=srw.SIM_TYPE),
            file='{}.json'.format(name),
        ),
        name,
    )


def test_srw_generate_python(fc):
    from sirepo.template import srw

    for name in ('NSLS-II CHX beamline', 'Sample from Image', 'Boron Fiber (CRL with 3 lenses)', 'Tabulated Undulator Example', 'Gaussian X-ray beam through a Beamline containing Imperfect Mirrors', 'NSLS-II SRX beamline', 'NSLS-II ESM beamline', 'Mask example', 'NSLS-II SMI beamline'):
        sim = fc.sr_sim_data(name)
        _generate_source(fc, sim, name)


def _generate_source(fc, sim, name):
    from pykern import pkio, pkunit, pkdebug
    import re

    pkdebug.pkdp(sim)
    d = fc.sr_get(
        'pythonSource',
        PKDict(
            simulation_id=sim.models.simulation.simulationId,
            simulation_type=sim.simulationType,
        ),
    ).data
    n = re.sub(
        r'[^\w\-\.]',
        '',
        re.sub(r'\s', '-', '{}.py'.format(name.lower())),
    )
    pkunit.work_dir().join(n).write(d, 'wb')
    pkunit.pkeq(pkunit.data_dir().join(n).read(), d)
