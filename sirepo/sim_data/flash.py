# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp
import sirepo.sim_data
import sirepo.util



class SimData(sirepo.sim_data.SimDataBase):

    _FLASH_PREFIX = 'flash4'
    _FLASH_SETUP_UNITS_PREFIX = 'setup_units'

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls._init_models(dm)
        if dm.simulation.flashType == 'CapLaserBELLA':
            dm.IO.update(
                plot_var_5='magz',
                plot_var_6='depo',
            )
            if not dm.Multispecies.ms_fillSpecies:
                m = dm.Multispecies
                m.ms_fillSpecies = 'hydrogen'
                m.ms_wallSpecies = 'alumina'
                m.eos_fillTableFile = 'helium-fill-imx.cn4'
                m.eos_wallTableFile = 'alumina-wall-imx.cn4'
                m.eos_fillSubType = 'ionmix4'
                m.eos_wallSubType = 'ionmix4'
                m = dm['physics:materialProperties:Opacity:Multispecies']
                m.op_fillFileName = 'helium-fill-imx.cn4'
                m.op_wallFileName  = 'alumina-wall-imx.cn4'
                m.op_fillFileType = 'ionmix4'
                m.op_wallFileType = 'ionmix4'
        dm['physics:sourceTerms:EnergyDeposition:Laser'].pkdel('ed_gridnAngularTics_1')

    @classmethod
    def flash_exe_path(cls, data, unchecked=False):
        from pykern import pkio
        import distutils.spawn
        n = '{}-{}'.format(
            cls._FLASH_PREFIX,
            data.models.simulation.flashType,
        )
        p = distutils.spawn.find_executable(n)
        if p:
            return pkio.py_path(p)
        if unchecked:
            return  None
        raise AssertionError(f'unable to find executable={n}')

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
        if t == 'CapLaserBELLA':
            return [
                'alumina-wall-imx.cn4',
                'argon-fill-imx.cn4',
                'helium-fill-imx.cn4',
                'hydrogen-fill-imx.cn4',
            ]
        raise AssertionError('invalid flashType: {}'.format(t))
