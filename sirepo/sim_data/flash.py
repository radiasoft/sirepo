# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
import sirepo.sim_data
import sirepo.util



class SimData(sirepo.sim_data.SimDataBase):

    _FLASH_PREFIX = 'flash4'
    _FLASH_SETUP_UNITS_PREFIX = 'setup_units'

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
    def flash_exe_path(cls, data):
        from pykern import pkio
        import distutils.spawn
        p = distutils.spawn.find_executable(
            '{}-{}'.format(
                cls._FLASH_PREFIX,
                data.models.simulation.flashType,
            ),
        )
        if p:
            return pkio.py_path(p)
        return  None

    @classmethod
    def flash_setup_units_path(cls, data):
        return cls.flash_exe_path(data).join(
            '..',
            '..',
            'share',
            cls._FLASH_PREFIX,
            f'{cls._FLASH_SETUP_UNITS_PREFIX}-{data.models.simulation.flashType}',
        )

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return [r]

    @classmethod
    def _lib_file_basenames(cls, data):
        t = data.models.simulation.flashType
        if t == 'RTFlame':
            return ['helm_table.dat']
        if t == 'CapLaser':
            return ['al-imx-004.cn4', 'h-imx-004.cn4']
        raise AssertionError('invalid flashType: {}'.format(t))
