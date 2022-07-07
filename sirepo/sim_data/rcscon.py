# -*- coding: utf-8 -*-
u"""RCSCON simulation data operations

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
                'dataSource',
                'elegantAnimation',
                'epochAnimation',
                'files',
                'latticeSettings',
                'mlModel',
                'mlModelGraph',
                'neuralNet',
                'neuralNetLayer',
                'partition',
                'partitionSelectionReport',
                'rfcSettings',
            ))
        if 'beamlines' not in dm:
            from sirepo import simulation_db
            defaults = simulation_db.default_data(cls.sim_type()).models
            for m in ('beamlines', 'commands', 'elements', 'rpnCache', 'rpnVariables'):
                dm[m] = defaults[m]

    @classmethod
    def rcscon_filename(cls, data, model, field):
        if data.models.dataSource.source == 'elegant':
            return '../elegantAnimation/{}.csv'.format(field)
        return cls.lib_file_name_with_model_field(model, field, data.models[model][field])

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if 'fileColumnReport' in r or r == 'partitionSelectionReport':
            return ['files', 'dataSource', 'elegantAnimation']
        return []

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if 'fileColumnReport' in analysis_model:
            return 'fileColumnReport'
        if analysis_model == 'epochAnimation' or 'fitAnimation' in analysis_model:
            return 'animation'
        if 'partitionAnimation' in analysis_model:
            return 'partitionAnimation'
        return analysis_model

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        if data.models.dataSource.source == 'files':
            files = data.models.files
            if files.get('inputs'):
                res.append(cls.rcscon_filename(data, 'files', 'inputs'))
            if files.get('outputs'):
                res.append(cls.rcscon_filename(data, 'files', 'outputs'))
        return res
