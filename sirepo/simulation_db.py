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
from sirepo import cookie
from sirepo import feature_config
from sirepo import util
from sirepo.template import template_common
from sirepo.schema import validate_fields, validate_name, validate_schema
import copy
import datetime
import errno
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

#: The root of the pkresource tree (package_data)
RESOURCE_FOLDER = pkio.py_path(pkresource.filename(''))

#: Where server files and static files are found
STATIC_FOLDER = RESOURCE_FOLDER.join('static')

#: Verify ID
_IS_PARALLEL_RE = re.compile('animation', re.IGNORECASE)

#: How to find examples in resources
_EXAMPLE_DIR = 'examples'

#: Valid characters in ID
_ID_CHARS = numconv.BASE62

#: length of ID
_ID_LEN = 8

#: Relative regexp from ID_Name
_ID_PARTIAL_RE_STR = '[{}]{{{}}}'.format(_ID_CHARS, _ID_LEN)

#: Verify ID
_ID_RE = re.compile('^{}$'.format(_ID_PARTIAL_RE_STR))

#: where users live under db_dir
_LIB_DIR = 'lib'

#: lib relative to sim_dir
_REL_LIB_DIR = '../' + _LIB_DIR

#: Older than any other version
_OLDEST_VERSION = '20140101.000001'

#: Matches cancelation errors in run_log: KeyboardInterrupt probably only happens in dev
_RUN_LOG_CANCEL_RE = re.compile(r'^KeyboardInterrupt$', flags=re.MULTILINE)

#: Cache of schemas keyed by app name
_SCHEMA_CACHE = {}

#: Special field to direct pseudo-subclassing of schema objects
_SCHEMA_SUPERCLASS_FIELD = '_super'

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

#: Locking for global operations like serial, user moves, etc.
_global_lock = threading.RLock()

#: configuration
cfg = None


class CopyRedirect(Exception):
    def __init__(self, resp):
        super(CopyRedirect, self).__init__()
        self.sr_response = resp


def app_version():
    """Force the version to be dynamic if running in dev channel

    Returns:
        str: chronological version
    """
    if pkconfig.channel_in('dev'):
        return _timestamp()
    return SCHEMA_COMMON.version


def assert_id(sid):
    if not _ID_RE.search(sid):
        raise RuntimeError('{}: invalid simulation id'.format(sid))


def celery_queue(data):
    """Which queue to execute simulation in

    Args:
        data (dict): simulation parameters

    Returns:
        str: celery queue name
    """
    from sirepo import celery_tasks
    return celery_tasks.queue_name(is_parallel(data))


def default_data(sim_type):
    """New simulation base data

    Args:
        sim_type (str): simulation type

    Returns:
        dict: simulation data
    """
    return open_json_file(
        sim_type,
        path=template_common.resource_dir(sim_type).join(
            'default-data{}'.format(JSON_SUFFIX),
        ),
    )


def delete_simulation(simulation_type, sid):
    """Deletes the simulation's directory.
    """
    pkio.unchecked_remove(simulation_dir(simulation_type, sid))


def examples(app):
    files = pkio.walk_tree(
        template_common.resource_dir(app).join(_EXAMPLE_DIR),
        re.escape(JSON_SUFFIX) + '$',
    )
    #TODO(robnagler) Need to update examples statically before build
    # and assert on build
    # example data is not fixed-up to avoid performance problems when searching examples by name
    # fixup occurs during save_new_example()
    return [open_json_file(app, path=str(f), fixup=False) for f in files]


def find_global_simulation(sim_type, sid, checked=False):
    paths = pkio.sorted_glob(user_dir_name().join('*', sim_type, sid))
    if len(paths) == 1:
        return str(paths[0])
    if len(paths) == 0:
        if checked:
            util.raise_not_found(
                '{}/{}: global simulation not found',
                sim_type,
                sid,
            )
        return None
    util.raise_not_found(
        '{}: more than one path found for simulation={}/{}',
        paths,
        sim_type,
        sid,
    )


