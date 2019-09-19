# -*- coding: utf-8 -*-
u"""myapp simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp
from pykern import pkinspect
import sirepo.sim_data
from sirepo import simulation_db


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        for m in cls.schema().model:
            if m not in data.models:
                data.models[m] = pkcollections.Dict()
            cls.update_model_defaults(data.models[m], m, cls.schema())
