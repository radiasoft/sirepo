# -*- coding: utf-8 -*-
u"""myapp simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkdebug import pkdp
from sirepo import simulation_db
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        s = cls.schema()
        for m in s.model:
            if m not in data.models:
                data.models[m] = pkcollections.Dict()
            cls.update_model_defaults(data.models[m], m, s)
        if data.models.simulation.flashType == 'CapLaser':
            io_model = data.models.IO
            io_model.plot_var_5 = 'magz'
            io_model.plot_var_6 = 'depo'
