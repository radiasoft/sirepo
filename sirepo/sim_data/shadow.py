# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        if (
            float(data.fixup_old_version) < 20170703.000001
            and 'geometricSource' in dm
        ):
            g = data.models.geometricSource
            x = g.cone_max
            g.cone_max = g.cone_min
            g.cone_min = x
        cls.init_models(dm, ('initialIntensityReport', 'plotXYReport'))
        for m in dm:
            if cls.is_watchpoint(m):
                cls.update_model_defaults(dm[m], 'watchpointReport')
        cls.organize_example(data)
