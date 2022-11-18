# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def fixup_old_data(cls, data, **kwargs):
        pass

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model, **kwargs):
        return [
            data.report,
            "sauce",
        ]

    @classmethod
    def _lib_file_basenames(cls, *args, **kwargs):
        return ["a-lib-file.txt"]
