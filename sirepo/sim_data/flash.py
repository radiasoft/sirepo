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

    FLASH_RPM_FILENAME = 'flash.rpm'
    _FLASH_EXE_PREFIX = 'flash4'
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
    def flash_exe_name(cls, data):
        return '{}-{}'.format(
            cls._FLASH_EXE_PREFIX,
            data.models.simulation.flashType,
        )

    @classmethod
    def flash_setup_units_path(cls, data):
        return pkio.py_path(
            # TODO(e-carlin): talk with rn about sharing this path better with installer
            '/home/vagrant/.local/share/flash4/{}-{}'.format(
                cls._FLASH_SETUP_UNITS_PREFIX,
                data.models.simulation.flashType,
            )
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
