# -*- coding: utf-8 -*-
u"""test simulation list

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

def test_copy_non_session(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq, pkexcept, pkre
    import copy

    o = fc.sr_sim_data()
    i = o.models.simulation.simulationId
    fc.sr_logout()
    fc.sr_login_as_guest()
    r = fc.sr_get_json(
        'simulationData',
        PKDict(
            simulation_type=fc.sr_sim_type,
            pretty='0',
            simulation_id=i,
        ),
    )
    pkeq(i, r.redirect.simulationId)
    pkeq(None, r.redirect.userCopySimulationId)
    d = fc.sr_post(
        'copyNonSessionSimulation',
        PKDict(
            simulationId=i,
            simulationType=fc.sr_sim_type,
        ),
    )
    pkeq(i, d.models.simulation.outOfSessionSimulationId)
    # Try again
    r = fc.sr_get_json(
        'simulationData',
        PKDict(
            simulation_type=fc.sr_sim_type,
            pretty='0',
            simulation_id=i,
        ),
    )
    pkeq(d.models.simulation.simulationId, r.redirect.userCopySimulationId)


def test_illegals(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq, pkexcept, pkre
    import copy

    d = fc.sr_sim_data()
    for x in (
        (PKDict(name='new/sim'), ('newsim', '/folder')),
        (PKDict(name='some*sim'), ('somesim', '/folder')),
        (PKDict(folder='.foo'), ('name', '/foo')),
        (PKDict(name='s|&+?\'"im***\\'), ('sim', '/folder')),
        (PKDict(folder=''), 'blank folder'),
        (PKDict(name=''), 'blank name'),
        (PKDict(name='***'), 'blank name'),
    ):
        c = d.copy().pkupdate(folder='folder', name='name')
        r = fc.sr_post('newSimulation', c.pkupdate(x[0]))
        if 'error' in r:
            pkre(x[1], r.error)
        else:
            pkeq(r.models.simulation.name, x[1][0])
            pkeq(r.models.simulation.folder, x[1][1])


def test_rename_folder(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkeq
    import copy

    d = fc.sr_sim_data()
    d.pkupdate(
        name='new sim 1',
        folder='first folder',
    )
    r = fc.sr_post('newSimulation', d)
    pkeq('/' + d.folder, r.models.simulation.folder)
    d2 = copy.deepcopy(d)
    d2.pkupdate(
        name='new sim 2',
        folder='first folder no-match',
    )
    r2 = fc.sr_post('newSimulation', d2)
    n = 'new dir'
    fc.sr_post(
        'updateFolder',
        PKDict(
            newName=n,
            oldName=d.folder,
            simulationType=fc.sr_sim_type,
        ),
    )
    x = fc.sr_sim_data(d.name)
    pkeq('/' + n, x.models.simulation.folder)
    x = fc.sr_sim_data('new sim 2')
    pkeq(r2.models.simulation.folder, x.models.simulation.folder)


def test_srw_discard_example(fc):
    """Emulates what the GUI does"""
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    from pykern.pkunit import pkok

    # See https://github.com/radiasoft/sirepo/issues/1972
    n = 'Undulator Radiation'
    d = fc.sr_sim_data(n)
    fc.sr_post(
        'deleteSimulation',
        PKDict(
            simulationType=fc.sr_sim_type,
            simulationId=d.models.simulation.simulationId,
        ),
    )
    r = fc.sr_get(
        'findByNameWithAuth',
        PKDict(
            simulation_type=fc.sr_sim_type,
            application_mode='default',
            simulation_name=n
        ),
        redirect=False,
    )
    i = r.headers['Location'].split('/').pop()
    r = fc.sr_get(
        'pythonSource',
        PKDict(
            simulation_type=fc.sr_sim_type,
            simulation_id=i,
        ),
    )
    pkok('srwl_bl.SRWLBeamline' in r.data, 'incomplete python={}', r.data)
