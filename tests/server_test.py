# -*- coding: utf-8 -*-
u"""Simple API test for app.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
try:
    import StringIO
except:
    import io as StringIO
import csv
import pytest
import re
import time
pytest.importorskip('srwl_bl')
pytest.importorskip('sdds')


def test_basic():
    from sirepo import sr_unit
    fc = sr_unit.flask_client()
    resp = fc.get('/')
    assert 'LandingPageController' in resp.get_data(), \
        'Top level document is the landing page'


def test_get_data_file():
    from sirepo import sr_unit
    from pykern import pkunit
    from pykern import pkio
    import sdds

    fc = sr_unit.flask_client()
    fc.get('/elegant')
    data = fc.sr_post(
        'listSimulations',
        {'simulationType': 'elegant', 'search': {'simulationName': 'fourDipoleCSR'}},
    )
    data = data[0].simulation
    data = fc.sr_get(
        'simulationData',
        params=dict(
            pretty='1',
            simulation_id=data.simulationId,
            simulation_type='elegant',
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
        raw_response=True,
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
        raw_response=True,
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
    from sirepo import sr_unit
    import json

    fc = sr_unit.flask_client()
    resp = fc.get('/srw')
    assert '<!DOCTYPE html' in resp.get_data(), \
        'Top level document is html'
    data = fc.sr_post(
        'listSimulations',
        {'simulationType': 'srw', 'search': ''},
    )
