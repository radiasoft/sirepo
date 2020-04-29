# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls._init_models(dm)
        if dm.simulation.flashType == 'CapLaser':
            dm.IO.update(
                plot_var_5='magz',
                plot_var_6='depo',
            )

    @classmethod
    def flash_setup_units_path(cls, data):
        return cls.lib_file_resource_dir().join(
            '{}.setup_units'.format(data.models.simulation.flashType),
        )

    @classmethod
    def proprietary_lib_file_basenames(cls):
        return ['CapLaser']

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return [r]

    @classmethod
    def _lib_file_basenames(cls, data):
        t = data.models.simulation.flashType
        #return ['flash.par', 'al-imx-004.cn4', 'h-imx-004.cn4']
        #return ['flash.par', 'helm_table.dat']
        if t == 'RTFlame':
            return ['helm_table.dat']
        if t == 'CapLaser':
            return ['al-imx-004.cn4', 'h-imx-004.cn4']
        raise AssertionError('invalid flashType: {}'.format(t))
