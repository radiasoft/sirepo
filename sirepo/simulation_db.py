# -*- coding: utf-8 -*-
u"""Simulation database

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkinspect
from pykern import pkio
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdp
import datetime
import flask
import glob
import json
import numconv
import os
import os.path
import py
import random
import re
import sirepo.template
import werkzeug.exceptions

#: Implemented apps
SIMULATION_TYPES = ['srw', 'warp', 'elegant']

#: Json files
JSON_SUFFIX = '.json'

#: Schema common values, e.g. version
SCHEMA_COMMON = None

#: Simulation file name is globally unique to avoid collisions with simulation output
SIMULATION_DATA_FILE = 'sirepo-data' + JSON_SUFFIX

#: Where server files and static files are found
STATIC_FOLDER = py.path.local(pkresource.filename('static'))

#: How to find examples in resources
_EXAMPLE_DIR_FORMAT = '{}_examples'

#: Valid characters in ID
_ID_CHARS = numconv.BASE62

#: length of ID
_ID_LEN = 8

#: Verify ID
_ID_RE = re.compile('^[{}]{{{}}}$'.format(_ID_CHARS, _ID_LEN))

#: where users live under db_dir
_LIB_DIR = 'lib'

#: created under dir
_TMP_DIR = 'tmp'

#: Attribute in session object
_UID_ATTR = 'uid'

#: where users live under db_dir
_USER_ROOT_DIR = 'user'

#: Flask app (init() must be called to set this)
_app = None


def _json_object_pairs_hook(pairs):
    """Use OrderedMapping for json objects if possible

    Args:
        pairs (list): list of 2-tuples
    Returns:
        object: OrderedMapping if object keys are valid idents else dict
    """
    # if all([pkinspect.is_valid_identifier(p[0]) for p in pairs]):
    #   return pkcollections.OrderedMapping(pairs)
    return dict(pairs)


with open(str(STATIC_FOLDER.join('json/schema-common{}'.format(JSON_SUFFIX)))) as f:
    SCHEMA_COMMON = json.load(f, object_pairs_hook=_json_object_pairs_hook)


def examples(app):
    files = pkio.walk_tree(
        pkresource.filename(_EXAMPLE_DIR_FORMAT.format(app)),
        re.escape(JSON_SUFFIX) + '$',
    )
    return [open_json_file(app, str(f)) for f in files]


def find_global_simulation(simulation_type, sid):
    global_path = None
    for path in glob.glob(
        str(_user_dir_name().join('*', simulation_type, sid))
    ):
        if global_path:
            raise RuntimeError('{}: duplicate value for global sid'.format(sid))
        global_path = path

    if global_path:
        return global_path
    return None


def fixup_old_data(simulation_type, data):
    if 'version' in data and data['version'] == SCHEMA_COMMON['version']:
        return data
    sirepo.template.import_module(simulation_type).fixup_old_data(data)
    data['version'] = SCHEMA_COMMON['version']
    return data


def init(app):
    global _app
    _app = app


def generate_json(data):
    return json.dumps(data, cls=_JSONEncoder)


def iterate_simulation_datafiles(simulation_type, op, search=None):
    res = []
    for path in glob.glob(
        str(simulation_dir(simulation_type).join('*', SIMULATION_DATA_FILE)),
    ):
        path = py.path.local(path)
        try:
            data = open_json_file(simulation_type, path)
            if search and not _search_data(data, search):
                continue
            op(res, path, data)
        except ValueError:
            pkdp('unparseable json file: {}', path)
    return res


def open_json_file(simulation_type, path=None, sid=None):
    if not path:
        path = _simulation_data_file(simulation_type, sid)
    if not os.path.isfile(str(path)):
        global_sid = None
        if sid:
            user_copy_sid = _find_user_simulation_copy(simulation_type, sid)
            if find_global_simulation(simulation_type, sid):
                global_sid = sid
        if global_sid:
            return {
                'redirect': {
                    'simulationId': global_sid,
                    'userCopySimulationId': user_copy_sid,
                },
            }
        raise werkzeug.exceptions.NotFound()
    try:
        with open(str(path)) as f:
            data = json.load(f, object_pairs_hook=_json_object_pairs_hook)
            # ensure the simulationId matches the path
            if sid:
                data['models']['simulation']['simulationId'] = _sid_from_path(path)
            return fixup_old_data(simulation_type, data)
    except:
        pkdp('File: {}', path)
        raise


def parse_json(string):
    """Read data from json string

    Args:
        string (str): valid json
    Returns:
        object: json converted to python
    """
    return json.loads(string, object_pairs_hook=_json_object_pairs_hook)


def parse_sid(data):
    """Extract id from data file

    Args:
        data (dict): data file parsed

    Returns:
        str: simulationId from data fiel
    """
    try:
        return str(data['simulationId'])
    except KeyError:
        return str(data['models']['simulation']['simulationId'])


def process_simulation_list(res, path, data):
    res.append({
        'simulationId': _sid_from_path(path),
        'name': data['models']['simulation']['name'],
        'folder': data['models']['simulation']['folder'],
        'last_modified': datetime.datetime.fromtimestamp(
            os.path.getmtime(str(path))
        ).strftime('%Y-%m-%d %H:%M'),
        'simulation': data['models']['simulation'],
    })


def read_json(filename):
    """Read data from json file

    Args:
        filename (py.path or str): will append JSON_SUFFIX if necessary

    Returns:
        object: json converted to python
    """
    with open(_json_filename(filename)) as f:
        return json.load(f, object_pairs_hook=_json_object_pairs_hook)


def save_new_example(simulation_type, data):
    data['models']['simulation']['isExample'] = '1'
    return save_new_simulation(simulation_type, data)


def save_new_simulation(simulation_type, data):
    sid = _random_id(simulation_dir(simulation_type), simulation_type)['id']
    data['models']['simulation']['simulationId'] = sid
    save_simulation_json(simulation_type, data)
    return simulation_type, sid


def save_simulation_json(simulation_type, data):
    sid = parse_sid(data)
    if 'version' not in data:
        data['version'] = SCHEMA_COMMON['version']
    write_json(_simulation_data_file(simulation_type, sid), data)


def simulation_dir(simulation_type, sid=None):
    """Generates simulation directory from sid and simulation_type

    Args:
        simulation_type (str): srw, warp, ...
        sid (str): simulation id (optional)
    """
    d = _user_dir().join(simulation_type)
    if not sid:
        return d
    if not _ID_RE.search(sid):
        raise RuntimeError('{}: invalid simulation id'.format(sid))
    return d.join(sid)


def simulation_lib_dir(simulation_type):
    """String name for user library dir

    Args:
        simulation_type: which app is this for

    Return:
        py.path: directory name
    """
    return simulation_dir(simulation_type).join(_LIB_DIR)


def simulation_run_dir(data, remove_dir=False):
    """Where to run the simulation

    Args:
        data (dict): contains simulationType and simulationId
        remove_dir (bool): remove the directory [False]

    Returns:
        py.path: directory to run
    """
    d = simulation_dir(data['simulationType'], parse_sid(data)).join(_report_name(data))
    if remove_dir:
        pkio.unchecked_remove(d)
    return d


def tmp_dir():
    """Generates tmp directory for the user

    Returns:
        py.path: directory to use for temporary work
    """
    return pkio.mkdir_parent(_random_id(_user_dir().join(_TMP_DIR))['path'])


def verify_app_directory(simulation_type):
    """Ensure the app directory is present. If not, create it and add example files.
    """
    d = simulation_dir(simulation_type)
    if d.exists():
        return
    _create_example_and_lib_files(simulation_type)


def write_json(filename, data):
    """Write data as json to filename

    Args:
        filename (py.path or str): will append JSON_SUFFIX if necessary
    """
    with open(_json_filename(filename), 'w') as f:
        json.dump(data, f, indent=4, separators=(',', ': '), sort_keys=True, cls=_JSONEncoder)


class _JSONEncoder(json.JSONEncoder, object):
    """Encode objects that container OrderedMapping
    """
    def default(self, obj):
        """If OrderedMapping, return dict

        Args:
            obj (object): Any object to convert to JSON
        Returns:
            object: dict if OrderedMapping else super()
        """
        # if isinstance(obj, pkcollections.OrderedMapping):
        #    return pkcollections.map_to_dict(obj)
        return super(_JSONEncoder, self).default(obj)


def _create_example_and_lib_files(simulation_type):
    d = simulation_dir(simulation_type)
    pkio.mkdir_parent(d)
    for s in examples(simulation_type):
        save_new_example(simulation_type, s)
    d = simulation_lib_dir(simulation_type)
    pkio.mkdir_parent(d)
    for f in sirepo.template.import_module(simulation_type).static_lib_files():
        f.copy(d)


def _find_user_simulation_copy(simulation_type, sid):
    rows = iterate_simulation_datafiles(simulation_type, process_simulation_list, {
        'simulation.outOfSessionSimulationId': sid,
    })
    if len(rows):
        return rows[0]['simulationId']
    return None


def _json_filename(filename):
    """Append JSON_SUFFIX if necessary and convert to str

    Args:
        filename (py.path or str): to convert
    Returns:
        str: filename.json
    """
    filename = str(filename)
    if not filename.endswith(JSON_SUFFIX):
        filename += JSON_SUFFIX
    return filename


def _random_id(parent_dir, simulation_type=None):
    """Create a random id in parent_dir

    Args:
        parent_dir (py.path): where id should be unique
    Returns:
        dict: id (str) and path (py.path)
    """
    pkio.mkdir_parent(parent_dir)
    r = random.SystemRandom()
    # Generate cryptographically secure random string
    for _ in range(5):
        i = ''.join(r.choice(_ID_CHARS) for x in range(_ID_LEN))
        if simulation_type:
            if find_global_simulation(simulation_type, i):
                continue
        d = parent_dir.join(i)
        try:
            os.mkdir(str(d))
            return dict(id=i, path=d)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            raise
    raise RuntimeError('{}: failed to create unique directory'.format(parent_dir))


def _report_name(data):
    """Extract report name from data

    Animations don't have a report name so we just return animation.

    Args:
        data (dict): passed in params
    Returns:
        str: name of the report requested in the data
    """
    return data['report']


def _search_data(data, search):
    for field in search:
        path = field.split('.')
        if len(path) == 1:
            continue
        path.insert(0, 'models')
        v = data
        for key in path:
            if key in v:
                v = v[key]
        if v != search[field]:
            return False
    return True


def _sid_from_path(path):
    sid = os.path.split(os.path.split(str(path))[0])[1]
    if not _ID_RE.search(sid):
        raise RuntimeError('{}: invalid simulation id'.format(sid))
    return sid


def _simulation_data_file(simulation_type, sid):
    return str(simulation_dir(simulation_type, sid).join(SIMULATION_DATA_FILE))


def _user_dir():
    """User for the session

    Returns:
        str: unique id for user from flask session
    """
    if not _UID_ATTR in flask.session:
        _user_dir_create()
    d = _user_dir_name(flask.session[_UID_ATTR])
    if d.check():
        return d
    # Beaker session might have been deleted (in dev) so "logout" and "login"
    _user_dir_create()
    return _user_dir_name(flask.session[_UID_ATTR])


def _user_dir_create():
    """Create a user and initialize the directory"""
    uid = _random_id(_user_dir_name())['id']
    # Must set before calling simulation_dir
    flask.session[_UID_ATTR] = uid
    for simulation_type in SIMULATION_TYPES:
        _create_example_and_lib_files(simulation_type)


def _user_dir_name(uid=None):
    """String name for user name

    Args:
        uid (str): properly formated user name (optional)
    Return:
        py.path: directory name
    """
    d = _app.sirepo_db_dir.join(_USER_ROOT_DIR)
    if not uid:
        return d
    return d.join(uid)
