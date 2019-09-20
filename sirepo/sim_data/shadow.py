# -*- coding: utf-8 -*-
u"""myapp simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkinspect
from sirepo import simulation_db
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        if (
            float(data.fixup_old_version) < 20170703.000001
            and 'geometricSource' in data.models
        ):
            g = data.models.geometricSource
            x = g.cone_max
            g.cone_max = g.cone_min
            g.cone_min = x
        for m in [
            'initialIntensityReport',
            'plotXYReport',
        ]:
            if m not in data.models:
                data.models[m] = pkcollections.Dict()
            cls.update_model_defaults(data.models[m], m, cls.schema())
        for m in data.models:
            if cls.is_watchpoint(m):
                cls.update_model_defaults(data.models[m], 'watchpointReport', cls.schema())
        cls.organize_example(data)
