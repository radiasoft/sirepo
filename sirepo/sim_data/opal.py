# -*- coding: utf-8 -*-
u"""synergia simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template import lattice
from sirepo.template.lattice import LatticeUtil
import re
import sirepo.sim_data

class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        dm.setdefault('rpnVariables', [])
        cls._init_models(
            dm,
            (
                'bunchAnimation',
                'plotAnimation',
                'plot2Animation',
                'twissReport',
            ),
        )

        # TODO(pjm): remove before check-in
        track = None
        commands = []
        for cmd in dm.commands:
            if cmd._type == 'track':
                track = cmd
            elif cmd._type == 'run':
                assert track, 'missing track for run'
                for f in cmd:
                    if f in ('name', '_type'):
                        continue
                    track['run_{}'.format(f)] = cmd[f]
                continue
            commands.append(cmd)
        dm.commands = commands


    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if r == 'twissReport':
            return ['beamlines', 'elements', 'commands', 'simulation.activeBeamlineId']
        return []

    @classmethod
    def _lib_file_basenames(cls, data):
        return LatticeUtil(data, cls.schema()).iterate_models(lattice.InputFileIterator(cls)).result
