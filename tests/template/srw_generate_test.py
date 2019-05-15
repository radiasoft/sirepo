# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.srw`

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
import pytest
import re
pytest.importorskip('srwl_bl')

def test_generate_all_optics():
    fc = _setup_client()
    from sirepo.template import srw
    from sirepo import srunit
    from sirepo.template import srw
    name = 'srw-all-optics'
    fn = pkunit.data_dir().join('{}.json'.format(name))
    (json, stream) = srunit.file_as_stream(fn)
    sim = fc.sr_post_form(
        'importFile',
        {
            'file': (stream, fn.basename),
            'folder': '/generate_test',
        },
        {'simulation_type': srw.SIM_TYPE},
    )
    _generate_source(fc, sim, name)


def test_generate_python():
    fc = _setup_client()
    from sirepo.template import srw

    for name in ('NSLS-II CHX beamline', 'Sample from Image', 'Boron Fiber (CRL with 3 lenses)', 'Tabulated Undulator Example', 'Gaussian X-ray beam through a Beamline containing Imperfect Mirrors', 'NSLS-II SRX beamline', 'NSLS-II ESM beamline', 'Mask example', 'NSLS-II SMI beamline'):
        sim = fc.sr_sim_data(srw.SIM_TYPE, name)
        _generate_source(fc, sim, name)


def _generate_source(fc, sim, name):
    from pykern.pkunit import pkeq
    resp = fc.sr_get(
        'pythonSource',
        {
            'simulation_id': sim['models']['simulation']['simulationId'],
            'simulation_type': sim['simulationType'],
        },
    )
    filename = '{}.py'.format(name.lower())
    filename = re.sub(r'\s', '-', filename)
    filename = re.sub(r'[^a-z0-9\-\.]', '', filename)
    with open(str(pkunit.work_dir().join(filename)), 'wb') as f:
        f.write(resp.data)
        expect = pkio.read_text(pkunit.data_dir().join(filename))
    pkeq(expect, resp.data)


def _setup_client():
    from sirepo import srunit
    fc = srunit.flask_client(sim_types='srw')
    fc.sr_login_as_guest('srw')
    return fc