def fixup_old_data(data, force=False):
    """Upgrade data to latest schema and updates version.

    Args:
        data (dict): to be updated (destructively)
        force (bool): force validation

    Returns:
        dict: upgraded `data`
        bool: True if data changed
    """
    try:
        if not force and 'version' in data and data.version == SCHEMA_COMMON.version:
            return data, False
        try:
            data.fixup_old_version = data.version
        except AttributeError:
            data.fixup_old_version = _OLDEST_VERSION
        data.version = SCHEMA_COMMON.version
        if 'simulationType' not in data:
            if 'sourceIntensityReport' in data.models:
                data.simulationType = 'srw'
            elif 'fieldAnimation' in data.models:
                data.simulationType = 'warppba'
            elif 'bunchSource' in data.models:
                data.simulationType = 'elegant'
            else:
                pkdlog('simulationType: not found; data={}', data)
                raise AssertionError('must have simulationType')
        elif data.simulationType == 'warp':
            data.simulationType = 'warppba'
        elif data.simulationType == 'fete':
            data.simulationType = 'warpvnd'
        if 'simulationSerial' not in data.models.simulation:
            data.models.simulation.simulationSerial = 0
        sirepo.template.import_module(data.simulationType).fixup_old_data(data)
        pkcollections.unchecked_del(data.models, 'simulationStatus')
        pkcollections.unchecked_del(data, 'fixup_old_version')
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
    pkcollections.mapping_merge(
        schema,
        {'feature_config': feature_config.for_sim_type(sim_type)},
    )
    schema.simulationType = sim_type
    _SCHEMA_CACHE[sim_type] = schema

    #TODO(mvk): improve merging common and local schema
    _merge_dicts(schema.common.dynamicFiles, schema.dynamicFiles)
    schema.dynamicModules = _files_in_schema(schema.dynamicFiles)

    for item in ['appModes', 'constants', 'cookies', 'enum', 'notifications', 'localRoutes', 'model', 'view']:
        if item not in schema:
            schema[item] = pkcollections.Dict()
        _merge_dicts(schema.common[item], schema[item])
        _merge_subclasses(schema, item)
    validate_schema(schema)
    return schema


def init_by_server(app):
    """Avoid circular import by explicit call from `sirepo.server`.

    Args:
        app (Flask): flask instance
    """
    global _app
    _app = app


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
        return json.dumps(data, indent=4, separators=(',', ': '), sort_keys=True, allow_nan=False)
    return json.dumps(data, allow_nan=False)


def hack_nfs_write_status(status, run_dir):
    """Verify status file exists before writing.

    NFS doesn't propagate files immediately so there
    is a race condition when the celery worker starts.
    This file handles this case.

    Args:
        status (str): pending, running, completed, canceled
        run_dir (py.path): where to write the file
    """
    fn = run_dir.join(_STATUS_FILE)
    for i in range(cfg.nfs_tries):
        if fn.check(file=True):
            break
        time.sleep(cfg.nfs_sleep)
    # Try once always
    pkio.write_text(fn, status)


def iterate_simulation_datafiles(simulation_type, op, search=None):
    res = []
    sim_dir = simulation_dir(simulation_type)
    for path in glob.glob(
        str(sim_dir.join('*', SIMULATION_DATA_FILE)),
    ):
        path = py.path.local(path)
        try:
            data = open_json_file(simulation_type, path, fixup=False)
            data, changed = fixup_old_data(data)
            # save changes to avoid re-applying fixups on each iteration
            if changed:
                #TODO(pjm): validate_name may causes infinite recursion, need better fixup of list prior to iteration
                save_simulation_json(data, do_validate=False)
            if search and not _search_data(data, search):
                continue
            op(res, path, data)
        except ValueError as e:
            pkdlog('{}: error: {}', path, e)
    return res


def job_id(data):
    """A Job is a simulation and report name.

    A jid is words and dashes.

    Args:
        data (dict): extract sid and report
    Returns:
        str: unique name
    """
    return '{}-{}-{}'.format(
        cookie.get_user(),
        data.simulationId,
        data.report,
    )


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
    return pkcollections.json_load_any(*args, **kwargs)


def lib_dir_from_sim_dir(sim_dir):
    """Path to lib dir from simulation dir

    Args:
        sim_dir (py.path): simulation dir

    Return:
        py.path: directory name
    """
    return sim_dir.join(_REL_LIB_DIR)


