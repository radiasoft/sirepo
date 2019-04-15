# -*- coding: utf-8 -*-
u"""FLASH execution template.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import glob
import h5py
import numpy as np
import re

SIM_TYPE = 'flash'

WANT_BROWSER_FRAME_CACHE = True

_FLASH_UNITS_PATH = {
    'RTFlame': '/home/vagrant/src/FLASH4.5/object/setup_units',
    'CapLaser': '/home/vagrant/src/FLASH4.5/CapLaser/setup_units',
}
_GRID_EVOLUTION_FILE = 'flash.dat'
_PLOT_FILE_PREFIX = 'flash_hdf5_plt_cnt_'

_SCHEMA = simulation_db.get_schema(SIM_TYPE)


def background_percent_complete(report, run_dir, is_running):
    files = _h5_file_list(run_dir)
    errors = ''
    count = len(files)
    if is_running and count:
        count -= 1
    return {
        'percentComplete': 0 if is_running else 100,
        'frameCount': count,
        'error': errors,
    }


def fixup_old_data(data):
    for m in _SCHEMA.model:
        if m not in data.models:
            data.models[m] = pkcollections.Dict({})
        template_common.update_model_defaults(data.models[m], m, _SCHEMA)
    if data.models.simulation.flashType == 'CapLaser':
        io_model = data.models.IO
        io_model.plot_var_5 = 'magz'
        io_model.plot_var_6 = 'depo'


def get_animation_name(data):
    return 'animation'


def get_simulation_frame(run_dir, data, model_data):
    if data['modelName'] == 'varAnimation':
        return _extract_meshed_plot(run_dir, data)
    if data['modelName'] == 'gridEvolutionAnimation':
        return _extract_evolution_plot(run_dir, data, model_data)
    assert False, 'invalid animation frame model: {}'.format(data['modelName'])


def lib_files(data, source_lib):
    #return template_common.filename_to_path(['flash.par', 'al-imx-004.cn4', 'h-imx-004.cn4'], source_lib)
    #return template_common.filename_to_path(['flash.par', 'helm_table.dat'], source_lib)
    if data.models.simulation.flashType == 'RTFlame':
        return template_common.filename_to_path(['helm_table.dat'], source_lib)
    if data.models.simulation.flashType == 'CapLaser':
        return template_common.filename_to_path(['al-imx-004.cn4', 'h-imx-004.cn4'], source_lib)
    assert False, 'invalid flashType: {}'.format(data.models.simulation.flashType)


def models_related_to_report(data):
    r = data['report']
    if r == get_animation_name(data):
        return []
    return [
        r,
    ]

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
        'Grid:paramesh': {
            'lrefine_max': 3,
            'nblockx': 4,
            'refine_var_1': 'dens',
            'refine_var_2': 'flam',
        },
        'IO': {
            'plot_var_1': 'dens',
            'plotFileIntervalTime': 0.01,
        },
        'Simulation:RTFlame': {
            'flame_initial_position': 2000000,
            'spert_ampl1': 200000,
            'spert_ampl2': 200000,
            'spert_phase2': 0.235243,
            'spert_wl1': 1500000,
            'spert_wl2': 125000,
        },
        'physics:Gravity:Constant': {
            'gconst': -1900000000,
        },
        'physics:sourceTerms:Flame:FlameEffects:EIP': {
            'flame_deltae': 280000000000000000,
            'sumyi_burned': 0.072917,
            'sumyi_unburned': 0.041667,
        },
        'physics:sourceTerms:Flame:FlameSpeed:Constant': {
            'fl_fsConstFlameSpeed': 2000000,
        },
        'gridEvolutionAnimation': {
            'y1': 'mass',
            'y2': 'Burned Mass',
            'y3': 'Burning rate',
        },
    },
    'CapLaser': {
        'varAnimation': {
            'var': 'tele',
        },
        'Grid': {
            'eosModeInit': 'dens_temp_gather',
            'xl_boundary_type': 'axisymmetric',
            'xr_boundary_type': 'user',
            'yl_boundary_type': 'outflow',
            'yr_boundary_type': 'outflow',
            'zl_boundary_type':'reflect',
            'zr_boundary_type': 'reflect',
            'geometry': 'cylindrical',
            'xmin': 0.0,
            'xmax': 250.0e-04,
            'ymin': -500.0e-04,
            'ymax': 500.0e-04,
        },
        'Grid:paramesh': {
            'flux_correct': '0',
            'lrefine_max': 2,
            'lrefine_min': 1,
            'nblockx': 1,
            'nblocky': 4,
        },
        'Grid:paramesh:paramesh4:Paramesh4dev': {
            'gr_pmrpCurvilinear': '1',
            'gr_pmrpCurvilinearConserve': '1',
            'gr_pmrpForceConsistency': '0',
            'gr_pmrpCylindricalPm': '1',
        },
        'Driver': {
            'tstep_change_factor': 1.10,
            'tmax': 300.0e-09,
            'dtmin': 1.0e-16,
            'dtinit': 1.0e-15,
            'dtmax': 3.0e-09,
            'nend': 10000000,
        },
        'Multispecies': {
            'ms_wallA': 26.9815386,
            'ms_wallZ': 13.0,
            'ms_wallZMin': 0.001,
            'eos_wallEosType': 'eos_tab',
            'eos_wallSubType': 'ionmix4',
            'eos_wallTableFile': 'al-imx-004.cn4',
            'ms_fillA': 1.00794,
            'ms_fillZ': 1.0,
            'ms_fillZMin': 0.001,
            'eos_fillEosType': 'eos_tab',
            'eos_fillSubType': 'ionmix4',
            'eos_fillTableFile': 'h-imx-004.cn4',
        },
        'physics:Hydro': {
            'cfl': 0.3,
        },
        'physics:Eos:Tabulated:Hdf5TableRead': {
            'eos_useLogTables': '0',
        },
        'physics:Hydro:unsplit': {
            'hy_fPresInMomFlux': 0.0,
            'hy_fullSpecMsFluxHandling': '0',
            'order': 3,
            'shockDetect': '1',
            'slopeLimiter': 'minmod',
            'smallt': 1.0,
            'smallx': 1.0e-99,
            'use_avisc': '1',
        },
        'physics:Hydro:unsplit:MHD_StaggeredMesh': {
            'E_modification': '0',
            'energyFix': '1',
            'prolMethod': 'balsara_prol',
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
        'physics:RadTrans': {
            'rt_dtFactor': 1.0e+100,
        },
        'physics:sourceTerms:Heatexchange:Spitzer': {
            'hx_dtFactor': 1.0e+100,
        },
        'physics:RadTrans:MGD': {
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
        'physics:materialProperties:Opacity:Multispecies': {
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
        'physics:sourceTerms:EnergyDeposition:Laser': {
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
        'physics:sourceTerms:EnergyDeposition:Laser:LaserIO': {
            'ed_useLaserIO': '1',
            'ed_laserIOMaxNumberOfPositions': 10000,
            'ed_laserIOMaxNumberOfRays':  128,
        },
        'physics:Diffuse': {
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
        'physics:Diffuse:Unsplit': {
            'diff_thetaImplct': 1.0,
        },
        'Simulation:magnetoHD:CapLaser': {
            'sim_peakField': 3.2e3,
            'sim_period': 400e-9,
            'sim_rhoWall': 2.7,
            'sim_teleWall': 11598,
            'sim_tionWall': 11598,
            'sim_tradWall': 11598,
            'sim_rhoFill': 1.e-6,
            'sim_teleFill': 11598,
            'sim_tionFill': 11598,
            'sim_tradFill': 11598,
            'sim_condWall': 1.5e5,
        },
    },
}


def new_simulation(data, new_simulation_data):
    flash_type = new_simulation_data['flashType']
    data.models.simulation.flashType = flash_type
    for name in _DEFAULT_VALUES[flash_type]:
        data.models[name].update(_DEFAULT_VALUES[flash_type][name])


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def remove_last_frame(run_dir):
    files = _h5_file_list(run_dir)
    if len(files) > 0:
        pkio.unchecked_remove(files[-1])


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        #TODO: generate python instead
        run_dir.join('flash.par'),
        _generate_parameters_file(data),
    )


def _apply_to_grid(grid, values, bounds, cell_size, xdomain, ydomain):
    xsize = len(values)
    ysize = len(values[0])
    xi = _rounded_int((bounds[0][0] - xdomain[0]) / cell_size[0]) * xsize
    yi = _rounded_int((bounds[1][0] - ydomain[0]) / cell_size[1]) * ysize
    xscale = _rounded_int((bounds[0][1] - bounds[0][0]) / cell_size[0])
    yscale = _rounded_int((bounds[1][1] - bounds[1][0]) / cell_size[1])
    for x in xrange(xsize):
        for y in xrange(ysize):
            for x1 in xrange(xscale):
                for y1 in xrange(yscale):
                    grid[yi + (y * yscale) + y1][xi + (x * xscale) + x1] = values[y][x]


def _cell_size(f, refine_max):
    refine_level = f['refine level']
    while refine_max > 0:
        for i in xrange(len(refine_level)):
            if refine_level[i] == refine_max:
                return f['block size'][i]
        refine_max -= 1
    assert False, 'no blocks with appropriate refine level'


#TODO(pjm): plot columns are hard-coded for flashType
_PLOT_COLUMNS = {
    'RTFlame': [
        ['mass', 1],
        ['burned mass', 9],
        ['burning rate', 12],
    ],
    'CapLaser': [
        ['x-momentum', 2],
        ['y-momentum', 3],
        ['E kinetic', 6],
    ],
}

def _extract_evolution_plot(run_dir, data, model_data):
    frame_index = int(data['frameIndex'])
    args = template_common.parse_animation_args(
        data,
        {
            '': ['y1', 'y2', 'y3', 'startTime'],
        },
    )
    datfile = np.loadtxt(str(run_dir.join(_GRID_EVOLUTION_FILE)))
    stride = 20
    x = datfile[::stride, 0]
    plots = []
    for plot in _PLOT_COLUMNS[model_data.models.simulation.get('flashType', 'RTFlame')]:
        plots.append({
            'name': plot[0],
            'label': plot[0],
            'points': datfile[::stride, plot[1]].tolist(),
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


def _extract_meshed_plot(run_dir, data):
    frame_index = int(data['frameIndex'])
    report = template_common.parse_animation_args(
        data,
        {'': ['var', 'startTime']},
    )
    field = report['var']
    filename = _h5_file_list(run_dir)[frame_index]
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
        for i in xrange(len(node_type)):
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
        'subtitle': 'Time: {:.1f} [{}], Plot {}'.format(params['time'], time_units, frame_index + 1),
        'aspectRatio': aspect_ratio,
        'z_matrix': grid.tolist(),
        'amr_grid': amr_grid,
        'summaryData': {
            'aspectRatio': aspect_ratio,
        },
    }


def _generate_parameters_file(data):
    res = ''
    names = {}
    for line in pkio.read_text(_FLASH_UNITS_PATH[data.models.simulation.flashType]).split('\n'):
        name = ''
        #TODO(pjm): share with setup_params parser
        for part in line.split('/'):
            if not re.search('Main$', part):
                name += (':' if len(name) else '') + part
        names[name] = line
    for m in sorted(data.models):
        if m in names:
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
                        v = '.TRUE.' if v == '1' else '.FALSE.'
                    res += '{} = "{}"\n'.format(f, v)
            if has_heading:
                res += '\n'
    return res


def _h5_file_list(run_dir):
    return sorted(glob.glob(str(run_dir.join('{}*'.format(_PLOT_FILE_PREFIX)))))


def _parameters(f):
    res = {}
    for name in ('integer scalars', 'integer runtime parameters', 'real scalars', 'real runtime parameters'):
        for v in f[name]:
            res[v[0].strip()] = v[1]
    return res


def _rounded_int(v):
    return int(round(v))
