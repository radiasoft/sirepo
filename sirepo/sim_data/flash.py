# -*- coding: utf-8 -*-
u"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern import pkio
from pykern.pkdebug import pkdp
import re
import sirepo.sim_data
import sirepo.util



class SimData(sirepo.sim_data.SimDataBase):

    FLASH_PREFIX = 'flash4'
    # TODO(e-carlin): Where are we going to put these files?
    _FLASH_SETUP_UNITS_PREFIX = 'setup_units'

    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        for m in list(dm.keys()):
            n = m
            for x in (':', ''), ('magnetoHD', ''), ('CapLaser$', 'CapLaserBELLA'):
                n = re.sub(x[0], x[1], n)
            if m != n:
                dm[n] = dm[m]
                del dm[m]
        cls._init_models(dm)
        if dm.simulation.flashType == 'CapLaser':
            dm.simulation.flashType = 'CapLaserBELLA'
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
                m = dm['physicsmaterialPropertiesOpacityMultispecies']
                m.op_fillFileName = 'helium-fill-imx.cn4'
                m.op_wallFileName  = 'alumina-wall-imx.cn4'
                m.op_fillFileType = 'ionmix4'
                m.op_wallFileType = 'ionmix4'
        dm['physicssourceTermsEnergyDepositionLaser'].pkdel('ed_gridnAngularTics_1')
        for n in 'currType', 'eosFill', 'eosWall':
            dm.pkdel(f'SimulationCapLaserBELLA{n}')
        m = dm.physicssourceTermsHeatexchange
        if 'useHeatExchange' in m:
            m.useHeatexchange = m.useHeatExchange
            m.pkdel('useHeatExchange')
        m = dm.gridEvolutionAnimation
        if 'valueList' not in m:
            m.valueList = PKDict()
            for x in 'y1', 'y2', 'y3':
                if dm.simulation.flashType in ('CapLaserBELLA', 'CapLaser3D'):
                    m.valueList[x] = [
                        'mass',
                        'x-momentum',
                        'y-momentum',
                        'z-momentum',
                        'E_total',
                        'E_kinetic',
                        'E_internal',
                        'MagEnergy',
                        'r001',
                        'r002',
                        'r003',
                        'r004',
                        'r005',
                        'r006',
                        'sumy',
                        'ye',
                    ]
                elif dm.simulation.flashType == 'RTFlame':
                    m.valueList[x] = [
                        'mass',
                        'x-momentum',
                        'y-momentum',
                        'z-momentum',
                        'E_total',
                        'E_kinetic',
                        'E_turbulent',
                        'E_internal',
                        'Burned Mass',
                        'dens_burning_ave',
                        'db_ave samplevol',
                        'Burning rate',
                        'fspd to input_fspd ratio',
                        'surface area flam=0.1',
                        'surface area flam=0.5',
                        'surface area flam=0.9',
                    ]

    @classmethod
    def flash_setup_units_path(cls, data):
        # TODO(e-carlin): I've moved ~/.local/share/flash4 to ~/.local/share/flash
        # I did this manually on my machine. Need to update the RPM code.
        # Also, after compilation need to start putting the setup_units files in the
        # sim_dir and pulling them in in prepare_simulation.
        return cls.local_path('share').join(
            f'{cls._FLASH_SETUP_UNITS_PREFIX}-{data.models.simulation.flashType}',
        )

    @classmethod
    def proprietary_code_rpm(cls):
        return cls._proprietary_code_rpm()

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return [r]

    @classmethod
    def _lib_file_basenames(cls, data):
        t = data.models.simulation.flashType
        if t == 'RTFlame':
            return ['helm_table.dat']
        if 'CapLaser' in t:
            r = [
                'alumina-wall-imx.cn4',
                'argon-fill-imx.cn4',
                'helium-fill-imx.cn4',
                'hydrogen-fill-imx.cn4',
            ]
            if t == 'CapLaserBELLA'  and data.models['SimulationCapLaserBELLA'].sim_currType == '2':
                r.append(cls.lib_file_name_with_model_field(
                    'SimulationCapLaserBELLA',
                    'sim_currFile',
                    data.models['SimulationCapLaserBELLA'].sim_currFile,
                ))
            return r
        raise AssertionError('invalid flashType: {}'.format(t))

    # TODO(e-carlin): sort
    @classmethod
    def _sim_file_basenames(cls, data):
        def _hash():
            # TODO(e-carlin): get data and create a hash of the compilation
            # params
            return '123'
        return [f'{cls.FLASH_PREFIX}-{_hash()}']
