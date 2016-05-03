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
    frame_count = 0
    #TODO(pjm): use final output file as test
    if run_dir.join('w1.sdds').exists():
        frame_count = 1
    return {
        'percent_complete': 100,
        'frame_count': 0 if is_running else frame_count,
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
        v['lattice'] = _generate_lattice(data, schema, v)
    else:
        # use a dummy lattice with a 0 length drift for generating bunches
        v['use_beamline'] = 'bl'
        v['lattice'] = '''
d: drift,l=0
bl: line=(d)
'''
    return pkjinja.render_resource('elegant.py', v)


def get_animation_name(data):
    return data['modelName']


def get_simulation_frame(run_dir, data, model_data):
    index = 0
    if sdds.sddsdata.InitializeInput(index, str(run_dir.join('elegant.out'))) != 1:
        sdds.sddsdata.PrintErrors(1)
    column_names = sdds.sddsdata.GetColumnNames(index)
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
    if 'bunchReport' in data['report']:
        for name in [data['report'], 'bunch', 'simulation']:
            if data['models'][name] != old_data['models'][name]:
                return False
        return True
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


def _generate_lattice(data, schema, v):
    res = ''
    names = {}

    for el in data['models']['elements']:
        res += el['name'] + ': ' + el['type'] + ','
        names[el['_id']] = el['name']

        for k in el:
            if k in ['name', 'type', '_id']:
                continue
            value = el[k]
            default_value = schema['model'][el['type']][k][2]
            if value is not None and default_value is not None:
                if str(value) != str(default_value):
                    res += '{}={},'.format(k, value)
        res = res[:-1]
        res += "\n"

    for bl in data['models']['beamlines']:
        if 'use_beamline' not in v:
            v['use_beamline'] = bl['name']
        names[bl['id']] = bl['name']

    for bl in reversed(data['models']['beamlines']):
        res += bl['name'] + ': line=('
        for id in bl['items']:
            res += '{},'.format(names[id])
        if len(bl['items']):
            res = res[:-1]
        res += ")\n"

    return res


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    enum_info = template_common.parse_enums(schema['enum'])
    for k in data['models']:
        if k in schema['model']:
            template_common.validate_model(data['models'][k], schema['model'][k], enum_info)
