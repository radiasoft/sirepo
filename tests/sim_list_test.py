# -*- coding: utf-8 -*-
u"""test simulation list

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_rename_folder(fc):
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq
    import copy

    d = fc.sr_sim_data()
    d.pkupdate(
        name='new sim 1',
        folder='first folder',
    )
    fc.sr_post('newSimulation', d)
    d2 = copy.deepcopy(d)
    d2.pkupdate(
        name='new sim 2',
        folder='first folder no-match',
    )
    fc.sr_post('newSimulation', d2)
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
    pkeq(n, x.models.simulation.folder)
    x = fc.sr_sim_data('new sim 2')
    pkeq(d2.folder, x.models.simulation.folder)
