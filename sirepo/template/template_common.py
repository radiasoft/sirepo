# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp
from pykern import pkresource
import copy
import hashlib
import json
import py.path
import re
import sirepo.template

DEFAULT_INTENSITY_DISTANCE = 20

#: Input json file
INPUT_BASE_NAME = 'in'

#: Output json file
OUTPUT_BASE_NAME = 'out'

#: Python file (not all simulations)
PARAMETERS_PYTHON_FILE = 'parameters.py'

#: stderr and stdout
RUN_LOG = 'run.log'

RESOURCE_DIR = py.path.local(pkresource.filename('template'))

LIB_FILE_PARAM_RE = re.compile(r'.*File$')

_HISTOGRAM_BINS_MAX = 500

_WATCHPOINT_REPORT_NAME = 'watchpointReport'

def flatten_data(d, res, prefix=''):
    """Takes a nested dictionary and converts it to a single level dictionary with flattened keys."""
    for k in d:
        v = d[k]
        if isinstance(v, dict):
            flatten_data(v, res, prefix + k + '_')
        elif isinstance(v, list):
            pass
        else:
            res[prefix + k] = v
    return res


def histogram_bins(nbins):
    """Ensure the histogram count is in a valid range"""
    nbins = int(nbins)
    if nbins <= 0:
        nbins = 1
    elif nbins > _HISTOGRAM_BINS_MAX:
        nbins = _HISTOGRAM_BINS_MAX
    return nbins


def internal_lib_files(files, source_lib):
    """Return list of files used by the simulation

    Args:
        data (dict): sim db

    Returns:
        list: py.path.local to files
    """
    res = []
    seen = set()
    for f in files:
        if f not in seen:
            seen.add(f)
            res.append(source_lib.join(f))
    return res


def is_watchpoint(name):
    return _WATCHPOINT_REPORT_NAME in name


def lib_files(data):
    """Return list of files used by the simulation

    Args:
        data (dict): sim db

    Returns:
        list: py.path.local to files
    """
    from sirepo import simulation_db
    sim_type = data.simulationType
    return sirepo.template.import_module(data).lib_files(
        data,
        simulation_db.simulation_lib_dir(sim_type),
    )


def parse_enums(enum_schema):
    """Returns a list of enum values, keyed by enum name."""
    res = {}
    for k in enum_schema:
        res[k] = {}
        for v in enum_schema[k]:
            res[k][v[0]] = True
    return res


def resource_dir(sim_type):
    """Where to get library files from

    Args:
        sim_type (str): application name
    Returns:
        py.path.Local: absolute path to folder
    """
    return RESOURCE_DIR.join(sim_type)


def report_parameters_hash(data):
    """Compute a hash of the parameters for his report.

    Only needs to be unique relative to the report, not globally unique
    so MD5 is adequate. Long and cryptographic hashes make the
    cache checks slower.

    Args:
        data (dict): report and related models
    Returns:
        str: url safe encoded hash
    """
    if not 'reportParametersHash' in data:
        models = sirepo.template.import_module(data).models_related_to_report(data)
        res = hashlib.md5()
        dm = data['models']
        for m in models:
            if isinstance(m, basestring):
                name, field = m.split('.') if '.' in m else (m, None)
                value = dm[name][field] if field else dm[name]
            else:
                value = m
            res.update(json.dumps(value, sort_keys=True))
        data['reportParametersHash'] = res.hexdigest()
    return data['reportParametersHash']


def validate_model(model_data, model_schema, enum_info):
    """Ensure the value is valid for the field type. Scales values as needed."""
    for k in model_schema:
        label = model_schema[k][0]
        field_type = model_schema[k][1]
        if k in model_data:
            value = model_data[k]
        elif len(model_schema[k]) > 2:
            value = model_schema[k][2]
        else:
            raise Exception('no value for field "{}" and no default value in schema'.format(k))
        if field_type in enum_info:
            if str(value) not in enum_info[field_type]:
                raise Exception('invalid enum value: {} for {}'.format(value, k))
        elif field_type == 'Float':
            if not value:
                value = 0
            v = float(value)
            if re.search('\[m(m|rad)\]', label) or re.search('\[Lines/mm', label):
                v /= 1000
            elif re.search('\[n(m|rad)\]', label) or re.search('\[nm/pixel\]', label):
                v /= 1e09
            elif re.search('\[ps]', label):
                v /= 1e12
            #TODO(pjm): need to handle unicode in label better (mu)
            elif re.search('\[\xb5(m|rad)\]', label):
                v /= 1e6
            model_data[k] = float(v)
        elif field_type == 'Integer':
            if not value:
                value = 0
            model_data[k] = int(value)
        elif field_type in (
                'BeamList', 'MirrorFile', 'ImageFile', 'String', 'OptionalString', 'MagneticZipFile',
                'ValueList', 'Array', 'InputFile', 'RPNValue', 'OutputFile', 'StringArray',
                'InputFileXY', 'BeamInputFile', 'ElegantBeamlineList', 'ElegantLatticeList',
                'RPNBoolean', 'UndulatorList', 'ReflectivityMaterial',
        ):
            model_data[k] = _escape(value)
        else:
            raise Exception('unknown field type: {} for {}'.format(field_type, k))


def validate_models(model_data, model_schema):
    """Validate top-level models in the schema. Returns enum_info."""
    enum_info = parse_enums(model_schema['enum'])
    for k in model_data['models']:
        if k in model_schema['model']:
            validate_model(model_data['models'][k], model_schema['model'][k], enum_info)
    if 'beamline' in model_data['models']:
        for m in model_data['models']['beamline']:
            validate_model(m, model_schema['model'][m['type']], enum_info)
    return enum_info


def watchpoint_id(report):
    m = re.search(_WATCHPOINT_REPORT_NAME + '(\d+)', report)
    if not m:
        raise RuntimeError('invalid watchpoint report name: ', report)
    return int(m.group(1))


def _escape(v):
    return re.sub("['()]", '', str(v))
