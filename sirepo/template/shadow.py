# -*- coding: utf-8 -*-
u"""shadow execution template.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common

#: Simulation type
SIM_TYPE = 'shadow'


def copy_related_files(data, source_path, target_path):
    pass


def fixup_old_data(data):
    pass


def models_related_to_report(data):
    """What models are required for this data['report']

    Args:
        data (dict): simulation
    Returns:
        list: Named models, model fields or values (dict, list) that affect report
    """
    r = data['report']
    res = [
        r,
        'bendingMagnet',
        'rayFilter',
    ]
    if r == 'initialIntensityReport' and len(data['models']['beamline']):
        res.append([data['models']['beamline'][0]['position']])
    #TODO(pjm): only include items up to the current watchpoint
    if template_common.is_watchpoint(r):
        res.append('beamline')
    return res


def new_simulation(data, new_simulation_data):
    pass


def prepare_aux_files(run_dir, data):
    pass


def prepare_for_client(data):
    return data


def prepare_for_save(data):
    return data


def remove_last_frame(run_dir):
    pass


def resource_files():
    return []


def write_parameters(data, schema, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        schema (dict): to validate data
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(
            data,
            run_dir,
            is_parallel,
        ),
    )


_CENTIMETER_FIELDS = {
    'bendingMagnet': ['sigmax', 'sigmaz', 'epsi_x', 'epsi_z'],
    'rayFilter': ['distance', 'x1', 'x2', 'z1', 'z2'],
    'aperture': ['position', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
    'obstacle': ['position', 'horizontalSize', 'verticalSize', 'horizontalOffset', 'verticalOffset'],
    'histogramReport': ['distanceFromSource'],
    'plotXYReport': ['distanceFromSource'],
    'watch': ['position'],
}

def _convert_meters_to_centimeters(models):
    for m in models:
        if isinstance(m, dict):
            name = m['type']
            model = m
        else:
            name = m
            model = models[m]
        if name in _CENTIMETER_FIELDS:
            for f in _CENTIMETER_FIELDS[name]:
                model[f] *= 100


def _generate_beamline_optics(models, last_id):
    beamline = models['beamline']
    res = ''
    prev_position = 0
    last_element = False
    count = 0
    for item in beamline:
        if 'isDisabled' in item and item['isDisabled']:
            continue
        count += 1
        res += '''
oe = Shadow.OE()
        '''
        if item['type'] == 'aperture' or item['type'] == 'obstacle':
            res += _generate_screen(item)
        elif item['type'] == 'watch':
            res += '''
oe.set_empty()
            '''
            if last_id and last_id == int(item['id']):
                last_element = True
        else:
            raise RuntimeError('unknown item type: {}'.format(item))
        res += '''
oe.FWRITE = 3
oe.T_IMAGE = 0.0
oe.T_SOURCE = {}
beam.traceOE(oe, {})
        '''.format(item.position - prev_position, count)
        prev_position = item.position
        if last_element:
            break
    return res


def _generate_parameters_file(data, run_dir=None, is_parallel=False):
    _validate_data(data, simulation_db.get_schema(SIM_TYPE))
    _convert_meters_to_centimeters(data['models'])
    _convert_meters_to_centimeters(data['models']['beamline'])
    v = template_common.flatten_data(data['models'], {})
    r = data['report']
    report_model = data['models'][r]
    beamline = data['models']['beamline']

    if r == 'initialIntensityReport':
        v['distanceFromSource'] = beamline[0]['position'] if len(beamline) else template_common.DEFAULT_INTENSITY_DISTANCE
    elif template_common.is_watchpoint(r):
        v['beamlineOptics'] = _generate_beamline_optics(data['models'], template_common.watchpoint_id(r))
    else:
        v['distanceFromSource'] = report_model['distanceFromSource']
    return pkjinja.render_resource('shadow.py', v)


def _generate_screen(item):
    res = '''
oe.set_empty().set_screens()
oe.I_SLIT[0] = 1
oe.K_SLIT[0] = {}
oe.I_STOP[0] = {}
oe.RX_SLIT[0] = {}
oe.RZ_SLIT[0] = {}
oe.CX_SLIT[0] = {}
oe.CZ_SLIT[0] = {}
    '''.format(
        item['shape'],
        0 if item['type'] == 'aperture' else 1,
        item['horizontalSize'],
        item['verticalSize'],
        item['horizontalOffset'],
        item['verticalOffset'],
    )
    return res


def _validate_data(data, schema):
    template_common.validate_models(data, schema)
