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
from scipy import constants
from sirepo import simulation_db
from sirepo.template import template_common
import csv
import h5py
import math
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
        res.frameCount = int((int(m.group(1)) + 1) / 2)
        res.wavefrontsFrameCount = _counts_for_beamline(res.frameCount, data.models.beamline)[0]
        total_count = _total_frame_count(data)
        res.percentComplete = res.frameCount * 100 / total_count
    return res


def get_application_data(data, **kwargs):
    if data['method'] == 'compute_rms_size':
        return _compute_rms_size(data)


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def sim_frame(frame_args):
    idx = 0
    beamline = frame_args.sim_in.models.beamline
    for item in beamline:
        if str(frame_args.id) == str(item.id):
            break
        idx += 1
    total_count = _total_frame_count(frame_args.sim_in)
    counts = _counts_for_beamline(total_count, beamline)[1]
    counts = counts[idx]
    file_index = counts[frame_args.frameIndex]
    with h5py.File(f'wfr{file_index:05d}.h5', 'r') as f:
        wfr = f['wfr']
        points = np.array(wfr)
        return PKDict(
            title='S={}m (E={} eV)'.format(
                _format_float(wfr.attrs['pos']),
                frame_args.sim_in.models.gaussianBeam.photonEnergy,
            ),
            subtitle='',
            x_range=[wfr.attrs['xStart'], wfr.attrs['xFin'], len(points[0])],
            x_label='Horizontal Position [m]',
            y_range=[wfr.attrs['yStart'], wfr.attrs['yFin'], len(points)],
            y_label='Vertical Position [m]',
            z_matrix=points.tolist(),
        )


def sim_frame_wavefrontSummaryAnimation(frame_args):
    beamline = frame_args.sim_in.models.beamline
    if 'element' not in frame_args:
        frame_args.element = 'all'
    idx = 0
    title = ''
    if frame_args.element != 'all':
        # find the element index from the element id
        for item in beamline:
            if item.id == int(frame_args.element):
                title = item.title
                break
            idx += 1
    #TODO(pjm): use column headings from csv
    cols = ['count', 'pos', 'sx', 'sy', 'xavg', 'yavg']
    v = np.genfromtxt(str(frame_args.run_dir.join(_SUMMARY_CSV_FILE)), delimiter=',', skip_header=1)
    if frame_args.element != 'all':
        # the wavefront csv include intermediate values, so take every other row
        counts = _counts_for_beamline(int((v[-1][0] + 1) / 2), beamline)[1]
        v2 = []
        for row in counts[idx]:
            v2.append(v[(row - 1) * 2])
        v = np.array(v2)
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
        title='{} Wavefront Dimensions'.format(title),
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


def _compute_rms_size(data):
    wavefrontEnergy = data.gaussianBeam.photonEnergy
    n0 = data.crystal.refractionIndex
    L_cryst = data.crystal.width
    dfL = data.mirror.focusingError
    L_cav = data.simulationSettings.cavity_length
    L_eff = L_cav + (1 / n0 - 1) * L_cryst
    beta0 = math.sqrt(L_eff * (L_cav / 4 + dfL) - L_eff ** 2 / 4)
    lam = constants.c * constants.value('Planck constant in eV/Hz') / wavefrontEnergy
    return PKDict(
        rmsSize=math.sqrt(lam*beta0/4/math.pi)
    )


def _counts_for_beamline(total_frames, beamline):
    # start at 2nd element, loop forward and backward across beamline
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


def _format_float(v):
    return float('{:.4f}'.format(v))


def _generate_parameters_file(data):
    beamline = data.models.beamline
    data.models.crystal = beamline[1]
    res, v = template_common.generate_parameters_file(data)
    v.leftMirrorFocusingError = beamline[0].focusingError
    v.rightMirrorFocusingError = beamline[-1].focusingError
    return res + template_common.render_jinja(SIM_TYPE, v)


def _total_frame_count(data):
    return data.models.simulationSettings.n_reflections * 2 * (len(data.models.beamline) - 1) + 1
