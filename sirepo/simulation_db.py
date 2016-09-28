# -*- coding: utf-8 -*-
u"""Simulation database

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern import pkresource
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo.template import template_common
import copy
import datetime
import errno
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
import threading
import time
import werkzeug.exceptions

#: Json files
JSON_SUFFIX = '.json'

#: Schema common values, e.g. version
SCHEMA_COMMON = None

#: Simulation file name is globally unique to avoid collisions with simulation output
SIMULATION_DATA_FILE = 'sirepo-data' + JSON_SUFFIX

#: Implemented apps
SIMULATION_TYPES = ['srw', 'warp', 'elegant']

#: Where server files and static files are found
STATIC_FOLDER = py.path.local(pkresource.filename('static'))

#: Verify ID
_IS_PARALLEL_RE = re.compile('animation', re.IGNORECASE)

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

#: Matches cancelation errors in run_log: KeyboardInterrupt probably only happens in dev
_RUN_LOG_CANCEL_RE = re.compile(r'^KeyboardInterrupt$', flags=re.MULTILINE)

#: Cache of schemas keyed by app name
_SCHEMA_CACHE = {}

#: Status file name
_STATUS_FILE = 'status'

#: created under dir
_TMP_DIR = 'tmp'

#: where users live under db_dir
_USER_ROOT_DIR = 'user'

#: Flask app (init() must be called to set this)
_app = None

#: Use to assert _serial_new result. Not perfect but good enough to avoid common problems
_serial_prev = 0

#: Locking of _serial_prev test/update
_serial_lock = threading.RLock()

#: sirepo.server module, initialized manually to avoid circularity
_server = None


class CopyRedirect(Exception):
    def __init__(self, response):
        super(CopyRedirect, self).__init__()
        self.sr_response = response


def app_version():
    """Force the version to be dynamic if running in dev channel

    Returns:
        str: chronological version
    """
    if pkconfig.channel_in('dev'):
        return datetime.datetime.utcnow().strftime('%Y%m%d.%H%M%S')
    return SCHEMA_COMMON['version']


def celery_queue(data):
    """Which queue to execute simulation in

    Args:
        data (dict): simulation parameters

    Returns:
        str: celery queue name
    """
    from sirepo import celery_tasks
    return celery_tasks.queue_name(is_parallel(data))


def examples(app):
    files = pkio.walk_tree(
        pkresource.filename(_EXAMPLE_DIR_FORMAT.format(app)),
        re.escape(JSON_SUFFIX) + '$',
    )
    #TODO(robnagler) Need to update examples statically before build
    # and assert on build
    return [open_json_file(app, path=str(f)) for f in files]


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


def fixup_old_data(data):
    """Upgrade data to latest schema and updates version.

    Args:
        data (dict): to be updated (destructively)

    Returns:
        dict: upgraded `data`
        bool: True if data changed
    """
    try:
        if 'version' in data and data['version'] == SCHEMA_COMMON['version']:
            return data, False
        data['version'] = SCHEMA_COMMON['version']
        if not 'simulationType' in data:
            if 'sourceIntensityReport' in data['models']:
                data['simulationType'] = 'srw'
            elif 'fieldAnimation' in data['models']:
                data['simulationType'] = 'warp'
            elif 'bunchSource' in data['models']:
                data['simulationType'] = 'elegant'
            else:
                pkdlog('simulationType: not found; data={}', data)
                raise AssertionError('must have simulationType')
        if not 'simulationSerial' in data['models']['simulation']:
            data['models']['simulation']['simulationSerial'] = 0
        sirepo.template.import_module(data['simulationType']).fixup_old_data(data)
        try:
            del data['models']['simulationStatus']
        except KeyError:
            pass
        return data, True
    except Exception as e:
        pkdlog('{}: error: {}', data, pkdexc())
        raise


def get_schema(sim_type):
    if sim_type in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[sim_type]
    schema = read_json(
        STATIC_FOLDER.join('json/{}-schema'.format(sim_type)))
    pkcollections.mapping_merge(schema, SCHEMA_COMMON)
    schema['simulationType'] = sim_type
    _SCHEMA_CACHE[sim_type] = schema
    return schema


def init_by_server(app, server):
    """Avoid circular import by explicit call from `sirepo.server`.

    Args:
        app (Flask): flask instance
        server (module): sirepo.server
    """
    global _app
    _app = app
    global _server
    _server = server


def is_parallel(data):
    """Is this report a parallel (long) simulation?

    Args:
        data (dict): report and models

    Returns:
        bool: True if parallel job
    """
    return bool(_IS_PARALLEL_RE.search(_report_name(data)))


def generate_json(data, pretty=False):
    """Convert data to JSON to be send back to client

    Use only for responses. Use `:func:write_json` to save.
    Args:
        data (dict): what to format
        pretty (bool): pretty print [False]
    Returns:
        str: formatted data
    """
    if pretty:
        return json.dumps(data, indent=4, separators=(',', ': '), sort_keys=True)
    return json.dumps(data)


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
        except ValueError as e:
            pkdlog('{}: error: {}', path, e)
    return res


def json_filename(filename, run_dir=None):
    """Append JSON_SUFFIX if necessary and convert to str

    Args:
        filename (py.path or str): to convert
        run_dir (py.path): which directory to joing
    Returns:
        py.path: filename.json
    """
    filename = str(filename)
    if not filename.endswith(JSON_SUFFIX):
        filename += JSON_SUFFIX
    if run_dir and not os.path.isabs(filename):
        filename = run_dir.join(filename)
    return py.path.local(filename)


def json_load(*args, **kwargs):
    #TODO(robnagler) see https://github.com/radiasoft/sirepo/issues/379
    kwargs['object_pairs_hook'] = dict
    return pkcollections.json_load_any(*args, **kwargs)


def open_json_file(sim_type, path=None, sid=None, fixup=True):
    """Read a db file and return result

    Args:
        sim_type (str): simulation type (app)
        path (py.path.local): where to read the file
        sid (str): simulation id

    Returns:
        dict: data

    Raises:
        CopyRedirect: if the simulation is in another user's
    """
    if not path:
        path = _simulation_data_file(sim_type, sid)
    if not os.path.isfile(str(path)):
        global_sid = None
        if sid:
            #TODO(robnagler) workflow should be in server.py,
            # because only valid in one case, not e.g. for opening examples
            # which are not found.
            user_copy_sid = _find_user_simulation_copy(sim_type, sid)
            if find_global_simulation(sim_type, sid):
                global_sid = sid
        if global_sid:
            raise CopyRedirect({
                'redirect': {
                    'simulationId': global_sid,
                    'userCopySimulationId': user_copy_sid,
                },
            })
        #TODO(robnagler) should be a regular exception or abstraction, not bound to werkzeug
        raise werkzeug.exceptions.NotFound()
    data = None
    try:
        with open(str(path)) as f:
            data = json_load(f)
            # ensure the simulationId matches the path
            if sid:
                data['models']['simulation']['simulationId'] = _sid_from_path(path)
    except Exception as e:
        pkdlog('{}: error: {}', path, pkdexc())
        raise
    return fixup_old_data(data)[0] if fixup else data


def parse_sid(data):
    """Extract id from data

    Args:
        data (dict): models or request

    Returns:
        str: simulationId from data
    """
    try:
        return str(data['simulationId'])
    except KeyError:
        return str(data['models']['simulation']['simulationId'])


def parse_sim_ser(data):
    """Extract simulationStatus from data

    Args:
        data (dict): models or request

    Returns:
        int: simulationSerial
    """
    try:
        return int(data['simulationSerial'])
    except KeyError:
        try:
            return int(data['models']['simulation']['simulationSerial'])
        except KeyError:
            return None


def poll_seconds(data):
    """Client poll period for simulation status

    TODO(robnagler) needs to be encapsulated

    Args:
        data (dict): must container report name
    Returns:
        int: number of seconds to poll
    """
    return 2 if _IS_PARALLEL_RE.search(_report_name(data)) else 1


def prepare_simulation(data):
    """Create and install files, update parameters, and generate command.

    Copies files into the simulation directory (``run_dir``).
    Updates the parameters in ``data`` and save.
    Generate the pkcli command to pass to task runner.

    Args:
        data (dict): report and model parameters
    Returns:
        list, py.path: pkcli command, simulation directory
    """
    run_dir = simulation_run_dir(data, remove_dir=True)
    #TODO(robnagler) create a lock_dir -- what node/pid/thread to use?
    #   probably can only do with celery.
    pkio.mkdir_parent(run_dir)
    write_status('pending', run_dir)
    sim_type = data['simulationType']
    sid = parse_sid(data)
    template = sirepo.template.import_module(data)
    for d in simulation_dir(sim_type, sid), simulation_lib_dir(sim_type):
        for f in glob.glob(str(d.join('*.*'))):
            if os.path.isfile(f):
                py.path.local(f).copy(run_dir)
    template.prepare_aux_files(run_dir, data)
    write_json(run_dir.join(template_common.INPUT_BASE_NAME), data)
    #TODO(robnagler) encapsulate in template
    is_p = is_parallel(data)
    template.write_parameters(
        data,
        get_schema(sim_type),
        run_dir=run_dir,
        is_parallel=is_p,
    )
    cmd = [
        pkinspect.root_package(template),
        pkinspect.module_basename(template),
        'run-background' if is_p else 'run',
        str(run_dir),
    ]
    return cmd, run_dir


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
    with open(str(json_filename(filename))) as f:
        return json_load(f)


def read_result(run_dir):
    """Read result data file from simulation

    Args:
        run_dir (py.path): where to find output

    Returns:
        dict: result or describes error
    """
    fn = json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
    res = None
    err = None
    try:
        res = read_json(fn)
    except Exception as e:
        pkdc('{}: exception={}', fn, e)
        err = pkdexc()
        if pkio.exception_is_not_found(e):
            #TODO(robnagler) change POSIT matches _SUBPROCESS_ERROR_RE
            err = 'ERROR: Terminated unexpectedly'
            # Not found so return run.log as err
            rl = run_dir.join(template_common.RUN_LOG)
            try:
                e = pkio.read_text(rl)
                if _RUN_LOG_CANCEL_RE.search(e):
                    err = None
                elif e:
                    err = e
            except Exception as e:
                if not pkio.exception_is_not_found(e):
                    pkdlog('{}: error reading log: {}', rl, pkdexc())
        else:
            pkdlog('{}: error reading output: {}', fn, err)
    if err:
        return None, err
    if not res:
        res = {}
    if not 'state' in res:
        # Old simulation or other error, just say is canceled so restarts
        res = {'state': 'canceled'}
    return res, None


def read_simulation_json(sim_type, *args, **kwargs):
    """Calls `open_json_file` and fixes up data, possibly saving

    Args:
        sim_type (str): simulation type

    Returns:
        data (dict): simulation data
    """
    data = open_json_file(sim_type, fixup=False, *args, **kwargs)
    new, changed = fixup_old_data(data)
    if changed:
        return save_simulation_json(sim_type, new)
    return data


def read_status(run_dir):
    """Read status from simulation dir

    Args:
        run_dir (py.path): where to read
    """
    try:
        return pkio.read_text(run_dir.join(_STATUS_FILE))
    except IOError:
        return 'error'


def save_new_example(simulation_type, data):
    data['models']['simulation']['isExample'] = True
    return save_new_simulation(simulation_type, data)


def save_new_simulation(simulation_type, data):
    sid = _random_id(simulation_dir(simulation_type), simulation_type)['id']
    data['models']['simulation']['simulationId'] = sid
    return save_simulation_json(simulation_type, data)


def save_simulation_json(simulation_type, data):
    """Prepare data and save to json db

    Args:
        simulation_type (str): srw, warp, ...
        data (dict): what to write (contains simulationId)
    """
    with _serial_lock:
        sid = parse_sid(data)
        try:
            # Never save this
            #TODO(robnagler) have "_private" fields that don't get saved
            del data['simulationStatus']
        except:
            pass
        data = fixup_old_data(data)[0]
        data['models']['simulation']['simulationSerial'] = _serial_new()
        write_json(_simulation_data_file(simulation_type, sid), data)
        return data


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


def validate_serial(req_data):
    """Verify serial in data validates

    Args:
        req_data (dict): request with serial and possibly models

    Returns:
        object: None if all ok, or json response (bad)
    """
    with _serial_lock:
        sim_type = req_data['simulationType']
        sid = parse_sid(req_data)
        req_ser = req_data['models']['simulation']['simulationSerial']
        curr = read_simulation_json(sim_type, sid=sid)
        curr_ser = curr['models']['simulation']['simulationSerial']
        if not req_ser is None:
            if req_ser == curr_ser:
                return None
            status = 'newer' if req_ser > curr_ser else 'older'
            pkdlog(
                '{}: incoming serial {} than stored serial={} sid={}, resetting client',
                req_ser,
                status,
                curr_ser,
                sid,
            )
        return curr


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
    with open(str(json_filename(filename)), 'w') as f:
        f.write(generate_json(data, pretty=True))


def write_result(result, run_dir=None):
    """Write simulation result to standard output.

    Args:
        result (dict): will set state to completed
        run_dir (py.path): Defaults to current dir
    """
    if not run_dir:
        run_dir = py.path.local()
    fn = json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
    if fn.exists():
        # Don't overwrite first written file, because first write is
        # closest to the reason is stopped (e.g. canceled)
        return
    result.setdefault('state', 'completed')
    write_json(fn, result)
    write_status(result['state'], run_dir)


def write_status(status, run_dir):
    """Write status to simulation

    Args:
        status (str): pending, running, completed, canceled
        run_dir (py.path): where to write the file
    """
    pkio.write_text(run_dir.join(_STATUS_FILE), status)


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


def _init():
    global SCHEMA_COMMON
    with open(str(STATIC_FOLDER.join('json/schema-common{}'.format(JSON_SUFFIX)))) as f:
        SCHEMA_COMMON = json_load(f)


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


def _serial_new():
    """Generate a serial number

    Serial numbers are 16 digits (time represented in microseconds
    since epoch) which are always less than Javascript's
    Number.MAX_SAFE_INTEGER (9007199254740991=2*53-1).

    Timestamps are not guaranteed to be sequential. If the
    system clock is adjusted, we'll throw an exception here.
    """
    global _serial_prev
    res = int(time.time() * 1000000)
    with _serial_lock:
        # Good enough assertion. Any collisions will also be detected
        # by parameter hash so order isn't only validation
        assert res > _serial_prev, \
            '{}: serial did not increase: prev={}'.format(res, _serial_prev)
        _serial_prev = res
    return res


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
    try:
        uid = _server.session_user()
    except KeyError:
        uid = _user_dir_create()
    d = _user_dir_name(uid)
    if d.check():
        return d
    # Beaker session might have been deleted (in dev) so "logout" and "login"
    uid = _user_dir_create()
    return _user_dir_name(uid)


def _user_dir_create():
    """Create a user and initialize the directory

    Returns:
        str: New user id
    """
    uid = _random_id(_user_dir_name())['id']
    # Must set before calling simulation_dir
    _server.session_user(uid)
    for simulation_type in SIMULATION_TYPES:
        _create_example_and_lib_files(simulation_type)
    return uid


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

_init()
