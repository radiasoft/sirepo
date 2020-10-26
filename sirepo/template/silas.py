# -*- coding: utf-8 -*-
u"""SILAS execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import csv
import h5py
import numpy as np
import re
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

_SUMMARY_CSV_FILE = 'wavefront.csv'


def background_percent_complete(report, run_dir, is_running):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    line = template_common.read_last_csv_line(run_dir.join(_SUMMARY_CSV_FILE))
    m = re.search(r'^(\d+)', line)
    if m and int(m.group(1)) > 0:
        res.frameCount = int(m.group(1))
        res.wavefrontsFrameCount = _counts_for_beamline(res.frameCount, data.models.beamline)[0]
        #TODO(pjm): share calculation
        total_count = data.models.simulationSettings.n_reflections * 2 ** (len(data.models.beamline) - 1)
        res.percentComplete = res.frameCount * 100 / total_count
    return res


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def sim_frame(frame_args):
    idx = 0
    beamline = frame_args.sim_in.models.beamline
    for item in beamline:
        if str(frame_args.id) == str(item.id):
            break
        idx += 1
    total_count = frame_args.sim_in.models.simulationSettings.n_reflections * 2 ** (len(beamline) - 1)
    counts = _counts_for_beamline(total_count, beamline)[1]
    counts = counts[idx]
    file_index = counts[frame_args.frameIndex]
    with h5py.File(f'wfr{file_index:05d}.h5', 'r') as f:
        wfr = f['wfr']
        points = np.array(wfr)
        return PKDict(
            title='S={}m (E={} eV]'.format(wfr.attrs['pos'], frame_args.sim_in.models.gaussianBeam.photonEnergy),
            subtitle='',
            x_range=[wfr.attrs['xStart'], wfr.attrs['xFin'], len(points[0])],
            x_label='Horizontal Position [m]',
            y_range=[wfr.attrs['yStart'], wfr.attrs['yFin'], len(points)],
            y_label='Vertical Position [m]',
            z_matrix=points.tolist(),
        )


def sim_frame_wavefrontSummaryAnimation(frame_args):
    cols = ['count', 'pos', 'sx', 'sy', 'xavg', 'yavg']
    v = np.genfromtxt(str(frame_args.run_dir.join(_SUMMARY_CSV_FILE)), delimiter=',', skip_header=1)
    #TODO(pjm): generalize, use template_common parameter_plot()?
    plots = []
    for col in ('sx', 'sy'):
        plots.append(PKDict(
            points=v[:, cols.index(col)].tolist(),
            label=f'{col} [m]',
        ))
    x = v[:, cols.index('pos')].tolist()
    return PKDict(
        aspectRatio=1 / 5.0,
        title='Wavefront Dimensions',
        x_range=[float(min(x)), float(max(x))],
        y_label='',
        x_label='s [m]',
        x_points=x,
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
    )


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _counts_for_beamline(total_frames, beamline):
    # first element is 2nd in list, loop back and forth across beamline
    counts = [0 for _ in beamline]
    idx = 1
    direction = 1
    frames = [[] for _ in beamline]

    for i in range(total_frames):
        counts[idx] += 1
        frames[idx].append(i + 1)
        idx += direction
        if idx < 0 or idx > len(counts) - 1:
            direction *= -1
            idx += 2 * direction
    return counts, frames


def _generate_parameters_file(data):
    report = data.get('report', '')
    res, v = template_common.generate_parameters_file(data)
    beamline = data.models.beamline
    v.leftMirrorFocusingError = beamline[0].focusingError
    v.rightMirrorFocusingError = beamline[-1].focusingError
    return res + template_common.render_jinja(SIM_TYPE, v)
