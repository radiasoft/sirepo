# -*- coding: utf-8 -*-
"""Wrapper to run SRW from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from subprocess import call
import json
import numpy as np
import os
import sdds

_ELEGANT_ME_EV = 0.51099906e6

#TODO(pjm): lookup in PhaseSpaceCoordinate
_FIELD_LABEL = {
    'x': 'x [m]',
    'xp': "x' [rad]",
    'y': 'y [m]',
    'yp': "y' [rad]",
    't': 't [s]',
    'p': '(p - p₀)/p₀ [eV]',
}

_PLOT_TITLE = {
    'x-xp': 'Horizontal',
    'y-yp': 'Vertical',
    'x-y': 'Cross-section',
    't-p': 'Longitudinal',
}


def run(cfg_dir):
    """Run srw in ``cfg_dir``

    The files in ``cfg_dir`` must be configured properly.

    Args:
        cfg_dir (str): directory to run srw in
    """
    with pkio.save_chdir(cfg_dir):
        _run_elegant()


        def _plot_title(bunch):
    key = '{}-{}'.format(bunch['x'], bunch['y'])
    if key in _PLOT_TITLE:
        return _PLOT_TITLE[key]
    return '{} / {}'.format(bunch['x'], bunch['y'])


def _scale_p(points, data):
    p_central_ev = float(data['models']['bunch']['p_central_mev']) * 1e6
    return (np.array(points) * _ELEGANT_ME_EV - p_central_ev).tolist()


def _run_elegant():
    run_dir = os.getcwd()
    with open('in.json') as f:
        data = json.load(f)
    exec(pkio.read_text('elegant_parameters.py'), locals(), locals())
    pkio.write_text('elegant.lte', lattice_file)
    pkio.write_text('elegant.ele', elegant_file)
    call(['elegant', 'elegant.ele'])

    index = 0
    if sdds.sddsdata.InitializeInput(index, 'elegant.bun') != 1:
        sdds.sddsdata.PrintErrors(1)
    column_names = sdds.sddsdata.GetColumnNames(index)
    errorCode = sdds.sddsdata.ReadPage(index)
    if errorCode != 1:
        sdds.sddsdata.PrintErrors(1)
    bunch = data['models'][data['report']]
    x = sdds.sddsdata.GetColumn(index, column_names.index(bunch['x']))
    if bunch['x'] == 'p':
        x = _scale_p(x, data)
    y = sdds.sddsdata.GetColumn(index, column_names.index(bunch['y']))
    if bunch['y'] == 'p':
        y = _scale_p(y, data)
    nbins = int(bunch['histogramBins'])
    hist, edges = np.histogramdd([x, y], nbins)

    info = {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': _FIELD_LABEL[bunch['x']],
        'y_label': _FIELD_LABEL[bunch['y']],
        'title': _plot_title(bunch),
        'z_matrix': hist.T.tolist(),
    }
    with open('out.json', 'w') as outfile:
        json.dump(info, outfile)
