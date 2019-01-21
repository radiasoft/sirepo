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

def test_generate_python():
    from pykern import pkio
    from pykern.pkunit import pkeq
    from sirepo.template import srw
    from sirepo import srunit
    fc = srunit.flask_client()
    fc.get('/{}'.format(srw.SIM_TYPE))

    for name in ('NSLS-II CHX beamline', 'Sample from Image', 'Boron Fiber (CRL with 3 lenses)', 'Tabulated Undulator Example', 'Gaussian X-ray beam through a Beamline containing Imperfect Mirrors', 'NSLS-II SRX beamline', 'NSLS-II ESM beamline', 'Mask example', 'NSLS-II SMI beamline'):
        sim = fc.sr_sim_data(srw.SIM_TYPE, name)
        resp = fc.sr_get(
            'pythonSource',
            {
                'simulation_id': sim['models']['simulation']['simulationId'],
                'simulation_type': srw.SIM_TYPE,
            },
            raw_response=True,
        )
        filename = '{}.py'.format(name.lower())
        filename = re.sub(r'\s', '-', filename)
        filename = re.sub(r'[^a-z0-9\-\.]', '', filename)
        with open(str(pkunit.work_dir().join(filename)), 'wb') as f:
            f.write(resp.data)
            expect = pkio.read_text(pkunit.data_dir().join(filename))
        pkeq(expect, resp.data)
