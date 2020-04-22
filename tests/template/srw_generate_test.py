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

    for name in (
        'Boron Fiber (CRL with 3 lenses)',
        'Gaussian X-ray beam through a Beamline containing Imperfect Mirrors',
        'Mask example',
        'NSLS-II CHX beamline',
        'NSLS-II ESM beamline',
        'NSLS-II HXN beamline: SSA closer',
        'NSLS-II SMI beamline',
        'NSLS-II SRX beamline',
        'Sample from Image',
        'Tabulated Undulator Example',
    ):
        sim = fc.sr_sim_data(name)
        _generate_source(fc, sim, name)


def _generate_source(fc, sim, name):
    from pykern import pkio, pkunit, pkdebug, pkcompat
    import re

    d = pkcompat.from_bytes(fc.sr_get(
        'pythonSource',
        PKDict(
            simulation_id=sim.models.simulation.simulationId,
            simulation_type=sim.simulationType,
        ),
    ).data)
    n = re.sub(
        r'[^\w\-\.]',
        '',
        re.sub(r'\s', '-', '{}.py'.format(name.lower())),
    )
    e = pkunit.data_dir().join(n)
    a = pkunit.work_dir().join(n)
    pkio.write_text(a, d)
    pkunit.pkeq(pkio.read_text(e), d, 'diff {} {}', e, a)
