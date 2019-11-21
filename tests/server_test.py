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


def test_myapp_basic(fc):
    from pykern import pkunit

    resp = fc.get('/old')
    assert 'LandingPageController' in resp.get_data(), \
        'Top level document is the landing page'
    resp = fc.get('/robots.txt')
    pkunit.pkre('elegant.*myapp.*srw', resp.get_data())


def test_elegant_data_file(fc):
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    import sdds

    data = fc.sr_sim_data('bunchComp - fourDipoleCSR')
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
    pkunit.pkre('no-cache', resp.headers['Cache-Control'])
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


def test_srw(fc):
    from pykern import pkio
    from pykern.pkdebug import pkdpretty
    from pykern.pkunit import pkeq, pkre
    import json

    r = fc.sr_get_root()
    pkre('<!DOCTYPE html', r.data)
    fc.sr_login_as_guest()
    d = fc.sr_post('listSimulations', {'simulationType': fc.sr_sim_type})
    pkeq(fc.get('/find-by-name-auth/srw/default/UndulatorRadiation').status_code, 404)
    for sep in (' ', '%20', '+'):
        pkeq(fc.get('/find-by-name-auth/srw/default/Undulator{}Radiation'.format(sep)).status_code, 200)
