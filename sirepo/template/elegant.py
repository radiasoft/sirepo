# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjinja
from sirepo.template import template_common
import glob
import numpy as np
import os
import py.path
import sdds

WANT_BROWSER_FRAME_CACHE = False

_FIELD_LABEL = {
    'x': 'x [m]',
    'xp': "x' [rad]",
    'y': 'y [m]',
    'yp': "y' [rad]",
    't': 't [s]',
    'p': '(p - p₀)/p₀ [eV]',
}


def background_percent_complete(data, run_dir, is_running):
    return {
        'percent_complete': 100,
        'frame_count': 0 if is_running else 1,
    }


def copy_animation_file(source_path, target_path):
    pass


def fixup_old_data(data):
    if 'bunchReport4' not in data['models']:
        data['models']['bunchReport1'] = {
            'x': 'x',
            'y': 'xp',
            'histogramBins': 200,
        }
        data['models']['bunchReport2'] = {
            'x': 'y',
            'y': 'yp',
            'histogramBins': 200,
        }
        data['models']['bunchReport3'] = {
            'x': 'x',
            'y': 'y',
            'histogramBins': 200,
        }
        data['models']['bunchReport4'] = {
            'x': 't',
            'y': 'p',
            'histogramBins': 200,
        }
    if 'longitudinalMethod' not in data['models']['bunch']:
        bunch = data['models']['bunch']
        bunch['longitudinalMethod'] = '1'
        bunch['dp_s_coupling'] = 0
        bunch['alpha_z'] = 0
        bunch['beta_z'] = 0
        bunch['emit_z'] = 0
    if 'beamlines' not in data['models']:
        data['models']['beamlines'] = []
    if 'elements' not in data['models']:
        data['models']['elements'] = []
    if 'elementAnimation' not in data['models']:
        data['models']['elementAnimation'] = {
            'x': 'x',
            'y': 'xp',
            'histogramBins': 200,
        }
    if 'simulationStatus' not in data['models']:
        data['models']['simulationStatus'] = {
            'elementAnimation': {
                'state': 'initial',
            },
        }
    if 'beamlineReport' not in data['models']:
        data['models']['beamlineReport'] = {}


def generate_parameters_file(data, schema, run_dir=None, run_async=False):
    _validate_data(data, schema)
    v = template_common.flatten_data(data['models'], {})
    longitudinal_method = int(data['models']['bunch']['longitudinalMethod'])
    if longitudinal_method == 1:
        v['bunch_emit_z'] = 0
        v['bunch_beta_z'] = 0
        v['bunch_alpha_z'] = 0
    elif longitudinal_method == 2:
        v['bunch_emit_z'] = 0
        v['bunch_beta_z'] = 0
        v['bunch_dp_s_coupling'] = 0
    elif longitudinal_method == 3:
        v['bunch_sigma_dp'] = 0
        v['bunch_sigma_s'] = 0
        v['bunch_dp_s_coupling'] = 0
    if run_async:
        v['lattice'] = '''
q: charge,total=1e-9
B1: csrcsbend,angle=0.146607657167524,l=0.200718260855179,e1=0,e2=0.146607657167524,&
 nonlinear=1,n_kicks=100,integration_order=4,&
 bins=500,sg_halfwidth=1
B2: csrcsbend,angle=-0.146607657167524,l=0.200718260855179,e1=-0.146607657167524,e2=0,&
 nonlinear=1,n_kicks=100,integration_order=4,&
 bins=500,sg_halfwidth=1
B3: csrcsbend,angle=-0.146607657167524,l=0.200718260855179,e1=0,e2=-0.146607657167524,&
 nonlinear=1,n_kicks=100,integration_order=4,&
 bins=500,sg_halfwidth=1
B4: csrcsbend,angle=0.146607657167524,l=0.200718260855179,e1=0.146607657167524,e2=0,&
 nonlinear=1,n_kicks=100,integration_order=4,&
 bins=500,sg_halfwidth=1
w1: watch,filename="w1.sdds",mode=coord
w2: watch,filename="w2.sdds",mode=coord
w3: watch,filename="w3.sdds",mode=coord
w4: watch,filename="w4.sdds",mode=coord
w5: watch,filename="w5.sdds",mode=coord
l1: csrdrift,l=0.758132998376353,dz=0.01,use_stupakov=1
l2: csrdrift,l=0.5,dz=0.01,use_stupakov=1
l3: csrdrift,l=1.0,dz=0.01,use_stupakov=1
pf: pfilter,deltalimit=0.005
bl: line=(q,L1,w1,B1,L1,w2,B2,L2,w3,B3,L1,w4,B4,w5,l3,pf)
'''
    else:
        v['lattice'] = '''
d: drift,l=0
bl: line=(d)
'''
    return pkjinja.render_resource('elegant.py', v)


def get_animation_name(data):
    print('here: {}'.format(data['modelName']))
    return data['modelName']


def get_simulation_frame(run_dir, data, model_data):
    index = 0
    if sdds.sddsdata.InitializeInput(index, str(run_dir.join('w1.sdds'))) != 1:
        sdds.sddsdata.PrintErrors(1)
    column_names = sdds.sddsdata.GetColumnNames(index)
    print('column_names: {}'.format(column_names))
    errorCode = sdds.sddsdata.ReadPage(index)
    if errorCode != 1:
        sdds.sddsdata.PrintErrors(1)
    x = sdds.sddsdata.GetColumn(index, column_names.index('x'))
#    if bunch['x'] == 'p':
#        x = _scale_p(x, data)
    y = sdds.sddsdata.GetColumn(index, column_names.index('xp'))
#    if bunch['y'] == 'p':
#        y = _scale_p(y, data)
#    nbins = int(bunch['histogramBins'])
    nbins = 200
    hist, edges = np.histogramdd([x, y], nbins)
    return {
        'x_range': [float(edges[0][0]), float(edges[0][-1]), len(hist)],
        'y_range': [float(edges[1][0]), float(edges[1][-1]), len(hist[0])],
        'x_label': _FIELD_LABEL['x'],
        'y_label': _FIELD_LABEL['xp'],
        'title': 'Horizontal',
        'z_matrix': hist.T.tolist(),
    }


def get_data_file(run_dir, frame_index):
    for path in glob.glob(str(run_dir.join('elegant.bun'))):
        path = str(py.path.local(path))
        with open(path) as f:
            return os.path.basename(path), f.read(), 'application/octet-stream'
    raise RuntimeError('no datafile found in run_dir: {}'.format(run_dir))


def is_cache_valid(data, old_data):
    return False


def new_simulation(data, new_simulation_data):
    pass


def prepare_aux_files(run_dir, data):
    pass


def remove_last_frame(run_dir):
    pass


def run_all_text():
    return '''
'''


def static_lib_files():
    """Library shared between simulations of this type

    Returns:
        list: py.path.local objects
    """
    return []


def write_parameters(data, schema, run_dir, run_async):
    """Write the parameters file

    Args:
        data (dict): input
        schema (dict): to validate data
        run_dir (py.path): where to write
        run_async (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        generate_parameters_file(
            data,
            schema,
            run_dir,
            run_async,
        ),
    )


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.parse_enums(schema['enum'])
    for k in data['models']:
        if k in schema['model']:
            template_common.validate_model(data['models'][k], schema['model'][k], enum_info)
