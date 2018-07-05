# -*- coding: utf-8 -*-
u"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkcompat
from pykern import pkio
from pykern import pkjinja
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdlog, pkdp
import hashlib
import json
import py.path
import os.path
import re
import sirepo.template

ANIMATION_ARGS_VERSION_RE = re.compile(r'v(\d+)$')

DEFAULT_INTENSITY_DISTANCE = 20

#: Input json file
INPUT_BASE_NAME = 'in'

LIB_FILE_PARAM_RE = re.compile(r'.*File$')

#: Output json file
OUTPUT_BASE_NAME = 'out'

#: Python file (not all simulations)
PARAMETERS_PYTHON_FILE = 'parameters.py'

#: stderr and stdout
RUN_LOG = 'run.log'

_HISTOGRAM_BINS_MAX = 500

_PLOT_LINE_COLOR = ['#1f77b4', '#ff7f0e', '#2ca02c']

_RESOURCE_DIR = py.path.local(pkresource.filename('template'))

_WATCHPOINT_REPORT_NAME = 'watchpointReport'


def compute_plot_color_and_range(plots):
    """ For parameter plots, assign each plot a color and compute the full y_range. """
    y_range = None
    for i in range(len(plots)):
        plot = plots[i]
        plot['color'] = _PLOT_LINE_COLOR[i]
        vmin = min(plot['points'])
        vmax = max(plot['points'])
        if y_range:
            if vmin < y_range[0]:
                y_range[0] = vmin
            if vmax > y_range[1]:
                y_range[1] = vmax
        else:
            y_range = [vmin, vmax]
    return y_range


def copy_lib_files(data, source, target):
    """Copy auxiliary files to target

    Args:
        data (dict): simulation db
        target (py.path): destination directory
    """
    for f in lib_files(data, source):
        path = target.join(f.basename)
        pkio.mkdir_parent_only(path)
        if not path.exists():
            if not f.exists():
                sim_resource = resource_dir(data.simulationType)
                r = sim_resource.join(f.basename)
                # the file doesn't exist in the simulation lib, check the resource lib
                if r.exists():
                    pkio.mkdir_parent_only(f)
                    r.copy(f)
                else:
                    pkdlog('No file in lib or resource: {}', f)
                    continue
            if source:
                # copy files from another session
                f.copy(path)
            else:
                # symlink into the run directory
                path.mksymlinkto(f, absolute=False)



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


