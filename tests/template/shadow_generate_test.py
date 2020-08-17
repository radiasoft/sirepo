# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.shadow`

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
import pytest

pytest.importorskip('xraylib')

def test_generate_python():
    from pykern import pkio
    from pykern.pkunit import pkeq
    from sirepo.template import shadow

    with pkunit.save_chdir_work():
        for name in ('Beamline Propagation', 'Complete Beamline', 'Wiggler'):
            data = _example_data(name)
            data['report'] = 'watchpointReport{}'.format(data.models.beamline[-1].id)
            actual = shadow._generate_parameters_file(data)
            outfile = data.models.simulation.simulationId + '.txt'
            pkio.write_text(outfile, actual)
            expect = pkio.read_text(pkunit.data_dir().join(outfile))
            pkeq(expect, actual)


def _example_data(simulation_name):
    from sirepo import simulation_db
    from sirepo.template import shadow
    for data in simulation_db.examples(shadow.SIM_TYPE):
        if data.models.simulation.name == simulation_name:
            return simulation_db.fixup_old_data(data)[0]
    assert False
