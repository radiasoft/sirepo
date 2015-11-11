# -*- coding: utf-8 -*-
"""Wrapper to run SRW from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import json
import numpy as np
import re
import srwl_bl
import srwlib

from pykern import pkio
from pykern.pkdebug import pkdc, pkdp
from uti_plot import *
from uti_plot_com import *


def run(cfg_dir):
    """Run srw in ``cfg_dir``

    The files in ``cfg_dir`` must be configured properly.

    Args:
        cfg_dir (str): directory to run srw in
    """
    with pkio.save_chdir(cfg_dir):
        _run_srw()


def _mirror_plot(model_data):
    mirror = model_data['models']['mirrorReport']
    element = srwlib.srwl_opt_setup_surf_height_1d(
        srwlib.srwl_uti_read_data_cols(mirror['heightProfileFile'], "\t", 0, 1),
        _dim=mirror['orientation'],
        _ang=float(mirror['grazingAngle']) / 1e3,
        _amp_coef=float(mirror['heightAmplification']))
        #_size_x=float(mirror['horizontalTransverseSize']) / 1e3,
        #_size_y=float(mirror['verticalTransverseSize']) / 1e3)
    transmission_data = element.get_data(3, 3)
    srwlib.srwl_uti_save_intens_ascii(
        transmission_data, element.mesh, 'res_mirror.dat', 0,
        ['', 'Horizontal Position', 'Vertical Position', 'Optical Path Difference'], _arUnits=['', 'm', 'm', ''])
    return 'res_mirror.dat'

def _process_output(filename, model_data):
    sValShort = 'Flux'; sValType = 'Flux through Finite Aperture'; sValUnit = 'ph/s/.1%bw'
    if model_data['models']['fluxReport']['fluxType'] == 2:
        sValShort = 'Intensity'
        sValUnit = 'ph/s/.1%bw/mm^2'
    is_3d = {
        'res_pow.dat': True,
        'res_int_se.dat': True,
        'res_int_pr_se.dat': True,
        'res_mirror.dat': True,
    }
    file_info = {
        'res_spec_se.dat': [['Photon Energy', 'Intensity', 'On-Axis Spectrum from Filament Electron Beam'], ['eV', 'ph/s/.1%bw/mm^2']],
        'res_spec_me.dat': [['Photon Energy', sValShort, sValType], ['eV', sValUnit]],
        'res_pow.dat': [['Horizontal Position', 'Vertical Position', 'Power Density', 'Power Density'], ['m', 'm', 'W/mm^2']],
        'res_int_se.dat': [['Horizontal Position', 'Vertical Position', '{} eV Before Propagation', 'Intensity'], ['m', 'm', 'ph/s/.1%bw/mm^2']],
        'res_int_pr_se.dat': [['Horizontal Position', 'Vertical Position', '{} eV After Propagation', 'Intensity'], ['m', 'm', 'ph/s/.1%bw/mm^2']],
        'res_mirror.dat': [['Horizontal Position', 'Vertical Position', 'Optical Path Difference', 'Height'], ['m', 'm', 'm']],
    }

    data, mode, allrange, arLabels, arUnits = uti_plot_com.file_load(filename)

    title = file_info[filename][0][2]
    if '{' in title:
        title = title.format(model_data['models'][model_data['report']]['photonEnergy'])
    info = {
        'title': title,
        'x_range': [allrange[0], allrange[1]],
        'y_label': _superscript(file_info[filename][0][1] + ' [' + file_info[filename][1][1] + ']'),
        'x_label': file_info[filename][0][0] + ' [' + file_info[filename][1][0] + ']',
        'x_units': file_info[filename][1][0],
        'points': data.tolist(),
    }
    if is_3d.get(filename):
        info = _remap_3d(info, allrange, file_info[filename][0][3], file_info[filename][1][2])
    with open('out.json', 'w') as outfile:
        json.dump(info, outfile)


def _remap_3d(info, allrange, z_label, z_units):
    x_range = [allrange[3], allrange[4], allrange[5]]
    y_range = [allrange[6], allrange[7], allrange[8]]
    ar2d = info['points']

    totLen = int(x_range[2]*y_range[2])
    lenAr2d = len(ar2d)
    if lenAr2d > totLen: ar2d = np.array(ar2d[0:totLen])
    elif lenAr2d < totLen:
        auxAr = array('d', [0]*lenAr2d)
        for i in range(lenAr2d): auxAr[i] = ar2d[i]
        ar2d = np.array(auxAr)
    if isinstance(ar2d,(list,array)): ar2d = np.array(ar2d)
    ar2d = ar2d.reshape(y_range[2],x_range[2])
    return {
        'x_range': x_range,
        'y_range': y_range,
        'x_label': info['x_label'],
        'y_label': info['y_label'],
        'z_label': _superscript(z_label + ' [' + z_units + ']'),
        'title': info['title'],
        'z_matrix': ar2d.tolist(),
    }

def _run_srw():
    with open('in.json') as f:
        data = json.load(f)
    #TODO(pjm): need to properly escape data values, untrusted from client
    # this defines the get_srw_params() and get_beamline_optics() functions
    exec(pkio.read_text('srw_parameters.py'), locals(), locals())
    v = srwl_bl.srwl_uti_parse_options(get_srw_params())
    source_type, mag = setup_source(v)
    op = None
    if data['report'] == 'intensityReport':
        v.ss = True
        outfile = v.ss_fn
    elif data['report'] == 'fluxReport':
        v.sm = True
        outfile = v.sm_fn
    elif data['report'] == 'powerDensityReport':
        v.pw = True
        outfile = v.pw_fn
    elif data['report'] == 'initialIntensityReport' or data['report'] == 'gaussianBeamIntensityReport':
        v.si = True
        outfile = v.si_fn
    elif data['report'] == 'mirrorReport':
        _process_output(_mirror_plot(data), data)
        return
    elif re.search('^watchpointReport', data['report']):
        op = get_beamline_optics()
        v.ws = True
        outfile = v.ws_fni
    else:
        raise Exception('unknown report: {}'.format(data['report']))
    srwl_bl.SRWLBeamline(_name=v.name, _mag_approx=mag).calc_all(v, op)
    _process_output(outfile, data)

def _superscript(val):
    return re.sub(r'\^2', u'\u00B2', val)
