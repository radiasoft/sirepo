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


def test_basic():
    from sirepo import srunit
    from pykern import pkunit
    fc = srunit.flask_client(sim_types='elegant:srw:myapp')
    resp = fc.get('/old')
    assert 'LandingPageController' in resp.get_data(), \
        'Top level document is the landing page'
    resp = fc.get('/robots.txt')
    pkunit.pkre('elegant.*myapp.*srw', resp.get_data())


def test_get_data_file():
    from sirepo import srunit
    from pykern import pkunit
    from pykern import pkio
    import sdds

    fc = srunit.flask_client(sim_types='elegant:srw:myapp')
    sim_type = 'elegant'
    fc.sr_login_as_guest(sim_type)
    data = fc.sr_post(
        'listSimulations',
        {'simulationType': sim_type, 'search': {'simulationName': 'fourDipoleCSR'}},
    )
    data = data[0].simulation
    data = fc.sr_get_json(
        'simulationData',
        params=dict(
            pretty='1',
            simulation_id=data.simulationId,
            simulation_type=sim_type,
        ),
    )
    run = fc.sr_post(
        'runSimulation',
        dict(
            forceRun=False,
            models=data.models,
            report='bunchReport1',
            simulationId=data.models.simulation.simulationId,
            simulationType=data.simulationType,
        ),
    )
    for _ in range(10):
        run = fc.sr_post(
            'runStatus',
            run.nextRequest
        )
        if run.state == 'completed':
            break
        time.sleep(1)
    else:
        pkunit.pkfail('runStatus: failed to complete: {}', run)
    resp = fc.sr_get(
        'downloadDataFile',
        dict(
            simulation_type=data.simulationType,
            simulation_id=data.models.simulation.simulationId,
            model='bunchReport1',
            frame='-1',
            suffix='csv',
        ),
    )
    rows = csv.reader(StringIO.StringIO(resp.get_data()))
    assert len(list(rows)) == 5001
    resp = fc.sr_get(
        'downloadDataFile',
        dict(
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


def test_srw():
    from pykern import pkio
    from pykern.pkdebug import pkdpretty
    from pykern.pkunit import pkeq, pkre
    from sirepo import srunit
    import json

    fc = srunit.flask_client(sim_types='elegant:srw:myapp')
    sim_type = 'srw'
    r = fc.sr_get_root(sim_type)
    pkre('<!DOCTYPE html', r.data)
    fc.sr_login_as_guest(sim_type)
    d = fc.sr_post('listSimulations', {'simulationType': sim_type})
    pkeq(fc.get('/find-by-name/srw/default/UndulatorRadiation').status_code, 404)
    for sep in (' ', '%20', '+'):
        pkeq(fc.get('/find-by-name/srw/default/Undulator{}Radiation'.format(sep)).status_code, 200)
