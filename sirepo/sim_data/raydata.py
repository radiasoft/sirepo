# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    pass

    @classmethod
    def fixup_old_data(cls, data):
        pass

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return []

    @classmethod
    def _lib_file_basenames(cls, data):
        return [data.models.analysisAnimation.notebook]
