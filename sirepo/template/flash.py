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

#TODO(pjm): change to True
WANT_BROWSER_FRAME_CACHE = False

_FLASH_UNITS_PATH = '/home/vagrant/src/FLASH4.5/object/setup_units'
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


def get_animation_name(data):
    return 'animation'


def get_simulation_frame(run_dir, data, model_data):
    if data['modelName'] == 'varAnimation':
        return _extract_meshed_plot(run_dir, data)
    if data['modelName'] == 'gridEvolutionAnimation':
        return _extract_evolution_plot(run_dir, data)
    assert False, 'invalid animation frame model: {}'.format(data['modelName'])


def lib_files(data, source_lib):
    #return template_common.filename_to_path(['flash.par', 'al-imx-004.cn4', 'h-imx-004.cn4'], source_lib)
    #return template_common.filename_to_path(['flash.par', 'helm_table.dat'], source_lib)
    return template_common.filename_to_path(['helm_table.dat'], source_lib)


def models_related_to_report(data):
    r = data['report']
    if r == get_animation_name(data):
        return []
    return [
        r,
    ]


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


def _extract_evolution_plot(run_dir, data):
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
    plots = [
        {
            'name': 'mass',
            'label': 'mass',
            'points': datfile[::stride, 1].tolist(),
        },
        {
            'name': 'Burned Mass',
            'label': 'burned mass',
            'points': datfile[::stride, 9].tolist(),
        },
        {
            'name': 'Burning rate',
            'label': 'burning rate',
            'points': datfile[::stride, 12].tolist(),
        },
    ]
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
        #'title': '{} for Time: {:.4e}s, Step {}'.format(title, data_time, data_file.iteration),
        'title': '{}'.format(field),
        'subtitle': 'Time: {:.1f} [{}], Plot {}'.format(params['time'], time_units, frame_index + 1),
        #'aspect_ratio': 0.25,
        'aspect_ratio': aspect_ratio,
        'z_matrix': grid.tolist(),
        'amr_grid': amr_grid,
        'summaryData': {
            'aspect_ratio': aspect_ratio,
        },
    }


def _generate_parameters_file(data):
    res = ''
    names = {}
    for line in pkio.read_text(_FLASH_UNITS_PATH).split('\n'):
        name = ''
        #TODO(pjm): share with setup_params parser
        for part in line.split('/'):
            if not re.search('Main$', part):
                name += (':' if len(name) else '') + part
        names[name] = line
    for m in sorted(data.models):
        if m in names:
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
