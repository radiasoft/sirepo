# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    ANALYSIS_ONLY_FIELDS = frozenset(('colorMap', 'name', 'notes', 'scaling'))
    GEOM_FILE = 'geom.h5'
    BEAM_TO_SYMMETRY = PKDict(
        x='0.0, 0.0, 1.0',
        y='0.0, 0.0, 1.0',
        z='1.0, 0.0, 0.0',
    )

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = cls._non_analysis_fields(data, r) + []
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model in (
            'solver',
        ):
            return 'animation'
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def __dynamic_defaults(cls, data, model):
        """defaults that depend on the current data"""
        if model not in ('geomObject',):
            return PKDict()
        #beam_axis = data.models.simulation.beamAxis
        #return PKDict(
        #    symmetryPlane=cls.BEAM_TO_SYMMETRY[beam_axis],
        #)
        return PKDict()

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls._init_models(
            dm,
            None,
            dynamic=lambda m: cls.__dynamic_defaults(data, m)
        )
        cls._organize_example(data)

    #@classmethod
    #def _compute_job_fields(cls, data, *args, **kwargs):
    #    return [
    #        data.report,
    #    ]

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        if 'fieldType' in data:
            res.append(cls.lib_file_name_with_model_field(
                'fieldPath',
                data.fieldType,
                data.name + '.' + data.fileType))
        return res
