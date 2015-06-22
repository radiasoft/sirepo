
#TODO(pjm): this whole file need to be completely reworked

#TODO(pjm): refine imports
from pykern import pkio
from uti_plot import *
from uti_plot_com import *
import default_parameters
import json
import numpy as np
import os
import re
import srwl_bl
import sys

if not sys.argv[1]:
    raise Exception("missing argv[1]")

dir = sys.argv[1]

def superscript(val):
    return re.sub(r'\^2', u'\u00B2', val)

def remap_3d(info, allrange, z_label, z_units):
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
    x = np.linspace(x_range[0],x_range[1],x_range[2])
    y = np.linspace(y_range[0],y_range[1],y_range[2])
    return {
        'x_range': x.tolist(),
        'y_range': y.tolist(),
        'x_label': info['x_label'],
        'y_label': info['y_label'],
        'z_label': superscript(z_label + ' [' + z_units + ']'),
        'title': info['title'],
        'z_matrix': ar2d.tolist(),
    }

def process_output(filename):
    sValShort = 'Flux'; sValType = 'Flux through Finite Aperture'; sValUnit = 'ph/s/.1%bw'

    is_3d = {
        'res_pow.dat': True,
        'res_int_se.dat': True,
        'res_int_pr_se.dat': True,
    }
    file_info = {
        'res_spec_se.dat': [['Photon Energy', 'Intensity', 'On-Axis Spectrum'], ['eV', 'ph/s/.1%bw/mm^2']],
        'res_spec_me.dat': [['Photon Energy', sValShort, sValType], ['eV', sValUnit]],
        'res_pow.dat': [['Horizontal Position', 'Vertical Position', 'Power Density', 'Power Density'], ['m', 'm', 'W/mm^2']],
        'res_int_se.dat': [['Horizontal Position', 'Vertical Position', 'Intensity Before Propagation', 'Intensity'], ['m', 'm', 'ph/s/.1%bw/mm^2']],
        'res_int_pr_se.dat': [['Horizontal Position', 'Vertical Position', 'Intensity After Propagation', 'Intensity'], ['m', 'm', 'ph/s/.1%bw/mm^2']],
    }

    data, mode, allrange, arLabels, arUnits = uti_plot_com.file_load(filename)

    print(allrange)
    info = {
        'title': file_info[filename][0][2],
        'x_range': [allrange[0], allrange[1]],
        'y_label': superscript(file_info[filename][0][1] + ' [' + file_info[filename][1][1] + ']'),
        'x_label': file_info[filename][0][0] + ' [' + file_info[filename][1][0] + ']',
        'x_units': file_info[filename][1][0],
        'points': data.tolist(),
    }
    if is_3d.get(filename):
        info = remap_3d(info, allrange, file_info[filename][0][3], file_info[filename][1][2])
    with open('out.json', 'w') as outfile:
        json.dump(info, outfile)


with pkio.save_chdir(dir):

    with open('in.json') as f:
        data = json.load(f)

    print('{}'.format(data))

    v = srwl_bl.srwl_uti_parse_options(default_parameters.varParam)
    v.fdir = os.getcwd()
    v.name = 'NSLS-II CHX beamline Day 1'
    v.ss_pl = ''
    v.sm_pl = ''
    v.pw_pl = ''
    v.ws_pl = ''

    # electron beam
    #"beamName":{name":"NSLS-II Low Beta Day 1"}
    #"current":0.5,
    #"horizontalPosition":0,
    #"verticalPosition":0,
    #"energyDeviation":0}
    electronBeam = data['models']['electronBeam']
    v.ebm_nm = electronBeam['beamName']['name']
    v.ebm_nms = ''
    v.ebm_i = float(electronBeam['current'])
    v.ebm_de = float(electronBeam['energyDeviation'])
    v.ebm_x = float(electronBeam['horizontalPosition'])
    v.ebm_y = float(electronBeam['verticalPosition'])

    # undulator
    #"undulator":{"_visible":true,"period":0.02,"length":3,"longitudinalPosition":0,"horizontalAmplitude":0.88770981,"horizontalSymmetry":"Symmetrical","horizontalInitialPhase":0,"verticalAmplitude":0,"verticalSymmetry":"Anti-symmetrical","verticalInitialPhase":0},
    undulator = data['models']['undulator']
    v.und_b = float(undulator['horizontalAmplitude'])
    v.und_per = float(undulator['period'])
    v.und_len = float(undulator['length'])
    v.und_zc = float(undulator['longitudinalPosition'])
    #v.und_sy = undulator['horizontalSymmetry']
    #v.und_sx = undulator['verticalSymmetry']

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
    elif data['report'] == 'initialIntensityReport':
        v.si = True
        outfile = v.si_fn
    elif data['report'] == 'intensityAtSampleReport':
        v.ws = True
        outfile = v.ws_fni
    else:
        raise Exception('unknown report: {}'.format(data['report']))

    #TODO(pjm): need a signal/alarm to stop long processes
    srwl_bl.SRWLBeamline(v.name).calc_all(v, op)
    process_output(outfile)


print("done")
