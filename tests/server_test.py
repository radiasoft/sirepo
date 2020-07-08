# -*- coding: utf-8 -*-
u"""Simple API test for app.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import csv
import pytest
import re
import six
import time


def test_elegant_data_file(fc):
    from pykern import pkunit, pkcompat, pkio
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
    r = fc.sr_get(
        'downloadDataFile',
        PKDict(
            simulation_type=data.simulationType,
            simulation_id=data.models.simulation.simulationId,
            model='bunchReport1',
            frame='-1',
            suffix='csv',
        ),
    )
    pkunit.pkeq(200, r.status_code)
    pkunit.pkre('no-cache', r.headers.get('Cache-Control'))
    rows = csv.reader(six.StringIO(pkcompat.from_bytes(r.data)))
    pkunit.pkeq(50001, len(list(rows)), '50,000 particles plus header row')
    r = fc.sr_get(
        'downloadDataFile',
        PKDict(
            simulation_type=data.simulationType,
            simulation_id=data.models.simulation.simulationId,
            model='bunchReport1',
            frame='-1',
        ),
    )
    pkunit.pkeq(200, r.status_code)
    m = re.search(
        r'attachment; filename="([^"]+)"',
        r.headers.get('Content-Disposition'),
    )
    d = pkunit.work_dir()
    path = d.join(m.group(1))
    path.write_binary(r.data)
    assert sdds.sddsdata.InitializeInput(0, str(path)) == 1, \
        '{}: sdds failed to open'.format(path)
    # Verify we can read something
    assert 0 <= len(sdds.sddsdata.GetColumnNames(0))
    sdds.sddsdata.Terminate(0)


def test_myapp_basic(fc):
    from pykern import pkunit, pkcompat
    from pykern.pkunit import pkok

    r = fc.get('/robots.txt')
    pkunit.pkre('elegant.*myapp.*srw', pkcompat.from_bytes(r.data))

    r = fc.get('/en/landing.html')
    pkok(
        not re.search(
            r'googletag',
            pkcompat.from_bytes(r.data)
        ),
        'Unexpected injection of googletag data={}',
        r.data
    )


def test_srw(fc):
    from pykern import pkio, pkcompat
    from pykern.pkdebug import pkdpretty
    from pykern.pkunit import pkeq, pkre
    import json

    r = fc.sr_get_root()
    pkre('<!DOCTYPE html', pkcompat.from_bytes(r.data))
    d = fc.sr_post('listSimulations', {'simulationType': fc.sr_sim_type})
    pkeq(fc.get('/find-by-name-auth/srw/default/UndulatorRadiation').status_code, 404)
    for sep in (' ', '%20', '+'):
        pkeq(fc.get('/find-by-name-auth/srw/default/Undulator{}Radiation'.format(sep)).status_code, 200)


def test_synergia_data_file(fc):
    from pykern import pkunit, pkcompat, pkio
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    import h5py

    data = fc.sr_sim_data('IOTA 6-6 Bare')
    run = fc.sr_post(
        'runSimulation',
        PKDict(
            forceRun=True,
            models=data.models,
            report='animation',
            simulationId=data.models.simulation.simulationId,
            simulationType=data.simulationType,
        ),
    )
    pkunit.pkeq('pending', run.state, 'not pending, run={}', run)
    for _ in range(20):
        if run.state == 'completed':
            break
        run = fc.sr_post(
            'runStatus',
            run.nextRequest
        )
        time.sleep(1)
    else:
        pkunit.pkfail('runStatus: failed to complete: {}', run)
    r = fc.sr_get(
        'downloadDataFile',
        PKDict(
            simulation_type=data.simulationType,
            simulation_id=data.models.simulation.simulationId,
            model='bunchAnimation',
            frame='1',
        ),
    )
    pkunit.pkeq(200, r.status_code)
    m = re.search(
        r'attachment; filename="([^"]+)"',
        r.headers.get('Content-Disposition'),
    )
    d = pkunit.work_dir()
    path = d.join(m.group(1))
    path.write_binary(r.data)
    with h5py.File(str(path), 'r') as f:
        pkunit.pkok(f['charge'], 'missing charge from {}', path)
    r = fc.sr_get(
        'downloadDataFile',
        PKDict(
            simulation_type=data.simulationType,
            simulation_id=data.models.simulation.simulationId,
            model='beamEvolutionAnimation',
            frame='1',
        ),
    )
    pkunit.pkeq(200, r.status_code)
    m = re.search(
        r'attachment; filename="([^"]+)"',
        r.headers.get('Content-Disposition'),
    )
    d = pkunit.work_dir()
    path = d.join(m.group(1))
    path.write_binary(r.data)
    with h5py.File(str(path), 'r') as f:
        pkunit.pkok(f['num_particles'], 'missing num_particles from {}', path)
