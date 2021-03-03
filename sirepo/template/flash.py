# -*- coding: utf-8 -*-
u"""FLASH execution template.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import glob
import h5py
import numpy as np
import re
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

_GRID_EVOLUTION_FILE = 'flash.dat'
_PLOT_FILE_PREFIX = 'flash_hdf5_plt_cnt_'
_DEFAULT_VALUES = {
    'RTFlame': {
        'Driver': {
            'dtinit': 1e-09,
            'dtmin': 1e-09,
            'nend': 99999,
            'tmax': 0.5,
        },
        'Grid': {
            'xl_boundary_type': 'reflect',
            'xmax': 6000000,
            'xr_boundary_type': 'outflow',
            'ymax': 750000,
            'ymin': -750000,
            'zmax': 750000,
            'zmin': -750000,
        },
        'gridEvolutionAnimation': {
            'y1': 'mass',
            'y2': 'Burned Mass',
            'y3': 'Burning rate',
            'valueList': {
                'y1': [],
                'y2': [],
                'y3': [],

            }
        },
        'Gridparamesh': {
            'lrefine_max': 3,
            'nblockx': 4,
            'refine_var_1': 'dens',
            'refine_var_2': 'flam',
        },
        'IO': {
            'plot_var_1': 'dens',
            'plotFileIntervalTime': 0.01,
        },
        'physicsGravityConstant': {
            'gconst': -1900000000,
        },
        'physicssourceTermsFlameFlameEffectsEIP': {
            'flame_deltae': 280000000000000000,
            'sumyi_burned': 0.072917,
            'sumyi_unburned': 0.041667,
        },
        'physicssourceTermsFlameFlameSpeedConstant': {
            'fl_fsConstFlameSpeed': 2000000,
        },
        'problemFiles': {
            'archive': None
        },
        'setupArguments': {
            'auto': '1',
            'd': 2,
            'nxb': 16,
            'nyb': 16
        },
        'setupConfigDirectives': [
            {
                '_id': 1,
                '_type': 'REQUIRES',
                'unit': 'Driver'
            },
            {
                '_id': 2,
                '_type': 'REQUIRES',
                'unit': 'physics/Hydro'
            },
            {
                '_id': 3,
                '_type': 'REQUIRES',
                'unit': 'physics/Gravity/GravityMain/Constant'
            },
            {
                '_id': 4,
                '_type': 'REQUIRES',
                'unit': 'physics/sourceTerms/Flame/FlameEffects/EIP'
            },
            {
                '_id': 5,
                '_type': 'REQUIRES',
                'unit': 'flashUtilities/contourSurface'
            },
            {
                '_id': 6,
                '_type': 'REQUESTS',
                'unit': 'physics/sourceTerms/Flame/FlameSpeed/Constant'
            },
            {
                '_id': 7,
                '_type': 'PARAMETER',
                'default': 100000000.0,
                'name': 'temp_unburned',
                'type': 'REAL',
            },
            {
                '_id': 8,
                '_type': 'PARAMETER',
                'default': 100000000.0,
                'name': 'dens_unburned',
                'type': 'REAL',
            },
            {
                '_id': 9,
                '_type': 'PARAMETER',
                'default': 0.0,
                'name': 'vel_pert_amp',
                'type': 'REAL',
            },
            {
                '_id': 10,
                '_type': 'PARAMETER',
                'default': 1.0,
                'name': 'vel_pert_wavelength1',
                'type': 'REAL',
            },
            {
                '_id': 11,
                '_type': 'PARAMETER',
                'default': 0.0,
                'name': 'spert_ampl1',
                'type': 'REAL',
            },
            {
                '_id': 12,
                '_type': 'PARAMETER',
                'default': 1.0,
                'name': 'spert_wl1',
                'type': 'REAL',
            },
            {
                '_id': 13,
                '_type': 'PARAMETER',
                'default': 0.0,
                'name': 'spert_phase1',
                'type': 'REAL',
            },
            {
                '_id': 14,
                '_type': 'PARAMETER',
                'default': 0.0,
                'name': 'spert_ampl2',
                'type': 'REAL',
            },
            {
                '_id': 15,
                '_type': 'PARAMETER',
                'default': 1.0,
                'name': 'spert_wl2',
                'type': 'REAL',
            },
            {
                '_id': 16,
                '_type': 'PARAMETER',
                'default': 0.0,
                'name': 'spert_phase2',
                'type': 'REAL',
            },
            {
                '_id': 17,
                '_type': 'PARAMETER',
                'default': 0.0,
                'name': 'flame_initial_position',
                'type': 'REAL',
            },
            {
                '_id': 18,
                '_type': 'PARAMETER',
                'default': '0',
                'name': 'refine_uniform_region',
                'type': 'BOOLEAN',
            },
            {
                '_id': 19,
                '_type': 'PARAMETER',
                'default': 6000000.0,
                'name': 'refine_region_size',
                'type': 'REAL',
            },
            {
                '_id': 20,
                '_type': 'PARAMETER',
                'default': 4500000.0,
                'name': 'refine_region_stepdown_size',
                'type': 'REAL',
            },
            {
                '_id': 21,
                '_type': 'PARAMETER',
                'default': 200000.0,
                'name': 'refine_lead',
                'type': 'REAL',
            },
            {
                '_id': 22,
                '_type': 'PARAMETER',
                'default': 100000.0,
                'name': 'refine_buf',
                'type': 'REAL',
            },
            {
                '_id': 23,
                '_type': 'PARAMETER',
                'default': '0',
                'name': 'sim_ParticleRefineRegion',
                'type': 'BOOLEAN',
            },
            {
                '_id': 24,
                '_type': 'PARAMETER',
                'default': 2,
                'name': 'sim_ParticleRefineRegionLevel',
                'type': 'INTEGER',
            },
            {
                '_id': 25,
                '_type': 'PARAMETER',
                'default': 6000000.0,
                'name': 'sim_ParticleRefineRegionBottom',
                'type': 'REAL',
            },
            {
                '_id': 26,
                '_type': 'PARAMETER',
                'default': 20000000.0,
                'name': 'sim_ParticleRefineRegionTop',
                'type': 'REAL',
            },
            {
                '_id': 27,
                '_type': 'PARTICLEPROP',
                'name': 'flam',
                'type': 'REAL'
            },
            {
                '_id': 28,
                '_type': 'PARTICLEPROP',
                'name': 'dens',
                'type': 'REAL'
            },
            {
                '_id': 29,
                '_type': 'PARTICLEPROP',
                'name': 'temp',
                'type': 'REAL'
            },
            {
                '_id': 30,
                '_type': 'PARTICLEMAP',
                'partName': 'temp',
                'varName': 'temp',
                'varType': 'VARIABLE'
            },
            {
                '_id': 31,
                '_type': 'PARTICLEMAP',
                'partName': 'dens',
                'varName': 'dens',
                'varType': 'VARIABLE'
            },
            {
                '_id': 32,
                '_type': 'PARTICLEMAP',
                'partName': 'flam',
                'varName': 'FLAM',
                'varType': 'MASS_SCALAR'
            },
            {
                '_id': 33,
                '_type': 'PARAMETER',
                'default': 'dens',
                'name': 'particle_attribute_1',
                'type': 'STRING',
            },
            {
                '_id': 34,
                '_type': 'PARAMETER',
                'default': 'temp',
                'name': 'particle_attribute_2',
                'type': 'STRING',
            },
            {
                '_id': 35,
                '_type': 'PARAMETER',
                'default': 'flam',
                'name': 'particle_attribute_4',
                'type': 'STRING',
            },
            {
                '_id': 36,
                '_type': 'VARIABLE',
                'name': 'turb'
            },
            {
                '_id': 37,
                '_type': 'VARIABLE',
                'name': 'fspd'
            }
        ],
        'SimulationRTFlame': {
            'dens_unburned': 100000000,
            'flame_initial_position': 2000000,
            'particle_attribute_1': 'dens',
            'particle_attribute_2': 'temp',
            'particle_attribute_4': 'flam',
            'refine_buf': 100000,
            'refine_lead': 200000,
            'refine_region_size': 6000000,
            'refine_region_stepdown_size': 4500000,
            'refine_uniform_region': '0',
            'sim_ParticleRefineRegion': '0',
            'sim_ParticleRefineRegionBottom': 6000000,
            'sim_ParticleRefineRegionLevel': 2,
            'sim_ParticleRefineRegionTop': 20000000,
            'spert_ampl1': 200000,
            'spert_ampl2': 200000,
            'spert_phase1': 0,
            'spert_phase2': 0.235243,
            'spert_wl1': 1500000,
            'spert_wl2': 125000,
            'temp_unburned': 100000000,
            'vel_pert_amp': 0,
            'vel_pert_wavelength1': 1
        }
    },
    'CapLaserBELLA': {
        'Driver': {
            'tstep_change_factor': 1.10,
            'tmax': 300.0e-09,
            'dtmin': 1.0e-16,
            'dtinit': 1.0e-15,
            'dtmax': 3.0e-09,
            'nend': 10000000,
        },
        'Grid': {
            'eosModeInit': 'dens_temp_gather',
            'xl_boundary_type': 'axisymmetric',
            'xr_boundary_type': 'user',
            'yl_boundary_type': 'outflow',
            'yr_boundary_type': 'outflow',
            'zl_boundary_type': 'reflect',
            'zr_boundary_type': 'reflect',
            'geometry': 'cylindrical',
            'xmin': 0.0,
            'xmax': 250.0e-04,
            'ymin': -500.0e-04,
            'ymax': 500.0e-04,
        },
        'gridEvolutionAnimation': {
            'notes': '',
            'y1': 'x-momentum',
            'y2': 'y-momentum',
            'y3': 'E_kinetic',
            'valueList': {
                'y1': [],
                'y2': [],
                'y3': [],

            }
        },
        'Gridparamesh': {
            'flux_correct': '0',
            'lrefine_max': 2,
            'lrefine_min': 1,
            'nblockx': 1,
            'nblocky': 4,
        },
        'Gridparameshparamesh4Paramesh4dev': {
            'gr_pmrpCurvilinear': '1',
            'gr_pmrpCurvilinearConserve': '1',
            'gr_pmrpForceConsistency': '0',
            'gr_pmrpCylindricalPm': '1',
        },
        'IO': {
            'plot_var_1': 'dens',
            'plot_var_2': 'pres',
            'plot_var_3': 'tele',
            'plot_var_4': 'tion',
            'plot_var_5': 'magz',
            'plot_var_6': 'depo',
            'plotFileIntervalTime': 1e-10,
            'io_writeMscalarIntegrals': '1',
        },
        'Multispecies': {
            'ms_fillSpecies': 'hydrogen',
            'ms_wallSpecies': 'alumina',
            'eos_fillEosType': 'eos_tab',
            'eos_fillSubType': 'ionmix4',
            'eos_wallEosType': 'eos_tab',
            'eos_wallSubType': 'ionmix4',
            'ms_fillA': 1.00794,
            'ms_fillZ': 1.0,
            'ms_fillZMin': 0.001,
            'ms_wallA': 26.9815386,
            'ms_wallZ': 13.0,
            'ms_wallZMin': 0.001,
        },
        'physicsDiffuse': {
            'diff_useEleCond': '1',
            'diff_eleFlMode': 'fl_larsen',
            'diff_eleFlCoef': 0.06,
            'diff_eleXlBoundaryType': 'neumann',
            'diff_eleXrBoundaryType': 'dirichlet',
            'diff_eleYlBoundaryType': 'neumann',
            'diff_eleYrBoundaryType': 'neumann',
            'diff_eleZlBoundaryType': 'neumann',
            'diff_eleZrBoundaryType': 'neumann',
            'useDiffuseComputeDtSpecies': '0',
            'useDiffuseComputeDtTherm': '0',
            'useDiffuseComputeDtVisc': '0',
            'dt_diff_factor': 0.3,
        },
        'physicsDiffuseUnsplit': {
            'diff_thetaImplct': 1.0,
        },
        'physicsEosTabulatedHdf5TableRead': {
            'eos_useLogTables': '0',
        },
        'physicsHydro': {
            'cfl': 0.3,
        },
        'physicsHydrounsplit': {
            'hy_fPresInMomFlux': 0.0,
            'hy_fullSpecMsFluxHandling': '0',
            'order': 3,
            'shockDetect': '1',
            'slopeLimiter': 'minmod',
            'smallt': 1.0,
            'smallx': 1.0e-99,
            'use_avisc': '1',
        },
        'physicsHydrounsplitMHD_StaggeredMesh': {
            'E_modification': '0',
            'energyFix': '1',
            'prolMethod': 'balsara_prol',
        },
        'physicsmaterialPropertiesOpacityMultispecies': {
            'op_fillAbsorb': 'op_tabpa',
            'op_fillEmiss': 'op_tabpe',
            'op_fillTrans': 'op_tabro',
            'op_fillFileType': 'ionmix4',
            'op_fillFileName': 'h-imx-004.cn4',
            'op_wallAbsorb': 'op_tabpa',
            'op_wallEmiss': 'op_tabpe',
            'op_wallTrans': 'op_tabro',
            'op_wallFileType': 'ionmix4',
            'op_wallFileName': 'al-imx-004.cn4',
        },
        'physicsRadTrans': {
            'rt_dtFactor': 1.0e+100,
        },
        'physicsRadTransMGD': {
            'rt_useMGD': '1',
            'rt_mgdNumGroups': 6,
            'rt_mgdBounds_1': 1e-1,
            'rt_mgdBounds_2': 1,
            'rt_mgdBounds_3': 10,
            'rt_mgdBounds_4': 100,
            'rt_mgdBounds_5': 1000,
            'rt_mgdBounds_6': 10000,
            'rt_mgdBounds_7': 100000,
            'rt_mgdFlMode': 'fl_harmonic',
            'rt_mgdXlBoundaryType': 'reflecting',
            'rt_mgdXrBoundaryType': 'reflecting',
            'rt_mgdYlBoundaryType': 'vacuum',
            'rt_mgdYrBoundaryType': 'vacuum',
            'rt_mgdZlBoundaryType': 'reflecting',
            'rt_mgdZrBoundaryType': 'reflecting',
        },
        'physicssourceTermsEnergyDepositionLaser': {
            'ed_maxRayCount': 10000,
            'ed_numberOfPulses': 1,
            'ed_numberOfSections_1': 4,
            'ed_time_1_1': 250.0e-09,
            'ed_time_1_2': 250.1e-09,
            'ed_time_1_3': 251.0e-09,
            'ed_time_1_4': 251.1e-09,
            'ed_power_1_1': 0.0,
            'ed_power_1_2': 1.0e+09,
            'ed_power_1_3': 1.0e+09,
            'ed_power_1_4': 0.0,
            'ed_numberOfBeams': 1,
            'ed_lensX_1': 0.0,
            'ed_lensY_1': -1000.0e-04,
            'ed_lensZ_1': 0.0,
            'ed_lensSemiAxisMajor_1': 10.0e-04,
            'ed_targetX_1': 0.0,
            'ed_targetY_1': 0.0,
            'ed_targetZ_1': 0.0,
            'ed_targetSemiAxisMajor_1': 10.0e-04,
            'ed_targetSemiAxisMinor_1': 10.0e-04,
            'ed_pulseNumber_1': 1,
            'ed_wavelength_1': 1.053,
            'ed_crossSectionFunctionType_1': 'gaussian1D',
            'ed_gaussianExponent_1': 2.0,
            'ed_gaussianRadiusMajor_1': 8.0e-04,
            'ed_gaussianRadiusMinor_1': 8.0e-04,
            'ed_numberOfRays_1': 1024,
            'ed_gridType_1': 'statistical1D',
            'ed_gridnRadialTics_1': 1024,
        },
        'physicssourceTermsEnergyDepositionLaserLaserIO': {
            'ed_useLaserIO': '1',
            'ed_laserIOMaxNumberOfPositions': 10000,
            'ed_laserIOMaxNumberOfRays':  128,
        },
        'physicssourceTermsHeatexchangeSpitzer': {
            'hx_dtFactor': 1.0e+100,
        },
        'problemFiles': {
            'archive': 'CapLaserBELLA.zip'
        },
        'setupArguments': {
            'auto': '1',
            'd': 2,
            'ed_maxBeams': 1,
            'ed_maxPulseSections': 4,
            'ed_maxPulses': 1,
            'hdf5typeio': '1',
            'laser': '1',
            'mgd': '1',
            'mgd_meshgroups': 6,
            'mtmmmt': '1',
            'nxb': 8,
            'nyb': 8,
            'species': 'fill,wall',
            'usm3t': '1'
        },
        'setupConfigDirectives': [
            {
                '_id': 1,
                '_type': 'REQUIRES',
                'unit': 'Driver'
            },
            {
                '_id': 2,
                '_type': 'REQUIRES',
                'unit': 'physics/Hydro/HydroMain/unsplit/MHD_StaggeredMesh'
            },
            {
                '_id': 3,
                '_type': 'REQUESTS',
                'unit': 'physics/Diffuse/DiffuseMain/Unsplit'
            },
            {
                '_id': 4,
                '_type': 'REQUESTS',
                'unit': 'physics/Eos/EosMain/Tabulated'
            },
            {
                '_id': 5,
                '_type': 'REQUESTS',
                'unit': 'physics/Eos/EosMain/multiTemp/Multitype'
            },
            {
                '_id': 6,
                '_type': 'REQUESTS',
                'unit': 'physics/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ'
            },
            {
                '_id': 7,
                '_type': 'REQUESTS',
                'unit': 'physics/materialProperties/MagneticResistivity/MagneticResistivityMain/SpitzerHighZ'
            },
            {
                '_id': 8,
                '_type': 'REQUESTS',
                'unit': 'physics/sourceTerms/EnergyDeposition'
            },
            {
                '_id': 9,
                '_type': 'REQUESTS',
                'unit': 'physics/sourceTerms/Heatexchange/HeatexchangeMain/LeeMore'
            },
            {
                '_id': 10,
                '_type': 'REQUESTS',
                'unit': 'physics/sourceTerms/Heatexchange/HeatexchangeMain/Spitzer'
            },
            {
                '_id': 11,
                '_type': 'PARAMETER',
                'default': 2400.0,
                'name': 'sim_peakField',
                'type': 'REAL'
            },
            {
                '_id': 12,
                '_type': 'PARAMETER',
                'default': 3e-07,
                'name': 'sim_period',
                'type': 'REAL'
            },
            {
                '_id': 13,
                '_type': 'PARAMETER',
                'default': 2.7,
                'name': 'sim_rhoWall',
                'type': 'REAL'
            },
            {
                '_id': 14,
                '_type': 'PARAMETER',
                'default': 290.11375,
                'name': 'sim_teleWall',
                'type': 'REAL'
            },
            {
                '_id': 15,
                '_type': 'PARAMETER',
                'default': 290.11375,
                'name': 'sim_tionWall',
                'type': 'REAL'
            },
            {
                '_id': 16,
                '_type': 'PARAMETER',
                'default': 290.11375,
                'name': 'sim_tradWall',
                'type': 'REAL'
            },
            {
                '_id': 17,
                '_type': 'PARAMETER',
                'default': 0.0,
                'name': 'sim_zminWall',
                'type': 'REAL'
            },
            {
                '_id': 18,
                '_type': 'PARAMETER',
                'default': 'eos_tab',
                'name': 'sim_eosWall',
                'type': 'STRING'
            },
            {
                '_id': 19,
                '_type': 'PARAMETER',
                'default': 195000.0,
                'name': 'sim_condWall',
                'type': 'REAL'
            },
            {
                '_id': 20,
                '_type': 'PARAMETER',
                'default': 2.655e-07,
                'name': 'sim_rhoFill',
                'type': 'REAL'
            },
            {
                '_id': 21,
                '_type': 'PARAMETER',
                'default': 290.11375,
                'name': 'sim_teleFill',
                'type': 'REAL'
            },
            {
                '_id': 22,
                '_type': 'PARAMETER',
                'default': 290.11375,
                'name': 'sim_tionFill',
                'type': 'REAL'
            },
            {
                '_id': 23,
                '_type': 'PARAMETER',
                'default': 290.11375,
                'name': 'sim_tradFill',
                'type': 'REAL'
            },
            {
                '_id': 24,
                '_type': 'PARAMETER',
                'default': 'eos_tab',
                'name': 'sim_eosFill',
                'type': 'STRING'
            },
            {
                '_id': 25,
                '_type': 'VARIABLE',
                'name': 'CVIO'
            },
            {
                '_id': 26,
                '_type': 'VARIABLE',
                'name': 'CVEL'
            },
            {
                '_id': 27,
                '_type': 'VARIABLE',
                'name': 'KAPA'
            },
            {
                '_id': 28,
                '_type': 'VARIABLE',
                'name': 'BDRY'
            },
            {
                '_id': 29,
                '_type': 'VARIABLE',
                'name': 'EX'
            },
            {
                '_id': 30,
                '_type': 'VARIABLE',
                'name': 'EY'
            },
            {
                '_id': 31,
                '_type': 'VARIABLE',
                'name': 'NELE'
            },
            {
                '_id': 32,
                '_type': 'VARIABLE',
                'name': 'BRSC'
            },
            {
                '_id': 33,
                '_type': 'VARIABLE',
                'name': 'BRMX'
            },
            {
                '_id': 34,
                '_type': 'VARIABLE',
                'name': 'ANGL'
            },
            {
                '_id': 35,
                '_type': 'VARIABLE',
                'name': 'RESI'
            }
        ],
        'SimulationCapLaserBELLA': {
            'sim_condWall': 150000,
            'sim_eosFill': 'eos_gam',
            'sim_eosWall': 'eos_tab',
            'sim_rhoFill': 1e-06,
            'sim_rhoWall': 2.7,
            'sim_teleFill': 11598,
            'sim_teleWall': 11598,
            'sim_tionFill': 11598,
            'sim_tionWall': 11598,
            'sim_tradFill': 11598,
            'sim_tradWall': 11598,
            'sim_zminWall': 0,
            'sim_currType': '1',
            'sim_peakCurr': 3.1e2 ,
            'sim_riseTime': 1.8e-9
        },
        'varAnimation': {
            'var': 'tele',
        },
    },
    'CapLaser3D': {
        'Driver': {
            'dtinit': 1e-15,
            'dtmax': 1e-09,
            'dtmin': 1e-16,
            'nend': 10000000,
            'tmax': 1.2e-07,
            'tstep_change_factor': 1.1,
        },
        'Grid': {
            'eosModeInit': 'dens_temp_gather',
            'geometry': 'cartesian',
            'xl_boundary_type': 'outflow',
            'xmax': 0.04,
            'xmin': -0.04,
            'xr_boundary_type': 'outflow',
            'yl_boundary_type': 'outflow',
            'ymax': 0.04,
            'ymin': -0.04,
            'yr_boundary_type': 'outflow',
            'zl_boundary_type': 'outflow',
            'zr_boundary_type': 'outflow'
        },
        'gridEvolutionAnimation': {
            'notes': '',
            'y1': 'x-momentum',
            'y2': 'y-momentum',
            'y3': 'E_kinetic',
            'valueList': {
                'y1': [],
                'y2': [],
                'y3': [],

            }
        },
        'Gridparamesh': {
            'flux_correct': '0',
            'lrefine_max': 3,
            'lrefine_min': 1,
            'nblockx': 1,
            'nblocky': 1
        },
        'Gridparameshparamesh4Paramesh4dev': {
            'gr_pmrpCurvilinear': '0',
            'gr_pmrpCurvilinearConserve': '0',
            'gr_pmrpCylindricalPm': '0',
            'gr_pmrpForceConsistency': '0'
        },
        'IO': {
            'io_writeMscalarIntegrals': '1',
            'plotFileIntervalTime': 1e-10,
            'plot_var_1': 'dens',
            'plot_var_2': 'pres',
            'plot_var_3': 'tele',
            'plot_var_4': 'tion',
            'plot_var_5': 'trad',
            'plot_var_6': 'ye'
        },
        'Multispecies': {
            'eos_fillEosType': 'eos_tab',
            'eos_fillSubType': 'ionmix4',
            'eos_wallEosType': 'eos_tab',
            'eos_wallSubType': 'ionmix4',
            'ms_fillA': 1.00784,
            'ms_fillSpecies': 'hydrogen',
            'ms_fillZ': 1,
            'ms_fillZMin': 0.001,
            'ms_wallA': 20.3922,
            'ms_wallSpecies': 'alumina',
            'ms_wallZ': 10,
            'ms_wallZMin': 0.001
        },
        'physicsDiffuse': {
            'diff_eleFlCoef': 0.06,
            'diff_eleFlMode': 'fl_larsen',
            'diff_eleXlBoundaryType': 'neumann',
            'diff_eleXrBoundaryType': 'neumann',
            'diff_eleYlBoundaryType': 'neumann',
            'diff_eleYrBoundaryType': 'neumann',
            'diff_eleZlBoundaryType': 'neumann',
            'diff_eleZrBoundaryType': 'neumann',
            'diff_useEleCond': '1',
            'dt_diff_factor': 0.3,
            'useDiffuseComputeDtSpecies': '0',
            'useDiffuseComputeDtTherm': '0',
            'useDiffuseComputeDtVisc': '0'
        },
        'physicsDiffuseUnsplit': {
            'diff_thetaImplct': 1.0,
        },
        'physicsEosTabulatedHdf5TableRead': {
            'eos_useLogTables': '0',
        },
        'physicsHydro': {
            'cfl': 0.3,
        },
        'physicsHydrounsplit': {
            'hy_fPresInMomFlux': 0.0,
            'hy_fullSpecMsFluxHandling': '0',
            'order': 3,
            'shockDetect': '1',
            'slopeLimiter': 'minmod',
            'smallt': 1.0,
            'smallx': 1.0e-99,
            'use_avisc': '1',
        },
        'physicsHydrounsplitMHD_StaggeredMesh': {
            'E_modification': '0',
            'energyFix': '1',
            'prolMethod': 'balsara_prol',
        },
        'physicsmaterialPropertiesOpacityMultispecies': {
            'op_fillAbsorb': 'op_tabpa',
            'op_fillEmiss': 'op_tabpe',
            'op_fillFileName': 'helium-fill-imx.cn4',
            'op_fillFileType': 'ionmix4',
            'op_fillTrans': 'op_tabro',
            'op_wallAbsorb': 'op_tabpa',
            'op_wallEmiss': 'op_tabpe',
            'op_wallFileName': 'alumina-wall-imx.cn4',
            'op_wallFileType': 'ionmix4',
            'op_wallTrans': 'op_tabro'
        },
        'physicsRadTrans': {
            'rt_dtFactor': 1.0e+100,
        },
        'physicsRadTransMGD': {
            'rt_mgdBounds_1': 0.1,
            'rt_mgdBounds_2': 1,
            'rt_mgdBounds_3': 10,
            'rt_mgdBounds_4': 100,
            'rt_mgdBounds_5': 1000,
            'rt_mgdBounds_6': 10000,
            'rt_mgdBounds_7': 100000,
            'rt_mgdFlMode': 'fl_harmonic',
            'rt_mgdNumGroups': 6,
            'rt_mgdXlBoundaryType': 'reflecting',
            'rt_mgdXrBoundaryType': 'reflecting',
            'rt_mgdYlBoundaryType': 'reflecting',
            'rt_mgdYrBoundaryType': 'reflecting',
            'rt_mgdZlBoundaryType': 'vacuum',
            'rt_mgdZrBoundaryType': 'vacuum',
            'rt_useMGD': '1'
        },
        'physicssourceTermsEnergyDepositionLaser': {
            'ed_crossSectionFunctionType_1': 'gaussian2D',
            'ed_gaussianExponent_1': 1,
            'ed_gaussianRadiusMajor_1': 0.008495,
            'ed_gaussianRadiusMinor_1': 0.008495,
            'ed_gridType_1': 'radial2D',
            'ed_gridnRadialTics_1': 1024,
            'ed_lensSemiAxisMajor_1': 0.02,
            'ed_lensX_1': 0,
            'ed_lensY_1': 0,
            'ed_lensZ_1': -0.745867,
            'ed_maxRayCount': 10000,
            'ed_numberOfBeams': 1,
            'ed_numberOfPulses': 1,
            'ed_numberOfRays_1': 1024,
            'ed_numberOfSections_1': 4,
            'ed_power_1_1': 0,
            'ed_power_1_2': 375000000.0,
            'ed_power_1_3': 375000000.0,
            'ed_power_1_4': 0,
            'ed_pulseNumber_1': 1,
            'ed_semiAxisMajorTorsionAngle_1': 0,
            'ed_semiAxisMajorTorsionAxis_1': 'x',
            'ed_targetSemiAxisMajor_1': 0.02,
            'ed_targetSemiAxisMinor_1': 0.02,
            'ed_targetX_1': 0,
            'ed_targetY_1': 0,
            'ed_targetZ_1': 0,
            'ed_time_1_1': 1e-07,
            'ed_time_1_2': 1.001e-07,
            'ed_time_1_3': 1.08e-07,
            'ed_time_1_4': 1.081e-07,
            'ed_wavelength_1': 0.523
        },
        'physicssourceTermsEnergyDepositionLaserLaserIO': {
            'ed_laserIOMaxNumberOfPositions': 10000,
            'ed_laserIOMaxNumberOfRays':  128,
            'ed_useLaserIO': '1',
        },
        'physicssourceTermsHeatexchangeSpitzer': {
            'hx_dtFactor': 1.0e+100,
        },
        'problemFiles': {
            'archive': 'CapLaser3D.zip'
        },
        'setupArguments': {
            'auto': '1',
            'cartesian': '1',
            'd': 3,
            'ed_maxBeams': 1,
            'ed_maxPulseSections': 4,
            'ed_maxPulses': 1,
            'hdf5typeio': '1',
            'laser': '1',
            'mgd': '1',
            'mgd_meshgroups': 6,
            'mtmmmt': '1',
            'species': 'fill,wall',
            'usm3t': '1'
        },
        'setupConfigDirectives': [
            {
                '_id': 1,
                '_type': 'REQUIRES',
                'unit': 'Driver'
            },
            {
                '_id': 2,
                '_type': 'REQUIRES',
                'unit': 'physics/Hydro/HydroMain/unsplit/MHD_StaggeredMesh'
            },
            {
                '_id': 3,
                '_type': 'REQUESTS',
                'unit': 'physics/Eos/EosMain/multiTemp/Multitype'
            },
            {
                '_id': 4,
                '_type': 'REQUESTS',
                'unit': 'physics/Eos/EosMain/Tabulated'
            },
            {
                '_id': 5,
                '_type': 'REQUESTS',
                'unit': 'physics/Diffuse/DiffuseMain/Unsplit'
            },
            {
                '_id': 6,
                '_type': 'REQUESTS',
                'unit': 'physics/sourceTerms/EnergyDeposition'
            },
            {
                '_id': 7,
                '_type': 'REQUESTS',
                'unit': 'physics/sourceTerms/Heatexchange/HeatexchangeMain/Spitzer'
            },
            {
                '_id': 8,
                '_type': 'REQUESTS',
                'unit': 'physics/materialProperties/Conductivity/ConductivityMain/SpitzerHighZ'
            },
            {
                '_id': 9,
                '_type': 'REQUESTS',
                'unit': 'physics/materialProperties/MagneticResistivity/MagneticResistivityMain/SpitzerHighZ'
            },
            {
                '_id': 10,
                '_type': 'PARAMETER',
                'default': 2400.0,
                'name': 'sim_peakField',
                'type': 'REAL',
            },
            {
                '_id': 11,
                '_type': 'PARAMETER',
                'default': 3e-07,
                'name': 'sim_period',
                'type': 'REAL',
            },
            {
                '_id': 12,
                '_type': 'PARAMETER',
                'default': 'current.dat',
                'name': 'sim_currFile',
                'type': 'STRING',
            },
            {
                '_id': 13,
                '_type': 'PARAMETER',
                'default': 450.0,
                'name': 'sim_peakCurr',
                'type': 'REAL',
            },
            {
                '_id': 14,
                '_type': 'PARAMETER',
                'default': 4e-07,
                'name': 'sim_riseTime',
                'type': 'REAL',
            },
            {
                '_id': 15,
                '_type': 'PARAMETER',
                'default': 0,
                'name': 'sim_runType',
                'type': 'INTEGER',
            },
            {
                '_id': 16,
                '_type': 'PARAMETER',
                'default': 2.7,
                'name': 'sim_rhoWall',
                'type': 'REAL',
            },
            {
                '_id': 17,
                '_type': 'PARAMETER',
                'default': 290.11375,
                'name': 'sim_teleWall',
                'type': 'REAL',
            },
            {
                '_id': 18,
                '_type': 'PARAMETER',
                'default': 290.11375,
                'name': 'sim_tionWall',
                'type': 'REAL',
            },
            {
                '_id': 19,
                '_type': 'PARAMETER',
                'default': 290.11375,
                'name': 'sim_tradWall',
                'type': 'REAL',
            },
            {
                '_id': 20,
                '_type': 'PARAMETER',
                'default': 0.0,
                'name': 'sim_zminWall',
                'type': 'REAL',
            },
            {
                '_id': 21,
                '_type': 'PARAMETER',
                'default': 'eos_tab',
                'name': 'sim_eosWall',
                'type': 'STRING',
            },
            {
                '_id': 22,
                '_type': 'PARAMETER',
                'default': 195000.0,
                'name': 'sim_condWall',
                'type': 'REAL',
            },
            {
                '_id': 23,
                '_type': 'PARAMETER',
                'default': 0.025,
                'name': 'sim_rWall',
                'type': 'REAL',
            },
            {
                '_id': 24,
                '_type': 'PARAMETER',
                'default': 2.655e-07,
                'name': 'sim_rhoFill',
                'type': 'REAL',
            },
            {
                '_id': 25,
                '_type': 'PARAMETER',
                'default': 290.11375,
                'name': 'sim_teleFill',
                'type': 'REAL',
            },
            {
                '_id': 26,
                '_type': 'PARAMETER',
                'default': 290.11375,
                'name': 'sim_tionFill',
                'type': 'REAL',
            },
            {
                '_id': 27,
                '_type': 'PARAMETER',
                'default': 290.11375,
                'name': 'sim_tradFill',
                'type': 'REAL',
            },
            {
                '_id': 28,
                '_type': 'PARAMETER',
                'default': 'eos_tab',
                'name': 'sim_eosFill',
                'type': 'STRING',
            },
            {
                '_id': 29,
                '_type': 'VARIABLE',
                'name': 'CVIO'
            },
            {
                '_id': 30,
                '_type': 'VARIABLE',
                'name': 'CVEL'
            },
            {
                '_id': 31,
                '_type': 'VARIABLE',
                'name': 'KAPA'
            },
            {
                '_id': 32,
                '_type': 'VARIABLE',
                'name': 'BDRY'
            },
            {
                '_id': 33,
                '_type': 'VARIABLE',
                'name': 'EX'
            },
            {
                '_id': 34,
                '_type': 'VARIABLE',
                'name': 'EY'
            },
            {
                '_id': 35,
                '_type': 'VARIABLE',
                'name': 'NELE'
            },
            {
                '_id': 36,
                '_type': 'VARIABLE',
                'name': 'BRSC'
            },
            {
                '_id': 37,
                '_type': 'VARIABLE',
                'name': 'BRMX'
            },
            {
                '_id': 38,
                '_type': 'VARIABLE',
                'name': 'ANGL'
            },
            {
                '_id': 39,
                '_type': 'VARIABLE',
                'name': 'RESI'
            }
        ],
        'SimulationCapLaser3D': {
            'sim_condWall': 195000,
            'sim_currFile': '',
            'sim_currType': '1',
            'sim_eosFill': 'eos_gam',
            'sim_eosWall': 'eos_tab',
            'sim_peakCurr': 310,
            'sim_peakField': 4500,
            'sim_period': 2e-07,
            'sim_rWall': 0.025,
            'sim_rhoFill': 1.467e-5,
            'sim_rhoWall': 2.7,
            'sim_riseTime': 1.8e-09,
            'sim_teleFill': 11598,
            'sim_teleWall': 11598,
            'sim_tionFill': 11598,
            'sim_tionWall': 11598,
            'sim_tradFill': 11598,
            'sim_tradWall': 11598,
            'sim_zminWall': 0
        },
        'varAnimation': {
            'var': 'tele',
        },
    },
}

def background_percent_complete(report, run_dir, is_running):
    files = _h5_file_list(run_dir)
    count = len(files)
    if is_running and count:
        count -= 1
    res = PKDict(
        percentComplete=0 if is_running else 100,
        frameCount=count,
    )
    c = _grid_evolution_columns(run_dir)
    if c:
        res.gridEvolutionColumns = [x for x in c if x[0] != '#']
    return res

def generate_config_file(run_dir, data):
    res = ''
    for e in data.models.setupConfigDirectives:
        l = f'\n{e._type} '
        if e._type == 'PARAMETER':
            l += f'{e.name} {e.type} {_format_parameter_directive_field(e.type, e.default, config=True)}'
        elif e._type == 'PARTICLEPROP':
            l += f'{e.name} {e.type}'
        elif e._type == 'PARTICLEMAP':
            l += f'TO {e.partName} FROM {e.varType} {e.varName}'
        elif e._type == 'VARIABLE':
            l += f'{e.name}'
        elif e._type in ('REQUIRES', 'REQUESTS'):
            l += f'{e.unit}'
        else:
            raise AssertionError(f'type={e._type} unknown')
        res += l
    pkio.write_text(
        _SIM_DATA.flash_simulation_unit_file_path(run_dir, data, 'Config'),
        res,
    )


def new_simulation(data, new_simulation_data):
    flash_type = new_simulation_data['flashType']
    data.models.simulation.flashType = flash_type
    for name in _DEFAULT_VALUES[flash_type]:
        f = 'update'
        if isinstance(data.models[name], list):
            f = 'extend'
        getattr(data.models[name], f)(_DEFAULT_VALUES[flash_type][name])


def remove_last_frame(run_dir):
    files = _h5_file_list(run_dir)
    if len(files) > 0:
        pkio.unchecked_remove(files[-1])


def setup_command(data):
    c = []
    for k, v in data.models.setupArguments.items():
        if k == 'units':
            for e in v:
                c.append(f'--with-unit={e}')
            continue
        if v == _SCHEMA.model.setupArguments[k][2]:
            continue
        t = _SCHEMA.model.setupArguments[k][1]
        if t == 'Boolean':
            v == '1' and c.append(f'-{k}')
        elif t == 'SetupArgumentDimension':
            c.append(f'-{v}d')
        elif t == 'Integer':
            c.append(f'-{k}={v}')
        elif t == 'NoDashInteger':
            c.append(f'{k}={v}')
        elif t == 'SetupArgumentShortcut':
            v == '1' and c.append(f'+{k}')
        elif t  == 'String':
           c.append(f'{k}={v}')
        else:
            raise AssertionError(f'type={t} not supported')
    t = data.models.simulation.flashType
    return [
        './setup',
        t,
        f'-objdir={t}',
    ] + c


def sim_frame_gridEvolutionAnimation(frame_args):
    c = _grid_evolution_columns(frame_args.run_dir)
    dat = np.loadtxt(str(frame_args.run_dir.join(_GRID_EVOLUTION_FILE)))
    stride = 20
    x = dat[::stride, 0]
    plots = []
    for v in 'y1', 'y2', 'y3':
        n = frame_args[v]
        plots.append({
            'name': n,
            'label': n,
            'points': dat[::stride, c.index(n)].tolist(),
        })
    return {
        'title': '',
        'x_range': [min(x), max(x)],
        'y_label': '',
        'x_label': 'time [s]',
        'x_points': x.tolist(),
        'plots': plots,
        'y_range': template_common.compute_plot_color_and_range(plots),
    }


def sim_frame_varAnimation(frame_args):
    field = frame_args['var']
    filename = _h5_file_list(frame_args.run_dir)[frame_args.frameIndex]
    with h5py.File(filename) as f:
        params = _parameters(f)
        node_type = f['node type']
        bounding_box = f['bounding box']
        xdomain = [params['xmin'], params['xmax']]
        ydomain = [params['ymin'], params['ymax']]
        size = _cell_size(f, params['lrefine_max'])
        dim = (
            _rounded_int((ydomain[1] - ydomain[0]) / size[1]) * params['nyb'],
            _rounded_int((xdomain[1] - xdomain[0]) / size[0]) * params['nxb'],
        )
        grid = np.zeros(dim)
        values = f[field]
        amr_grid = []
        for i in range(len(node_type)):
            if node_type[i] == 1:
                bounds = bounding_box[i]
                _apply_to_grid(grid, values[i, 0], bounds, size, xdomain, ydomain)
                amr_grid.append([
                    (bounds[0] / 100).tolist(),
                    (bounds[1] / 100).tolist(),
                ])

    # imgplot = plt.imshow(grid, extent=[xdomain[0], xdomain[1], ydomain[1], ydomain[0]], cmap='PiYG')
    aspect_ratio = float(params['nblocky']) / params['nblockx']
    time_units = 's'
    if params['time'] != 0:
        if params['time'] < 1e-6:
            params['time'] *= 1e9
            time_units = 'ns'
        elif params['time'] < 1e-3:
            params['time'] *= 1e6
            time_units = 'µs'
        elif params['time'] < 1:
            params['time'] *= 1e3
            time_units = 'ms'
    return {
        'x_range': [xdomain[0] / 100, xdomain[1] / 100, len(grid[0])],
        'y_range': [ydomain[0] / 100, ydomain[1] / 100, len(grid)],
        'x_label': 'x [m]',
        'y_label': 'y [m]',
        'title': '{}'.format(field),
        'subtitle': 'Time: {:.1f} [{}], Plot {}'.format(params['time'], time_units, frame_args.frameIndex + 1),
        'aspectRatio': aspect_ratio,
        'z_matrix': grid.tolist(),
        'amr_grid': amr_grid,
        'summaryData': {
            'aspectRatio': aspect_ratio,
        },
    }


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        #TODO: generate python instead
        run_dir.join('flash.par'),
        _generate_parameters_file(data, run_dir=run_dir),
    )


def _apply_to_grid(grid, values, bounds, cell_size, xdomain, ydomain):
    xsize = len(values)
    ysize = len(values[0])
    xi = _rounded_int((bounds[0][0] - xdomain[0]) / cell_size[0]) * xsize
    yi = _rounded_int((bounds[1][0] - ydomain[0]) / cell_size[1]) * ysize
    xscale = _rounded_int((bounds[0][1] - bounds[0][0]) / cell_size[0])
    yscale = _rounded_int((bounds[1][1] - bounds[1][0]) / cell_size[1])
    for x in range(xsize):
        for y in range(ysize):
            for x1 in range(xscale):
                for y1 in range(yscale):
                    grid[yi + (y * yscale) + y1][xi + (x * xscale) + x1] = values[y][x]


def _cell_size(f, refine_max):
    refine_level = f['refine level']
    while refine_max > 0:
        for i in range(len(refine_level)):
            if refine_level[i] == refine_max:
                return f['block size'][i]
        refine_max -= 1
    assert False, 'no blocks with appropriate refine level'


def _find_setup_config_directive(data, name):
    for d in data.models.setupConfigDirectives:
        if d.name == name:
            return d
    return PKDict()


def _format_boolean(value, config=False):
    r = 'TRUE' if value == '1' else 'FALSE'
    if not config:
        # runtime parameters (par file) have dots before and after bool
        r = f'.{r}.'
    return r


def _format_parameter_directive_field(type, value, config=False):
    v = str(value)
    if type  == 'BOOLEAN':
        v = _format_boolean(value, config=config)
    elif type == 'REAL':
        # Config file requires REALs to have decimal place or to be in
        # scientific notation
        v = '{:e}'.format(value)
    if type == 'STRING':
        v = f'"{value}"'
    return v


def _generate_parameters_file(data, run_dir=None):
    if not run_dir:
        run_dir = pkio.py_path()
    res = ''
    names = {}

    if _has_species_selection(data.models.simulation.flashType):
        for k in ('fill', 'wall'):
            f = f"{data.models.Multispecies[f'ms_{k}Species']}-{k}-imx.cn4"
            data.models.Multispecies[f'eos_{k}TableFile'] = f
            data.models[
                'physicsmaterialPropertiesOpacityMultispecies'
            ][f'op_{k}FileName'] = f

    for line in pkio.read_text(
            run_dir.join(_SIM_DATA.flash_setup_units_basename(data)),
    ).split('\n'):
        names[
            ''.join([x for x in line.split('/') if not x.endswith('Main')])
        ] = line
    for m in sorted(data.models):
        if m not in names or m == 'setupConfigDirectives':
            continue
        if m not in _SCHEMA.model:
            # old model which was removed from schema
            continue
        schema = _SCHEMA.model[m]
        heading = '# {}\n'.format(names[m])
        has_heading = False
        for f in sorted(data.models[m]):
            if f not in schema:
                continue
            v = data.models[m][f]
            if v != schema[f][2]:
                if not has_heading:
                    has_heading = True
                    res += heading
                if schema[f][1] == 'Boolean':
                    v = _format_boolean(v)
                res += '{} = "{}"\n'.format(f, v)
        if has_heading:
            res += '\n'
    return res


def _grid_evolution_columns(run_dir):
    try:
        with pkio.open_text(run_dir.join(_GRID_EVOLUTION_FILE)) as f:
            return [x for x in re.split('[ ]{2,}', f.readline().strip())]
    except FileNotFoundError:
        return []


def _has_species_selection(flash_type):
    return flash_type in ('CapLaserBELLA', 'CapLaser3D')


def _h5_file_list(run_dir):
    return sorted(glob.glob(str(run_dir.join('{}*'.format(_PLOT_FILE_PREFIX)))))


def _parameters(f):
    res = {}
    for name in ('integer scalars', 'integer runtime parameters', 'real scalars', 'real runtime parameters'):
        for v in f[name]:
            res[pkcompat.from_bytes(v[0].strip())] = v[1]
    return res


def _rounded_int(v):
    return int(round(v))
