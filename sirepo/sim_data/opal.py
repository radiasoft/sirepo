# -*- coding: utf-8 -*-
u"""synergia simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data

class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls._init_models(
            dm,
            (
                'bunchAnimation',
                'plotAnimation',
            ),
        )

    @classmethod
    def _compute_job_fields(cls, data, compute_model):
        if compute_model == 'twissReport':
            return ['beamlines', 'elements', 'simulation.activeBeamlineId']
        return []

    @classmethod
    def _lib_files(cls, data):
        return []
