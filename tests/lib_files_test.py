# -*- coding: utf-8 -*-
u"""lib files interface

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_srw_delete(fc):
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    import sirepo.sim_data

    d = fc.sr_sim_data('Tabulated Undulator Example')
    s = sirepo.sim_data.get_class(fc.sr_sim_type)
    u = pkunit.work_dir().join('not_used_name.zip')
    s.lib_file_resource_dir().join('magnetic_measurements.zip').copy(u)
    t = 'undulatorTable'
    d.models.tabulatedUndulator.magneticFile = u.basename
    r = fc.sr_post(
        'saveSimulationData',
        data=d,
        file=u,
    )
    pkunit.pkeq(u.basename, r.models.tabulatedUndulator.magneticFile)
    r = fc.sr_post_form(
        'uploadFile',
        params=PKDict(
            simulation_type=fc.sr_sim_type,
            simulation_id=d.models.simulation.simulationId,
            file_type=t,
        ),
        data=PKDict(),
        file=u,
    )
    pkunit.pkeq(u.basename, r.get('filename'), 'unexpected response={}', r)
    r = fc.sr_post(
        'deleteFile',
        PKDict(
            fileType=t,
            filename=u.basename,
            simulationType=fc.sr_sim_type,
        ),
    )
    pkunit.pkre('in use', r.get('error', ''))
    fc.sr_post(
        'deleteSimulation',
        PKDict(
            simulationType=fc.sr_sim_type,
            simulationId=d.models.simulation.simulationId,
        ),
    )
    r = fc.sr_post(
        'deleteFile',
        PKDict(
            fileType=t,
            filename=u.basename,
            simulationType=fc.sr_sim_type,
        ),
    )
    pkunit.pkeq('ok', r.get('state'), 'unexpected response={}', r)
    r = fc.sr_get_json(
        'downloadFile',
        params=PKDict(
            simulation_type=fc.sr_sim_type,
            simulation_id=d.models.simulation.simulationId,
            filename=u.basename,
        ),
        data=PKDict(),
        redirect=False,
    )
    pkunit.pkre('does not exist', r.error)


def test_jspec_list_files(fc):
    from pykern import pkio
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdpretty
    from pykern.pkunit import pkeq, pkre
    import json

    a = fc.sr_get_json(
        'listFiles',
        PKDict(simulation_type=fc.sr_sim_type, simulation_id='xxxxxxxxxx', file_type='ring-lattice'),
    )
    pkeq(['Booster.tfs'], a)


def test_srw_upload(fc):
    from pykern import pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp
    import sirepo.sim_data

    d = fc.sr_sim_data('NSLS-II CHX beamline')
    s = sirepo.sim_data.get_class(fc.sr_sim_type)
    f = s.lib_file_resource_dir().join('mirror_1d.dat')
    t = 'mirror'
    r = fc.sr_post_form(
        'uploadFile',
        params=PKDict(
            simulation_type=fc.sr_sim_type,
            simulation_id=d.models.simulation.simulationId,
            file_type=t,
        ),
        data=PKDict(),
        file=f,
    )
    pkunit.pkre('in use in other', r.get('error', ''))
    r = fc.sr_post_form(
        'uploadFile',
        params=PKDict(
            simulation_type=fc.sr_sim_type,
            simulation_id=d.models.simulation.simulationId,
            file_type=t,
        ),
        data=PKDict(confirm='1'),
        file=f,
    )
    e = r.get('error', '')
    pkunit.pkok(not e, 'unexpected error={}', e)
    r = fc.sr_post_form(
        'uploadFile',
        params=PKDict(
            simulation_type=fc.sr_sim_type,
            simulation_id=d.models.simulation.simulationId,
            file_type='invalid file type',
        ),
        data=PKDict(),
        file=f,
    )
    pkunit.pkre('invalid file type', r.get('error', ''))
    # the above used to delete the file
    r = fc.sr_get(
        'downloadFile',
        params=PKDict(
            simulation_type=fc.sr_sim_type,
            simulation_id=d.models.simulation.simulationId,
            filename=f.basename,
        ),
        data=PKDict(),
    )
    pkunit.pkre(r'^\s*-1.39500', r.data)
