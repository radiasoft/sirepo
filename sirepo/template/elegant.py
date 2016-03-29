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
import os
import py.path

WANT_BROWSER_FRAME_CACHE = False

def background_percent_complete(data, run_dir, is_running):
    pass


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
    if 'latticeGraph' not in data['models']:
        data['models']['latticeGraph'] = {}
    if 'longitudinalMethod' not in data['models']['bunch']:
        bunch = data['models']['bunch']
        bunch['longitudinalMethod'] = '1'
        bunch['dp_s_coupling'] = 0
        bunch['alpha_z'] = 0
        bunch['beta_z'] = 0
        bunch['emit_z'] = 0


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
    return pkjinja.render_resource('elegant.py', v)


def get_simulation_frame(run_dir, data):
    pass


def get_data_file(run_dir, frame_index):
    for path in glob.glob(str(run_dir.join('elegant.bun'))):
        path = str(py.path.local(path))
        with open(path) as f:
            return os.path.basename(path), f.read(), 'application/octet-stream'
    raise RuntimeError('no datafile found in run_dir: {}'.format(run_dir))


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
