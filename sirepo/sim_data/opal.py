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
        for cmd in dm.commands:
            if cmd._type == 'filter':
                cmd.type = cmd.type.upper()
            elif cmd._type == 'particlematterinteraction':
                cmd.material = cmd.material.upper()
        if 'bunchReport1' not in dm:
            for i in range(1, 5):
                m = dm['bunchReport{}'.format(i)] = PKDict()
                cls.update_model_defaults(m, 'bunchReport')
                if i == 1:
                    m.y = 'px'
                elif i == 2:
                    m.x = 'y'
                    m.y = 'py'
                elif i == 4:
                    m.x = 'z'
                    m.y = 'pz'

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if 'bunchReport' in analysis_model:
            return 'bunchReport'
        # twissReport2 and twissReport are compute_models
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if r == 'twissReport':
            return ['beamlines', 'elements', 'commands', 'simulation.activeBeamlineId', 'rpnVariables']
        if 'bunchReport' in r:
            return ['commands', 'rpnVariables']
        return []

    @classmethod
    def _lib_file_basenames(cls, data):
        return LatticeUtil(data, cls.schema()).iterate_models(lattice.InputFileIterator(cls)).result
