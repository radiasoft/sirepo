# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def _compute_model(cls, analysis_model, data):
        return analysis_model


    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls._init_models(
            dm,
            (
                'dicomSettings',
                'dicomWindow',
                'doseWindow',
            ),
        )

    @classmethod
    def lib_file_for_sim(cls, data, filename):
        return '{}-{}'.format(
            data.models.simulation.libFilePrefix,
            filename,
        )

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return [r]

    @classmethod
    def _lib_file_basenames(cls, data):
        r = data.get('report')
        res = []
        if not r:
            #TODO(pjm): share filenames with template.irad
            res += ['dvh-data.json', 'ct.zip','rtdose.zip','rtdose2.zip', 'rtstruct-data.json']
        elif r == 'dvhReport':
            res += ['dvh-data.json']
        elif r == 'dicom3DReport':
            res += ['ct.zip','rtdose.zip','rtdose2.zip', 'rtstruct-data.json']
        else:
            assert False, 'unknown report: {}'.format(r)
        return [cls.lib_file_for_sim(data, v) for v in res]
