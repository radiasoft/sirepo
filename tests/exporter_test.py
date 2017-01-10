# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
from pykern import pkunit


def test_create_zip():
    from pykern.pkdebug import pkdp, pkdpretty
    from pykern.pkunit import pkfail, pkok
    from sirepo import sr_unit
    import copy
    import zipfile

    fc = sr_unit.flask_client()
    sim_type = 'srw'
    sim_id = fc.sr_sim_data(sim_type, 'Tabulated Undulator Example')['models']['simulation']['simulationId']
    res = fc.sr_get_raw(
        'exportSimulation',
        {
            'simulation_type': sim_type,
            'simulation_id': sim_id,
            'filename': 'anything.zip',
        },
    )
    fn = str(pkunit.work_dir().join('foo.zip'))
    with open(fn, 'wb') as f:
        f.write(res)
    z = zipfile.ZipFile(fn)
    nl = sorted(z.namelist())
    pkok(
        nl == ['magnetic_measurements.zip', 'sirepo-data.json'],
        '{}: zip namelist unexpected',
    )
