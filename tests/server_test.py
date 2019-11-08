# -*- coding: utf-8 -*-
u"""Simple API test for app.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
try:
    import StringIO
except:
    from io import StringIO
import csv
import pytest
import re
import time
pytest.importorskip('srwl_bl')
pytest.importorskip('sdds')


_TYPES = 'elegant:jspec:myapp:srw'

def test_myapp_basic():
    from sirepo import srunit
    from pykern import pkunit
    fc = srunit.flask_client(sim_types=_TYPES)
    resp = fc.get('/old')
    assert 'LandingPageController' in resp.get_data(), \
        'Top level document is the landing page'
    resp = fc.get('/robots.txt')
    pkunit.pkre('elegant.*myapp.*srw', resp.get_data())


def test_elegant_data_file():
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from sirepo import srunit
    import sdds

    data, fc, sim_type = srunit.sim_data('elegant', 'bunchComp - fourDipoleCSR', sim_types=_TYPES)
    run = fc.sr_post(
        'runSimulation',
        PKDict(
            forceRun=False,
            models=data.models,
            report='bunchReport1',
            simulationId=data.models.simulation.simulationId,
            simulationType=data.simulationType,
        ),
    )
    pkunit.pkeq('pending', run.state, 'not pending, run={}', run)
    for _ in range(10):
        if run.state == 'completed':
            break
        run = fc.sr_post(
            'runStatus',
            run.nextRequest
        )
        time.sleep(1)
    else:
        pkunit.pkfail('runStatus: failed to complete: {}', run)
    resp = fc.sr_get(
        'downloadDataFile',
        PKDict(
            simulation_type=data.simulationType,
            simulation_id=data.models.simulation.simulationId,
            model='bunchReport1',
            frame='-1',
            suffix='csv',
        ),
    )
    rows = csv.reader(StringIO.StringIO(resp.get_data()))
    pkunit.pkeq(50001, len(list(rows)), '50,000 particles plus header row')
    resp = fc.sr_get(
        'downloadDataFile',
        PKDict(
            simulation_type=data.simulationType,
            simulation_id=data.models.simulation.simulationId,
            model='bunchReport1',
            frame='-1',
        ),
    )
    m = re.search(r'attachment; filename="([^"]+)"', resp.headers['Content-Disposition'])
    with pkunit.save_chdir_work():
        path = pkio.py_path(m.group(1))
        with open(str(path), 'w') as f:
            f.write(resp.get_data())
        assert sdds.sddsdata.InitializeInput(0, str(path)) == 1, \
            '{}: sdds failed to open'.format(path)
        # Verify we can read something
        assert 0 <= len(sdds.sddsdata.GetColumnNames(0))
        sdds.sddsdata.Terminate(0)


def test_jspec():
    from pykern import pkio
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdpretty
    from pykern.pkunit import pkeq, pkre
    from sirepo import srunit
    import json

    fc = srunit.flask_client(sim_types=_TYPES)
    sim_type = 'jspec'
    fc.sr_login_as_guest(sim_type)
    a = fc.sr_get_json(
        'listFiles',
        PKDict(simulation_type=sim_type, simulation_id='xxxxxxxxxx', file_type='ring-lattice'),
    )
    pkeq(['Booster.tfs'], a)


def test_srw():
    from pykern import pkio
    from pykern.pkdebug import pkdpretty
    from pykern.pkunit import pkeq, pkre
    from sirepo import srunit
    import json

    fc = srunit.flask_client(sim_types=_TYPES)
    sim_type = 'srw'
    r = fc.sr_get_root(sim_type)
    pkre('<!DOCTYPE html', r.data)
    fc.sr_login_as_guest(sim_type)
    d = fc.sr_post('listSimulations', {'simulationType': sim_type})
    pkeq(fc.get('/find-by-name-auth/srw/default/UndulatorRadiation').status_code, 404)
    for sep in (' ', '%20', '+'):
        pkeq(fc.get('/find-by-name-auth/srw/default/Undulator{}Radiation'.format(sep)).status_code, 200)
