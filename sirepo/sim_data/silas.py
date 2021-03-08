# -*- coding: utf-8 -*-
u"""SILAS simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
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
                'crystalAnimation',
                'crystalCylinder',
                'crystalSettings',
                'gaussianBeam',
                'plotAnimation',
                'plot2Animation',
                'simulation',
                'simulationSettings',
                'wavefrontSummaryAnimation',
            ),
        )
        for m in dm.beamline:
            cls.update_model_defaults(m, m.type)

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model in ('crystalAnimation', 'plotAnimation', 'plot2Animation'):
            return 'crystalAnimation'
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = []
        return res

    @classmethod
    def _lib_file_basenames(cls, data):
        return []
