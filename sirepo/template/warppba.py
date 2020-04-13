# -*- coding: utf-8 -*-
u"""WARP execution template.

:copyright: Copyright (c) 2015-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from openpmd_viewer import OpenPMDTimeSeries
from openpmd_viewer.openpmd_timeseries import main
from openpmd_viewer.openpmd_timeseries.data_reader import field_reader
from pykern import pkcollections
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import h5py
import numpy
import os
import os.path
import py.path
import re
import sirepo.sim_data


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

WANT_BROWSER_FRAME_CACHE = True


def background_percent_complete(report, run_dir, is_running):
    files = _h5_file_list(run_dir)
    if len(files) < 2:
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    file_index = len(files) - 1
    last_update_time = int(os.path.getmtime(str(files[file_index])))
    # look at 2nd to last file if running, last one may be incomplete
    if is_running:
        file_index -= 1
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    Fr, info = _read_field_circ(files[file_index])
    plasma_length = float(data.models.electronPlasma.length) / 1e3
    zmin = float(data.models.simulationGrid.zMin) / 1e6
    percent_complete = (info.imshow_extent[1] / (plasma_length - zmin))
    if percent_complete < 0:
        percent_complete = 0
    elif percent_complete > 1.0:
        percent_complete = 1.0
    return PKDict(
        lastUpdateTime=last_update_time,
        percentComplete=percent_complete * 100,
        frameCount=file_index + 1,
    )


def extract_field_report(field, coordinate, mode, data_file):
    opmd = _opmd_time_series(data_file)
    F, info = opmd.get_field(
        plot=False,
        vmin=None,
        m=mode,
        coord=coordinate,
        iteration=numpy.array([data_file.iteration]),
        slicing=0.0,
        field=field,
        theta=0.0,
        vmax=None,
        output=True,
        slicing_dir='y',

    )
    extent = info.imshow_extent
    if field == 'rho':
        field_label = field
    else:
        field_label = '{} {}'.format(field, coordinate)
    return PKDict(
        x_range=[extent[0], extent[1], len(F[0])],
        y_range=[extent[2], extent[3], len(F)],
        x_label='{} [m]'.format(info.axes[1]),
        y_label='{} [m]'.format(info.axes[0]),
        title="{} in the mode {} at {}".format(
            field_label, mode, _iteration_title(opmd, data_file)),
        z_matrix=numpy.flipud(F).tolist(),
    )


def extract_particle_report(frame_args, particle_type):
    data_file = open_data_file(frame_args.run_dir, frame_args.frameIndex)
    xarg = frame_args.x
    yarg = frame_args.y
    nbins = frame_args.histogramBins
    opmd = _opmd_time_series(data_file)
    data_list = opmd.get_particle(
        var_list=[xarg, yarg],
        species=particle_type,
        iteration=numpy.array([data_file.iteration]),
        select=None,
        output=True,
        plot=False,
    )
    with h5py.File(data_file.filename) as f:
        data_list.append(main.read_species_data(f, particle_type, 'w', ()))
    select = _particle_selection_args(frame_args)
    if select:
        with h5py.File(data_file.filename) as f:
            main.apply_selection(f, data_list, select, particle_type, ())
    xunits = ' [m]' if len(xarg) == 1 else ''
    yunits = ' [m]' if len(yarg) == 1 else ''

    if xarg == 'z':
        data_list = _adjust_z_width(data_list, data_file)

    hist, edges = numpy.histogramdd(
        [data_list[0], data_list[1]],
        template_common.histogram_bins(nbins),
        weights=data_list[2],
        range=[_select_range(data_list[0], xarg, select), _select_range(data_list[1], yarg, select)],
    )
    return PKDict(
        x_range=[float(edges[0][0]), float(edges[0][-1]), len(hist)],
        y_range=[float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        x_label='{}{}'.format(xarg, xunits),
        y_label='{}{}'.format(yarg, yunits),
        title='t = {}'.format(_iteration_title(opmd, data_file)),
        z_matrix=hist.T.tolist(),
        frameCount=data_file.num_frames,
    )


def generate_parameters_file(data, is_parallel=False):
    template_common.validate_models(data, _SCHEMA)
    res, v = template_common.generate_parameters_file(data)
    v['isAnimationView'] = is_parallel
    v['incSteps'] = 50
    v['diagnosticPeriod'] = 50
    if data['models']['simulation']['sourceType'] == 'electronBeam':
        v['useBeam'] = 1
        v['useLaser'] = 0
    else:
        v['useBeam'] = 0
        v['useLaser'] = 1
    if data['models']['electronBeam']['beamRadiusMethod'] == 'a':
        v['electronBeam_transverseEmittance'] = 0
    return res + template_common.render_jinja(SIM_TYPE, v)


def get_data_file(run_dir, model, frame, **kwargs):
    files = _h5_file_list(run_dir)
    #TODO(pjm): last client file may have been deleted on a canceled animation,
    # give the last available file instead.
    if len(files) < frame + 1:
        frame = -1
    filename = str(files[int(frame)])
    with open(filename, 'rb') as f:
        return os.path.basename(filename), f.read(), 'application/octet-stream'


def new_simulation(data, new_simulation_data):
    source = new_simulation_data['sourceType']
    if not source:
        source = 'laserPulse'
    data['models']['simulation']['sourceType'] = source
    if source == 'electronBeam':
        grid = data['models']['simulationGrid']
        grid['gridDimensions'] = 'e'
        grid['rCellResolution'] = 20
        grid['rCellsPerSpotSize'] = 8
        grid['rCount'] = 100
        grid['rLength'] = 264.0501846240597
        grid['rMax'] = 264.0501846240597
        grid['rMin'] = 0
        grid['rParticlesPerCell'] = 2
        grid['rScale'] = 5
        grid['zCellResolution'] = 30
        grid['zCellsPerWavelength'] = 8
        grid['zCount'] = 90
        grid['zLength'] = 316.86022154887166
        grid['zMax'] = 0
        grid['zMin'] = -316.86022154887166
        grid['zParticlesPerCell'] = 2
        grid['zScale'] = 3
        data['models']['electronPlasma']['density'] = 1e23
        data['models']['electronPlasma']['length'] = 1
        data['models']['fieldAnimation']['coordinate'] = 'z'
        data['models']['fieldAnimation']['mode'] = '0'
        data['models']['particleAnimation']['histogramBins'] = 90
        data['models']['particleAnimation']['yMin'] = -50
        data['models']['particleAnimation']['yMax'] = 50
        data['models']['beamAnimation']['histogramBins'] = 91
        data['models']['beamPreviewReport']['histogramBins'] = 91


def open_data_file(run_dir, file_index=None):
    """Opens data file_index'th in run_dir

    Args:
        run_dir (py.path): has subdir ``hdf5``
        file_index (int): which file to open (default: last one)
        files (list): list of files (default: load list)

    Returns:
        PKDict: various parameters
    """
    files = _h5_file_list(run_dir)
    res = PKDict()
    res.num_frames = len(files)
    res.frame_index = res.num_frames - 1 if file_index is None else file_index
    res.filename = str(files[res.frame_index])
    res.iteration = int(re.search(r'data(\d+)', res.filename).group(1))
    return res


def python_source_for_model(data, model):
    return generate_parameters_file(data, is_parallel=True)


def remove_last_frame(run_dir):
    files = _h5_file_list(run_dir)
    if len(files) > 0:
        pkio.unchecked_remove(files[-1])


def sim_frame_beamAnimation(frame_args):
    return extract_particle_report(frame_args, 'beam')


def sim_frame_fieldAnimation(frame_args):
    f = open_data_file(frame_args.run_dir, frame_args.frameIndex)
    m = frame_args.mode
    if m != 'all':
        m = int(m)
    return extract_field_report(
        frame_args.field,
        frame_args.coordinate,
        m,
        f,
    ).pkupdate(frameCount=f.num_frames)


def sim_frame_particleAnimation(frame_args):
    return extract_particle_report(frame_args, 'electrons')


def write_parameters(data, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        generate_parameters_file(
            data,
            is_parallel,
        ),
    )


def _adjust_z_width(data_list, data_file):
    # match boundaries with field report
    Fr, info = _read_field_circ(data_file.filename)
    extent = info.imshow_extent
    return [
        numpy.append(data_list[0], [extent[0], extent[1]]),
        numpy.append(data_list[1], [extent[2], extent[3]]),
        numpy.append(data_list[2], [0, 0]),
    ]


def _h5_file_list(run_dir):
    return pkio.walk_tree(
        run_dir.join('hdf5'),
        r'\.h5$',
    )


def _iteration_title(opmd, data_file):
    fs = opmd.t[0] * 1e15
    return '{:.1f} fs (iteration {})'.format(fs, data_file.iteration)


def _opmd_time_series(data_file):
    prev = None
    try:
        prev = main.list_h5_files
        main.list_h5_files = lambda x: ([data_file.filename], [data_file.iteration])
        return OpenPMDTimeSeries(py.path.local(data_file.filename).dirname)
    finally:
        if prev:
            main.list_h5_files = prev


def _particle_selection_args(args):
    if not 'uxMin' in args:
        return None
    res = PKDict()
    for f in '', 'u':
        for f2 in 'x', 'y', 'z':
            field = '{}{}'.format(f, f2)
            min = float(args[field + 'Min']) / 1e6
            max = float(args[field + 'Max']) / 1e6
            if min == 0 and max == 0:
                continue
            res[field] = [min, max]
    return res if len(res.keys()) else None


def _read_field_circ(filename):
    return field_reader.read_field_circ(
        str(filename),
        'E/r',
        slice_across=None,
        slice_relative_position=None,
    )


def _select_range(values, arg, select):
    if select and arg in select:
        if arg in ('x', 'y', 'z'):
            return [select[arg][0] / 1e6, select[arg][1] / 1e6]
        return select[arg]
    return [min(values), max(values)]
