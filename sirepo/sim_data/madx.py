# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data
from sirepo.template.lattice import LatticeUtil

class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls._init_models(
            dm,
            (
                'bunch',
                'simulation',
            ),
        )
        for container in ('commands', 'elements'):
            for m in dm[container]:
                cls.update_model_defaults(m, LatticeUtil.model_name_for_data(m))


    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = []
        if 'bunchReport' in compute_model:
            res += ['bunch', 'commands', 'rpnVariables', 'simulation.visualizationBeamlineId']
        if r == 'twissReport':
            res += ['beamlines', 'elements', 'simulation.activeBeamlineId', 'rpnVariables']
        if 'twissEllipseReport' in compute_model:
            res += [r, 'commands', 'rpnVariables']
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if 'bunchReport' in analysis_model:
            return 'bunchReport'
        if 'twissEllipseReport' in analysis_model:
            return 'twissEllipseReport'
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _lib_file_basenames(cls, data):
        # TODO(e-carlin): impl
        return []
