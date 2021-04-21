# -*- coding: utf-8 -*-
u"""FLASH execution template.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import h5py
import numpy as np
import re
import sirepo.sim_data

yt = None

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

_FLASH_PAR_FILE = 'flash.par'

_GRID_EVOLUTION_FILE = 'flash.dat'

_LINEOUTS_SAMPLING_SIZE = 256

_PLOT_FILE_PREFIX = 'flash_hdf5_plt_cnt_'

# TODO(e-carlin): When katex for labels is implemented
# https://git.radiasoft.org/sirepo/issues/3384
# dens='$\frac{\mathrm{g}}{\mathrm{cm}^3}$'
# magz='B$_{\phi}$ [T]'
_PLOT_VARIABLE_LABELS = PKDict(
    dens='g/cm^3',
    depo='cm/s',
    fill='',
    flam='cms/s',
    kapa='',
    length='cm',
    magz='Bphi T',
    sumy='',
    tele='K',
    time='s',
    tion='K',
    trad='K',
    velx='cm/s',
    wall='',
    ye='',
)


def background_percent_complete(report, run_dir, is_running):
    def _grid_columns():
        c = _grid_evolution_columns(run_dir)
        return [x for x in c if x[0] != '#'] if c \
            else None

    def _plot_filenames():
        return [
            PKDict(
                time=_time_and_units(yt.load(str(f)).parameters['time']),
                filename=f.basename,
            )
            for f in files
        ]

    def _plot_vars():
        names = []
        if len(files):
            io = simulation_db.read_json(
                run_dir.join(template_common.INPUT_BASE_NAME),
            ).models.IO
            idx = 1
            while io.get(f'plot_var_{idx}', ''):
                n = io[f'plot_var_{idx}']
                if n != 'none':
                    names.append(n)
                idx += 1
        return names

    res = PKDict(
        percentComplete=0 if is_running else 100,
    )
    if report == 'setupAnimation':
        f = run_dir.join(_SIM_DATA.SETUP_PARAMS_SCHEMA_FILE)
        if f.exists():
            res.pkupdate(
                frameCount=1,
                flashSchema=pkjson.load_any(pkio.read_text(f))
            )
    else:
        _init_yt()
        files = _h5_file_list(run_dir)
        if is_running and len(files):
            # the last file may be unfinished if the simulation is running
            files.pop()
        res.pkupdate(
            frameCount=len(files),
            plotVars=_plot_vars(),
            plotFiles=_plot_filenames(),
            gridEvolutionColumns=_grid_columns(),
        )
    return res


def generate_config_file(run_dir, data):

    field_order = _SCHEMA.constants.flashDirectives.fieldOrder
    labels = _SCHEMA.constants.flashDirectives.labels

    def _config_element_text(e, indent=0):
        l = ''
        if 'comment' in e:
            l += f'\n{"   " * indent}D {e.name} {e.comment}'
        l += f'\n{"   " * indent}{e._type}'
        for f in field_order[e._type]:
            v = e[f]
            if f == 'isConstant':
                if v == '1':
                    l += ' CONSTANT'
                continue
            if f == 'default' and e.type == 'STRING':
                v = f'"{v}"'
            if not len(v):
                continue
            if f == 'range':
                v = f'[{v}]'
            if f in labels:
                v = f'{labels[f]} {v}'
            l += f' {v}'
        if 'statements' in e:
            for stmt in e.statements:
                l += _config_element_text(stmt, indent + 1)
        return l

    res = ''
    for e in data.models.setupConfigDirectives:
        res += _config_element_text(e)
    pkio.write_text(
        _SIM_DATA.flash_simulation_unit_file_path(run_dir, data, 'Config'),
        res + '\n',
    )


def get_application_data(data, **kwargs):
    if data.method == 'setup_command':
        return PKDict(setupCommand=' '.join(setup_command(data)))
    raise AssertionError(f'unknown method={data.method}')


def post_execution_processing(success_exit=True, is_parallel=False, run_dir=None, **kwargs):
    # TODO(e-carlin): share with synergia (and possibly radia)
    if success_exit:
        return None
    e = None
    f = run_dir.join('mpi_run.out')
    if f.exists():
        m = re.search(
            r'^ Error message is (.*?)\n',
            pkio.read_text(f),
            re.MULTILINE | re.DOTALL,
        )
        if m:
            e = m.group(1)
    return e

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
        elif t  == 'String' or t == 'OptionalString':
           c.append(f'{k}={v}')
        else:
            raise AssertionError(f'type={t} not supported')
    t = _SCHEMA.constants.flashAppName
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
        if n == 'None':
            continue
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


def sim_frame_oneDimensionProfileAnimation(frame_args):
    import rsflash.plotting.extracts

    # def _interpolate_max(files):
    #     m = -1
    #     for f in files:
    #         d = yt.load(f)
    #         m = max(d.domain_width[0] + d.index.grid_left_edge[0][0], m)
    #     return m


    def _files():
        if frame_args.selectedPlotFiles:
            return sorted([str(frame_args.run_dir.join(f)) for f in frame_args.selectedPlotFiles.split(',')])
        return [str(_h5_file_list(frame_args.run_dir)[-1])]

    #_init_yt()
    plots = []
    x_points = []
    f = _files()
    xs, ys, times = rsflash.plotting.extracts.get_lineouts(
        f,
        frame_args.var,
        frame_args.axis,
        _LINEOUTS_SAMPLING_SIZE,
        # interpolate_max=_interpolate_max(f),
    )
    x = xs[0]
    for i, _ in enumerate(ys):
        assert x.all() == xs[i].all(), 'Plots must use the same x values'
        y = ys[i]
        plots.append(PKDict(
            name=i,
            label=_time_and_units(times[i]),
            points=y.tolist(),
        ))
    return PKDict(
        plots=plots,
        title=frame_args.var,
        x_label=_PLOT_VARIABLE_LABELS.length,
        x_points = x.tolist(),
        x_range=[np.min(x), np.max(x)],
        y_label=_PLOT_VARIABLE_LABELS.get(frame_args.var, ''),
        y_range=template_common.compute_plot_color_and_range(plots),
    )


def sim_frame_varAnimation(frame_args):
    field = frame_args['var']
    with h5py.File(str(_h5_file_list(frame_args.run_dir)[frame_args.frameIndex])) as f:
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
    return {
        'x_range': [xdomain[0] / 100, xdomain[1] / 100, len(grid[0])],
        'y_range': [ydomain[0] / 100, ydomain[1] / 100, len(grid)],
        'x_label': 'x [m]',
        'y_label': 'y [m]',
        'title': '{}'.format(field),
        'subtitle': 'Time: {}, Plot {}'.format(_time_and_units(params['time']), frame_args.frameIndex + 1),
        'aspectRatio': aspect_ratio,
        'z_matrix': grid.tolist(),
        'amr_grid': amr_grid,
        'summaryData': {
            'aspectRatio': aspect_ratio,
        },
    }


def write_parameters(data, run_dir, is_parallel):
    if data.report == 'setupAnimation':
        return
    pkio.write_text(
        run_dir.join(_FLASH_PAR_FILE),
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


def _generate_parameters_file(data, run_dir=None):
    res = ''
    # names = {}

    # if _has_species_selection(data.models.simulation.flashType):
    #     for k in ('fill', 'wall'):
    #         f = f"{data.models.Multispecies[f'ms_{k}Species']}-{k}-imx.cn4"
    #         data.models.Multispecies[f'eos_{k}TableFile'] = f
    #         data.models[
    #             'physicsmaterialPropertiesOpacityMultispecies'
    #         ][f'op_{k}FileName'] = f

    # for line in pkio.read_text(
    #     run_dir.join(_SIM_DATA.flash_setup_units_basename(data)),
    # ).split('\n'):
    #     names[
    #         #''.join([x for x in line.split('/') if not x.endswith('Main')])
    #         #re.sub(r'/', '_', line)
    #         flash_parser.SetupParameterParser.model_name_from_flash_unit_name(line)
    #     ] = line

    flash_schema = data.models.flashSchema

    for m in sorted(data.models):
        if m not in flash_schema.model:
            continue
        schema = flash_schema.model[m]
        heading = '# {}\n'.format(flash_schema.view[m].title)
        has_heading = False
        for f in sorted(data.models[m]):
            if f not in schema:
                continue
            if f in ('basenm', 'checkpointFileIntervalTime', 'checkpointFileIntervalStep'):
                # Simulation.basenm must remain the default
                # plotting routines depend on the constant name
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


def _init_yt():
    global yt
    if yt:
        return
    import yt
    # 50 disables logging
    # https://yt-project.org/doc/reference/configuration.html#configuration-options-at-runtime
    yt.funcs.mylog.setLevel(50)


def _h5_file_list(run_dir):
    return pkio.sorted_glob(run_dir.join('{}*'.format(_PLOT_FILE_PREFIX)))


def _parameters(f):
    res = {}
    for name in ('integer scalars', 'integer runtime parameters', 'real scalars', 'real runtime parameters'):
        for v in f[name]:
            res[pkcompat.from_bytes(v[0].strip())] = v[1]
    return res


def _rounded_int(v):
    return int(round(v))


def _time_and_units(time):
    u = 's'
    if time < 1e-12:
        time *= 1e15
        u  = 'fs'
    elif time < 1e-9:
        time *= 1e12
        u  = 'ps'
    elif time < 1e-6:
        time *= 1e9
        u  = 'ns'
    elif time < 1e-3:
        time *= 1e6
        u  = 'µs'
    elif time < 1:
        time *= 1e3
        u = 'ms'
    return f'{time:.2f} {u}'