def filename_to_path(files, source_lib):
    """Returns full, unique paths of simulation files

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


def histogram_bins(nbins):
    """Ensure the histogram count is in a valid range"""
    nbins = int(nbins)
    if nbins <= 0:
        nbins = 1
    elif nbins > _HISTOGRAM_BINS_MAX:
        nbins = _HISTOGRAM_BINS_MAX
    return nbins


def is_watchpoint(name):
    return _WATCHPOINT_REPORT_NAME in name


def lib_file_name(model_name, field, value):
    return '{}-{}.{}'.format(model_name, field, value)


def lib_files(data, source_lib=None):
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
        source_lib or simulation_db.simulation_lib_dir(sim_type),
    )


def model_defaults(name, schema):
    """Returns a set of default model values from the schema."""
    res = pkcollections.Dict()
    for f in schema['model'][name]:
        field_info = schema['model'][name][f]
        if len(field_info) >= 3 and field_info[2] is not None:
            res[f] = field_info[2]
    return res


def parse_animation_args(data, key_map):
    """Parse animation args according to key_map

    Args:
        data (dict): contains animationArgs
        key_map (dict): version to keys mapping, default is ''
    Returns:
        Dict: mapped animationArgs with version
    """
    a = data['animationArgs'].split('_')
    m = ANIMATION_ARGS_VERSION_RE.search(a[0])
    if m:
        a.pop(0)
        v = int(m.group(1))
    else:
        v = 1
    try:
        keys = key_map[v]
    except KeyError:
        keys = key_map['']
    res = pkcollections.Dict(zip(keys, a))
    res.version = v
    return res


def parse_enums(enum_schema):
    """Returns a list of enum values, keyed by enum name."""
    res = {}
    for k in enum_schema:
        res[k] = {}
        for v in enum_schema[k]:
            res[k][v[0]] = True
    return res


def render_jinja(sim_type, v, name=PARAMETERS_PYTHON_FILE):
    """Render the values into a jinja template.

    Args:
        sim_type (str): application name
        v: flattened model data
    Returns:
        str: source text
    """
    b = resource_dir(sim_type).join(name)
    return pkjinja.render_file(b + '.jinja', v)


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
            if pkcompat.isinstance_str(m):
                name, field = m.split('.') if '.' in m else (m, None)
                value = dm[name][field] if field else dm[name]
            else:
                value = m
            res.update(json.dumps(value, sort_keys=True, allow_nan=False).encode())
        data['reportParametersHash'] = res.hexdigest()
    return data['reportParametersHash']

def report_fields(data, report_name, style_fields):
    # if the model has "style" fields, then return the full list of non-style fields
    # otherwise returns the report name (which implies all model fields)
    m = data.models[report_name]
    for style_field in style_fields:
        if style_field not in m:
            continue
        res = []
        for f in m:
            if f in style_fields:
                continue
            res.append('{}.{}'.format(report_name, f))
        return res
    return [report_name]


def resource_dir(sim_type):
    """Where to get library files from

    Args:
        sim_type (str): application name
    Returns:
        py.path.Local: absolute path to folder
    """
    return _RESOURCE_DIR.join(sim_type)


def update_model_defaults(model, name, schema):
    defaults = model_defaults(name, schema)
    for f in defaults:
        if f not in model:
            model[f] = defaults[f]


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
                # Check a comma-delimited string against the enumeration
                for item in re.split(r'\s*,\s*', str(value)):
                    if item not in enum_info[field_type]:
                        assert item in enum_info[field_type], \
                            '{}: invalid enum "{}" value for field "{}"'.format(item, field_type, k)
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
            elif re.search('\[\xb5(m|rad)\]', label) or re.search('\[mm-mrad\]', label):
                v /= 1e6
            model_data[k] = float(v)
        elif field_type == 'Integer':
            if not value:
                value = 0
            model_data[k] = int(value)
        else:
            model_data[k] = _escape(value)


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


def file_extension_ok(file_path, white_list=[], black_list=['py', 'pyc']):
    """Determine whether a file has an acceptable extension

    Args:
        file_path (str): name of the file to examine
        white_list ([str]): list of file types allowed (defaults to empty list)
        black_list ([str]): list of file types rejected (defaults to ['py', 'pyc']). Ignored if white_list is not empty
    Returns:
        If file is a directory: True
        If white_list non-empty: True if the file's extension matches any in the list, otherwise False
        If white_list is empty: False if the file's extension matches any in black_list, otherwise True
    """
    import os

    if os.path.isdir(file_path):
        return True
    if len(white_list) > 0:
        in_list = False
        for ext in white_list:
            in_list = in_list or pkio.has_file_extension(file_path, ext)
        if not in_list:
            return False
        return True
    for ext in black_list:
        if pkio.has_file_extension(file_path, ext):
            return False
    return  True

def validate_safe_zip(zip_file_name, target_dir='.', *args):
    """Determine whether a zip file is safe to extract from

    Performs the following checks:

        - Each file must end up at or below the target directory
        - Files must be 100MB or smaller
        - If possible to determine, disallow "non-regular" and executable files
        - Existing files cannot be overwritten

    Args:
        zip_file_name (str): name of the zip file to examine
        target_dir (str): name of the directory to extract into (default to current directory)
        *args: list of validator functions taking a zip file as argument and returning True or False and a string
    Throws:
        AssertionError if any test fails, otherwise completes silently
    """
    import zipfile
    import os

    def path_is_sub_path(path, dir_name):
        real_dir = os.path.realpath(dir_name)
        end_path = os.path.realpath(real_dir + '/' + path)
        return end_path.startswith(real_dir)

    def file_exists_in_dir(file_name, dir_name):
        return os.path.exists(os.path.realpath(dir_name + '/' + file_name))

    def file_attrs_ok(attrs):

        # ms-dos attributes only use two bytes and don't contain much useful info, so pass them
        if attrs < 2 << 16:
            return True

        # UNIX file attributes live in the top two bytes
        mask = attrs >> 16
        is_file_or_dir = mask & (0o0100000 | 0o0040000) != 0
        no_exec = mask & (0o0000100 | 0o0000010 | 0o0000001) == 0

        return is_file_or_dir and no_exec

    # 100MB
    max_file_size = 100000000

    zip_file = zipfile.ZipFile(zip_file_name)

    for f in zip_file.namelist():

        i = zip_file.getinfo(f)
        s = i.file_size
        attrs = i.external_attr

        assert path_is_sub_path(f, target_dir), 'Cannot extract {} above target directory'.format(f)
        assert s <= max_file_size, '{} too large ({} > {})'.format(f, str(s), str(max_file_size))
        assert file_attrs_ok(attrs), '{} not a normal file or is executable'.format(f)
        assert not file_exists_in_dir(f, target_dir), 'Cannot overwrite file {} in target directory {}'.format(f, target_dir)

    for validator in args:
        res, err_string = validator(zip_file)
        assert res, '{} failed validator: {}'.format(os.path.basename(zip_file_name), err_string)


def zip_path_for_file(zf, file_to_find):
    """Find the full path of the specified file within the zip.

    For a zip zf containing:
        foo1
        foo2
        bar/
        bar/foo3

    zip_path_for_file(zf, 'foo3') will return 'bar/foo3'

    Args:
        zf(zipfile.ZipFile): the zip file to examine
        file_to_find (str): name of the file to find

    Returns:
        The first path in the zip that matches the file name, or None if no match is found
    """
    import os

    # Get the base file names from the zip (directories have a basename of '')
    file_names_in_zip = map(lambda path: os.path.basename(path),  zf.namelist())
    return zf.namelist()[file_names_in_zip.index(file_to_find)]


def watchpoint_id(report):
    m = re.search(_WATCHPOINT_REPORT_NAME + '(\d+)', report)
    if not m:
        raise RuntimeError('invalid watchpoint report name: ', report)
    return int(m.group(1))


def _escape(v):
    return re.sub("[\"'()]", '', str(v))