def move_user_simulations(to_uid):
    """Moves all non-example simulations for the current session into the target user's dir.
    """
    from_uid = cookie.get_user()
    with _global_lock:
        for path in glob.glob(
                str(user_dir_name(from_uid).join('*', '*', SIMULATION_DATA_FILE)),
        ):
            data = read_json(path)
            sim = data['models']['simulation']
            if 'isExample' in sim and sim['isExample']:
                continue
            dir_path = os.path.dirname(path)
            new_dir_path = dir_path.replace(from_uid, to_uid)
            pkdlog('{} -> {}', dir_path, new_dir_path)
            pkio.mkdir_parent(new_dir_path)
            os.rename(dir_path, new_dir_path)


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
        path = sim_data_file(sim_type, sid)
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
        util.raise_not_found(
            '{}/{}: global simulation not found',
            sim_type,
            sid,
        )
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
    return 2 if is_parallel(data) else 1


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
    template_common.copy_lib_files(data, None, run_dir)

    write_json(run_dir.join(template_common.INPUT_BASE_NAME), data)
    #TODO(robnagler) encapsulate in template
    is_p = is_parallel(data)
    template.write_parameters(
        data,
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
    sim = data['models']['simulation']
    res.append({
        'simulationId': _sid_from_path(path),
        'name': sim['name'],
        'folder': sim['folder'],
        'last_modified': datetime.datetime.fromtimestamp(
            os.path.getmtime(str(path))
        ).strftime('%Y-%m-%d %H:%M'),
        'isExample': sim['isExample'] if 'isExample' in sim else False,
        'simulation': sim,
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
    if 'state' not in res:
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
        return save_simulation_json(new)
    return data


def read_status(run_dir):
    """Read status from simulation dir

    Args:
        run_dir (py.path): where to read
    """
    try:
        return pkio.read_text(run_dir.join(_STATUS_FILE))
    except IOError as e:
        if pkio.exception_is_not_found(e):
            # simulation may never have been run
            return 'stopped'
        return 'error'


def report_info(data):
    """Read the run_dir and return cached_data.

    Only a hit if the models between data and cache match exactly. Otherwise,
    return cached data if it's there and valid.

    Args:
        data (dict): parameters identifying run_dir and models or reportParametersHash

    Returns:
        Dict: report parameters and hashes
    """
    # Sets data['reportParametersHash']
    rep = pkcollections.Dict(
        cache_hit=False,
        cached_data=None,
        cached_hash=None,
        job_id=job_id(data),
        model_name=_report_name(data),
        parameters_changed=False,
        run_dir=simulation_run_dir(data),
    )
    rep.input_file = json_filename(template_common.INPUT_BASE_NAME, rep.run_dir)
    rep.job_status = read_status(rep.run_dir)
    rep.req_hash = template_common.report_parameters_hash(data)
    if not rep.run_dir.check():
        return rep
    #TODO(robnagler) Lock
    try:
        cd = read_json(rep.input_file)
        rep.cached_hash = template_common.report_parameters_hash(cd)
        rep.cached_data = cd
        if rep.req_hash == rep.cached_hash:
            rep.cache_hit = True
            return rep
        rep.parameters_changed = True
    except IOError as e:
        pkdlog('{}: ignore IOError: {} errno={}', rep.run_dir, e, e.errno)
    except Exception as e:
        pkdlog('{}: ignore other error: {}', rep.run_dir, e)
        # No idea if cache is valid or not so throw away
    return rep


def save_new_example(data):
    data.models.simulation.isExample = True
    return save_new_simulation(fixup_old_data(data)[0], do_validate=False)


def save_new_simulation(data, do_validate=True):
    d = simulation_dir(data.simulationType)
    sid = _random_id(d, data.simulationType).id
    data.models.simulation.simulationId = sid
    return save_simulation_json(data, do_validate=do_validate)


def save_simulation_json(data, do_validate=True):
    """Prepare data and save to json db

    Args:
        data (dict): what to write (contains simulationId)
    """
    try:
        # Never save this
        #TODO(robnagler) have "_private" fields that don't get saved
        del data['simulationStatus']
    except Exception:
        pass
    data = fixup_old_data(data)[0]
    s = data.models.simulation
    fn = sim_data_file(data.simulationType, s.simulationId)
    with _global_lock:
        need_validate = True
        try:
            # OPTIMIZATION: If folder/name same, avoid reading entire folder
            on_disk = read_json(fn).models.simulation
            need_validate = not (
                on_disk.folder == s.folder and on_disk.name == s.name
            )
        except Exception:
            pass
        if need_validate and do_validate:
            _validate_name(data)
            validate_fields(data, get_schema(data.simulationType))
        s.simulationSerial = _serial_new()
        write_json(fn, data)
    return data


def sim_data_file(sim_type, sim_id):
    """Simulation data file name

    Args:
        sim_type (str): simulation type
        sim_id (str): simulation id

    Returns:
        py.path.local: simulation path
    """
    return simulation_dir(sim_type, sim_id).join(SIMULATION_DATA_FILE)


def simulation_dir(simulation_type, sid=None):
    """Generates simulation directory from sid and simulation_type

    Args:
        simulation_type (str): srw, warppba, ...
        sid (str): simulation id (optional)
    """
    d = _user_dir().join(sirepo.template.assert_sim_type(simulation_type))
    if not sid:
        return d
    assert_id(sid)
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
    d = simulation_dir(data['simulationType'], parse_sid(data)).join(_report_dir(data))
    if remove_dir:
        pkio.unchecked_remove(d)
    return d


def static_libs():
    return _files_in_schema(SCHEMA_COMMON.common.staticFiles)


def static_file_path(file_dir, file_name):
    """Absolute path to a static file
    For requesting static files (hence a public interface)

    Args:
        file_dir (str): directory in package_data/static
        file_name (str): name of the file

    Returns:
        py.path: absolute path of the file
    """
    return STATIC_FOLDER.join(file_dir).join(file_name)


def tmp_dir():
    """Generates new, temporary directory

    Returns:
        py.path: directory to use for temporary work
    """
    d = _random_id(_user_dir().join(_TMP_DIR))['path']
    pkio.unchecked_remove(d)
    return pkio.mkdir_parent(d)


def uid_from_dir_name(dir_name):
    """Extra user id from user_dir_name

    Args:
        dir_name (py.path): must be top level user dir or sim_dir

    Return:
        str: user id
    """
    r = re.compile(
        r'^{}/({})(?:$|/)'.format(
            re.escape(str(user_dir_name())),
            _ID_PARTIAL_RE_STR,
        ),
    )
    m = r.search(str(dir_name))
    assert m, \
        '{}: invalid user or sim dir; did not match re={}'.format(
            dir_name,
            r.pattern,
        )
    return m.group(1)


def user_dir_name(uid=None):
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


def validate_serial(req_data):
    """Verify serial in data validates

    Args:
        req_data (dict): request with serial and possibly models

    Returns:
        object: None if all ok, or json response (bad)
    """
    with _global_lock:
        sim_type = sirepo.template.assert_sim_type(req_data['simulationType'])
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
    input_file = json_filename(template_common.INPUT_BASE_NAME, run_dir)
    if input_file.exists():
        template = sirepo.template.import_module(read_json(input_file))
        if hasattr(template, 'clean_run_dir'):
            template.clean_run_dir(run_dir)


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
        save_new_example(s)
    d = simulation_lib_dir(simulation_type)
    pkio.mkdir_parent(d)
    template = sirepo.template.import_module(simulation_type)
    if hasattr(template, 'resource_files'):
        for f in template.resource_files():
            #TODO(pjm): symlink has problems in containers
            # d.join(f.basename).mksymlinkto(f)
            f.copy(d)


def _files_in_schema(schema):
    """Relative paths of local and external files of the given load and file type listed in the schema
    The order matters for javascript files

    Args:
        schema (pkcollections.Dict): schema (or portion thereof) to inspect

    Returns:
        str: combined list of local and external file paths, mapped by type
    """
    paths = pkcollections.Dict()
    for source, path in (('externalLibs', 'ext'), ('sirepoLibs', '')):
        for file_type in schema[source]:
            if file_type not in paths:
                paths[file_type] = []
            paths[file_type].extend(map(lambda file_name:
                    _pkg_relative_path_static(file_type + '/' + path, file_name),
                    schema[source][file_type]))

    return paths


def _find_user_simulation_copy(simulation_type, sid):
    rows = iterate_simulation_datafiles(simulation_type, process_simulation_list, {
        'simulation.outOfSessionSimulationId': sid,
    })
    if len(rows):
        return rows[0]['simulationId']
    return None


def _init():
    global SCHEMA_COMMON, cfg
    fn = STATIC_FOLDER.join('json/schema-common{}'.format(JSON_SUFFIX))
    with open(str(fn)) as f:
        SCHEMA_COMMON = json_load(f)
    # In development, you can touch schema-common to get a new version
    SCHEMA_COMMON.version = _timestamp(fn.mtime()) if pkconfig.channel_in('dev') else sirepo.__version__
    cfg = pkconfig.init(
        nfs_tries=(10, int, 'How many times to poll in hack_nfs_write_status'),
        nfs_sleep=(0.5, float, 'Seconds sleep per hack_nfs_write_status poll'),
    )


def _merge_dicts(base, derived, depth=-1):
    """Copy the items in the base dictionary into the derived dictionary, to the specified depth

    Args:
        base (dict): source
        derived (dict): receiver
        depth (int): how deep to recurse:
            >= 0:  <depth> levels
            < 0:   all the way
    """
    if depth == 0:
        return
    for key in base:
        # Items with the same name are not replaced
        if key not in derived:
            derived[key] = base[key]
        else:
            try:
                derived[key].extend(x for x in base[key] if x not in derived[key])
            except AttributeError:
                # The value was not an array
                pass
        try:
            _merge_dicts(base[key], derived[key], depth - 1 if depth > 0 else depth)
        except TypeError:
            # The value in question is not itself a dict, move on
            pass


def _merge_subclasses(schema, item):
    for m in schema[item]:
        has_super = False
        s = schema[item][m]
        try:
            has_super = _SCHEMA_SUPERCLASS_FIELD in s
        except TypeError:
            # Ignore non-indexable types
            continue
        if has_super:
            i = s[_SCHEMA_SUPERCLASS_FIELD]
            s_item = i[1]
            s_class = i[2]
            assert s_item in schema, util.err(s_item, 'No such field in schema')
            assert s_item == item, util.err(s_item, 'Superclass must be in same section of schema {}', item)
            assert s_class in schema[s_item], util.err(s_class, 'No such superclass')
            _merge_dicts(schema[item][s_class], s)


def _pkg_relative_path_static(file_dir, file_name):
    """Path to a file under /static, relative to the package_data directory

    Args:
        file_dir (str): sub-directory of package_data/static
        file_name (str): name of the file

    Returns:
        str: full relative path of the file
    """
    return '/' + RESOURCE_FOLDER.bestrelpath(static_file_path(file_dir, file_name))


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
            return pkcollections.Dict(id=i, path=d)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            raise
    raise RuntimeError('{}: failed to create unique directory'.format(parent_dir))


def _report_dir(data):
    """Return the report execution directory name. Allows multiple models to get data from same simulation run.
    """
    template = sirepo.template.import_module(data)
    if hasattr(template, 'simulation_dir_name'):
        return template.simulation_dir_name(_report_name(data))
    return _report_name(data)


def _report_name(data):
    """Extract report name from data
    Args:
        data (dict): passed in params
    Returns:
        str: name of the report requested in the data
    """
    return data['report']


def _search_data(data, search):
    for field, expect in search.items():
        path = field.split('.')
        if len(path) == 1:
            #TODO(robnagler) is this a bug? Why would you supply a search path
            # value that didn't want to be searched.
            continue
        path.insert(0, 'models')
        v = data
        for key in path:
            if key in v:
                v = v[key]
        if v != expect:
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
    with _global_lock:
        # Good enough assertion. Any collisions will also be detected
        # by parameter hash so order isn't only validation
        assert res > _serial_prev, \
            '{}: serial did not increase: prev={}'.format(res, _serial_prev)
        _serial_prev = res
    return res


def _sid_from_path(path):
    sid = os.path.split(os.path.split(str(path))[0])[1]
    assert_id(sid)
    return sid


def _timestamp(time=None):
    if not time:
        time = datetime.datetime.utcnow()
    elif not isinstance(time, datetime.datetime):
        time = datetime.datetime.fromtimestamp(time)
    return time.strftime('%Y%m%d.%H%M%S')


def _user_dir():
    """User for the session

    Returns:
        str: unique id for user from flask session
    """
    uid = cookie.get_user(checked=False)
    if not uid:
        uid = _user_dir_create()
    d = user_dir_name(uid)
    if d.check():
        return d
    # flask session might have been deleted (in dev) so "logout" and "login"
    uid = _user_dir_create()
    return user_dir_name(uid)


def _user_dir_create():
    """Create a user and initialize the directory

    Returns:
        str: New user id
    """
    uid = _random_id(user_dir_name())['id']
    # Must set before calling simulation_dir
    cookie.set_user(uid)
    for simulation_type in feature_config.cfg.sim_types:
        _create_example_and_lib_files(simulation_type)
    return uid


def _validate_name(data):
    """Validate and if necessary uniquify name

    Args:
        data (dict): what to validate
    """
    s = data.models.simulation
    sim_type = data.simulationType
    sim_id = s.simulationId
    n = s.name
    f = s.folder
    starts_with = pkcollections.Dict()
    for d in iterate_simulation_datafiles(
        sim_type,
        lambda res, _, d: res.append(d),
        {'simulation.folder': f},
    ):
        n2 = d.models.simulation.name
        if n2.startswith(n) and d.models.simulation.simulationId != sim_id:
            starts_with[n2] = d.models.simulation.simulationId
    i = 2
    max = SCHEMA_COMMON.common.constants.maxSimCopies
    n2 = data.models.simulation.name
    while n2 in starts_with:
        n2 = '{} {}'.format(data.models.simulation.name, i)
        i += 1
    assert i - 1 <= max, util.err(n, 'Too many copies: {} > {}', i - 1, max)
    data.models.simulation.name = n2


_init()
