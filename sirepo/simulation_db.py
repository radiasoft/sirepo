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
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import feature_config
from sirepo import srschema
from sirepo import util
from sirepo.template import template_common
import contextlib
import copy
import datetime
import errno
import glob
import numconv
import os
import os.path
import random
import re
import sirepo.auth
import sirepo.const
import sirepo.job
import sirepo.resource
import sirepo.srdb
import sirepo.template
import time

#: Names to display to use for jobRunMode

JOB_RUN_MODE_MAP = None

#: Schema common values, e.g. version
SCHEMA_COMMON = None

#: Simulation file name is globally unique to avoid collisions with simulation output
SIMULATION_DATA_FILE = 'sirepo-data' + sirepo.const.JSON_SUFFIX

#: where users live under db_dir
USER_ROOT_DIR = 'user'


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

#: Absolute path of rsmanifest file
_RSMANIFEST_PATH = pkio.py_path('/rsmanifest' + sirepo.const.JSON_SUFFIX)

#: Cache of schemas keyed by app name
_SCHEMA_CACHE = PKDict()

#: Special field to direct pseudo-subclassing of schema objects
_SCHEMA_SUPERCLASS_FIELD = '_super'

#: created under dir
_TMP_DIR = 'tmp'

#: Use to assert _serial_new result. Not perfect but good enough to avoid common problems
_serial_prev = 0

#: configuration
cfg = None

#: version for development
_dev_version = None


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


def assert_sid(sid):
    assert _ID_RE.search(sid), 'invalid sid='.format(sid)
    return sid


def default_data(sim_type):
    """New simulation base data

    Args:
        sim_type (str): simulation type

    Returns:
        dict: simulation data
    """
    import sirepo.sim_data

    return open_json_file(
        sim_type,
        path=sirepo.sim_data.get_class(sim_type).resource_path(f'default-data{sirepo.const.JSON_SUFFIX}')
    )


def delete_simulation(simulation_type, sid):
    """Deletes the simulation's directory.
    """
    pkio.unchecked_remove(simulation_dir(simulation_type, sid))


def delete_user(uid):
    """Deletes a user's directory."""
    assert uid is not None
    pkio.unchecked_remove(user_path(uid=uid))

def examples(app):
    #TODO(robnagler) Need to update examples statically before build
    # and assert on build
    # example data is not fixed-up to avoid performance problems when searching examples by name
    # fixup occurs during save_new_example()
    return [
        open_json_file(app, path=str(f), fixup=False) \
            for f in sirepo.sim_data.get_class(app).example_paths()
    ]


def find_global_simulation(sim_type, sid, checked=False, uid=None):
    paths = pkio.sorted_glob(user_path(uid=uid).join('*', sim_type, sid))
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
        pkdc("{} force= {}, version= {} (SCHEMA_COMMON.version={})",
             data.get('models', {}).get('simulation', {}).get('simulationId', None), force,
             data.get('version', None), SCHEMA_COMMON.version)
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
        if 'lastModified' not in data.models.simulation:
            update_last_modified(data)
        import sirepo.sim_data
        sirepo.sim_data.get_class(data.simulationType).fixup_old_data(data)
        data.pkdel('fixup_old_version')
        return data, True
    except Exception as e:
        pkdlog('exception={} data={} stack={}', e, data, pkdexc())
        raise


def get_schema(sim_type):
    """Get the schema for `sim_type`

    If sim_type is None, it will return the schema for the first sim_type
    in `feature_config.cfg().sim_types`

    Args:
        sim_type (str): must be valid
    Returns:
        dict: Shared schema

    """
    t = sirepo.template.assert_sim_type(sim_type) if sim_type is not None \
        else list(feature_config.cfg().sim_types)[0]
    return _SCHEMA_CACHE[t]


def generate_json(data, pretty=False):
    """Convert data to JSON to be send back to client

    Use only for responses. Use `:func:write_json` to save.
    Args:
        data (dict): what to format
        pretty (bool): pretty print [False]
    Returns:
        str: formatted data
    """
    return util.json_dump(data, pretty=pretty)


def iterate_simulation_datafiles(simulation_type, op, search=None, uid=None):
    res = []
    sim_dir = simulation_dir(simulation_type, uid=uid)
    for path in glob.glob(
        str(sim_dir.join('*', SIMULATION_DATA_FILE)),
    ):
        path = pkio.py_path(path=path)
        try:
            data = open_json_file(simulation_type, path, fixup=False, uid=uid)
            data, changed = fixup_old_data(data)
            # save changes to avoid re-applying fixups on each iteration
            if changed:
                #TODO(pjm): validate_name may causes infinite recursion, need better fixup of list prior to iteration
                save_simulation_json(data, do_validate=False, uid=uid)
            if search and not _search_data(data, search):
                continue
            op(res, path, data)
        except ValueError as e:
            pkdlog('{}: error: {}', path, e)
    return res


def json_filename(filename, run_dir=None):
    """Append sirepo.const.JSON_SUFFIX if necessary and convert to str

    Args:
        filename (py.path or str): to convert
        run_dir (py.path): which directory to join
    Returns:
        py.path: filename.json
    """
    filename = str(filename)
    if not filename.endswith(sirepo.const.JSON_SUFFIX):
        filename += sirepo.const.JSON_SUFFIX
    if run_dir and not os.path.isabs(filename):
        filename = run_dir.join(filename)
    return pkio.py_path(path=filename)


def json_load(*args, **kwargs):
    return pkcollections.json_load_any(*args, **kwargs)


def lib_dir_from_sim_dir(sim_dir):
    """Path to lib dir from simulation dir

    Args:
        sim_dir (py.path): simulation dir or below

    Return:
        py.path: directory name
    """
    return _sim_from_path(sim_dir)[1].join(_REL_LIB_DIR)


def logged_in_user_path():
    """Get logged in user's simulation directory

    Returns:
        py.path: user is valid and so is directory
    """
    return user_path(
        sirepo.auth.logged_in_user(check_path=False),
        check=True,
    )


def move_user_simulations(from_uid, to_uid):
    """Moves all non-example simulations `from_uid` into `to_uid`.

    Only moves non-example simulations. Doesn't delete the from_uid.

    Args:
        from_uid (str): source user
        to_uid (str): dest user

    """
    with util.THREAD_LOCK:
        for path in glob.glob(
                str(user_path(from_uid).join('*', '*', SIMULATION_DATA_FILE)),
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


def open_json_file(sim_type, path=None, sid=None, fixup=True, uid=None):
    """Read a db file and return result

    Args:
        sim_type (str): simulation type (app)
        path (py.path.local): where to read the file
        sid (str): simulation id
        uid (uid): user id

    Returns:
        dict: data

    Raises:
        CopyRedirect: if the simulation is in another user's
    """
    if not path:
        path = sim_data_file(sim_type, sid, uid=uid)
    if not os.path.isfile(str(path)):
        global_sid = None
        if sid:
            #TODO(robnagler) workflow should be in server.py,
            # because only valid in one case, not e.g. for opening examples
            # which are not found.
            user_copy_sid = _find_user_simulation_copy(sim_type, sid, uid=uid)
            if find_global_simulation(sim_type, sid, uid=uid):
                global_sid = sid
        if global_sid:
            raise CopyRedirect(PKDict(
                redirect=PKDict(
                    simulationId=global_sid,
                    userCopySimulationId=user_copy_sid,
                ),
            ))
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
                data.models.simulation.simulationId = _sim_from_path(path)[0]
    except Exception as e:
        pkdlog('{}: error: {}', path, pkdexc())
        raise
    return fixup_old_data(data)[0] if fixup else data


def parse_sim_ser(data):
    """Extract simulationSerial from data

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


def prepare_simulation(data, run_dir):
    """Create and install files, update parameters, and generate command.

    Copies files into the simulation directory (``run_dir``)
    Updates the parameters in ``data`` and save.
    Generate the pkcli command.

    Args:
        data (dict): report and model parameters
        run_dir (py.path.local): dir simulation will be run in
    Returns:
        list, py.path: pkcli command, simulation directory
    """
    import sirepo.sim_data
    sim_type = data.simulationType
    template = sirepo.template.import_module(data)
    s = sirepo.sim_data.get_class(sim_type)
    s.support_files_to_run_dir(data, run_dir)
    update_rsmanifest(data)
    write_json(run_dir.join(template_common.INPUT_BASE_NAME), data)
    #TODO(robnagler) encapsulate in template
    is_p = s.is_parallel(data)
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
    res.append(PKDict(
        simulationId=_sim_from_path(path)[0],
        name=sim['name'],
        folder=sim['folder'],
        isExample=sim['isExample'] if 'isExample' in sim else False,
        simulation=sim,
    ))


def read_json(filename):
    """Read data from json file

    Args:
        filename (py.path or str): will append sirepo.const.JSON_SUFFIX if necessary

    Returns:
        object: json converted to python
    """
    return json_load(json_filename(filename))


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


def save_new_example(data, uid=None):
    data.models.simulation.isExample = True
    return save_new_simulation(fixup_old_data(data)[0], do_validate=False, uid=uid)


def save_new_simulation(data, do_validate=True, uid=None):
    d = simulation_dir(data.simulationType, uid=uid)
    sid = _random_id(d, data.simulationType, uid=uid).id
    data.models.simulation.simulationId = sid
    return save_simulation_json(data, do_validate=do_validate, uid=uid)


def save_simulation_json(data, do_validate=True, uid=None):
    """Prepare data and save to json db

    Args:
        data (dict): what to write (contains simulationId)
        uid (str): user id
    """
    data = fixup_old_data(data)[0]
    # old implementation value
    data.pkdel('computeJobHash')
    s = data.models.simulation
    sim_type = data.simulationType
    fn = sim_data_file(sim_type, s.simulationId, uid=uid)
    with util.THREAD_LOCK:
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
            srschema.validate_name(
                data,
                iterate_simulation_datafiles(
                    sim_type,
                    lambda res, _, d: res.append(d),
                    PKDict({'simulation.folder': s.folder}),
                    uid=uid,
                ),
                SCHEMA_COMMON.common.constants.maxSimCopies
            )
            srschema.validate_fields(data, get_schema(data.simulationType))
        s.simulationSerial = _serial_new()
        # Do not write simulationStatus or computeJobCacheKey
        d = copy.deepcopy(data)
        pkcollections.unchecked_del(d.models, 'simulationStatus', 'computeJobCacheKey')
        write_json(fn, d)
    return data


def sid_from_compute_file(path):
    """Get sid from path to report file

    Args:
        path (py.path): must be an existing report file

    Returns:
        str: simulation id
    """
    assert path.check(file=1)
    return _sim_from_path(path)[0]


def sim_data_file(sim_type, sim_id, uid=None):
    """Simulation data file name

    Args:
        sim_type (str): simulation type
        sim_id (str): simulation id
        uid (str): user id

    Returns:
        py.path.local: simulation path
    """
    return simulation_dir(sim_type, sim_id, uid=uid).join(SIMULATION_DATA_FILE)


def simulation_dir(simulation_type, sid=None, uid=None):
    """Generates simulation directory from sid and simulation_type

    Args:
        simulation_type (str): srw, warppba, ...
        sid (str): simulation id (optional)
        uid (str): user id [logged_in_user]
    """
    p = user_path(uid) if uid else logged_in_user_path()
    d = p.join(sirepo.template.assert_sim_type(simulation_type))
    if not sid:
        return d
    return d.join(assert_sid(sid))


def simulation_file_uri(simulation_type, sid, basename):
    return '/'.join([
        sirepo.template.assert_sim_type(simulation_type),
        assert_sid(sid),
        basename,
    ])


def simulation_lib_dir(simulation_type, uid=None):
    """String name for user library dir

    Args:
        simulation_type: which app is this for
        uid (str): user id [logged_in_user]

    Return:
        py.path: directory name
    """
    return simulation_dir(simulation_type, uid=uid).join(_LIB_DIR)


def simulation_run_dir(req_or_data, remove_dir=False):
    """Where to run the simulation

    Args:
        req_or_data (dict): may be simulation data or a request
        remove_dir (bool): remove the directory [False]

    Returns:
        py.path: directory to run
    """
    import sirepo.sim_data
    t = req_or_data.simulationType
    s = sirepo.sim_data.get_class(t)
    d = simulation_dir(
        t,
        s.parse_sid(req_or_data),
    ).join(s.compute_model(req_or_data))
    if remove_dir:
        pkio.unchecked_remove(d)
    return d

def static_libs():
    return _files_in_schema(SCHEMA_COMMON.common.staticFiles)


@contextlib.contextmanager
def tmp_dir(chdir=False, uid=None):
    """Generates new, temporary directory

    Args:
        chdir (bool): if true, will save_chdir
        uid (str): user id
    Returns:
        py.path: directory to use for temporary work
    """
    d = None
    try:
        p = user_path(uid, check=True) if uid else logged_in_user_path()
        d = cfg.tmp_dir or _random_id(p.join(_TMP_DIR), uid=uid)['path']
        pkio.unchecked_remove(d)
        pkio.mkdir_parent(d)
        if chdir:
            with pkio.save_chdir(d):
                yield d
        else:
            yield d
    finally:
        if d:
            pkio.unchecked_remove(d)


def uid_from_dir_name(dir_name):
    """Extract user id from user_path

    Args:
        dir_name (py.path): must be top level user dir or sim_dir

    Return:
        str: user id
    """
    r = re.compile(
        r'^{}/({})(?:$|/)'.format(
            re.escape(str(user_path())),
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


def update_last_modified(data):
    """Set simulation.lastModified to the current time in javascript format.
    """
    data.models.simulation.lastModified = int(datetime.datetime.utcnow().timestamp() * 1000)
    return data


def update_rsmanifest(data):
    try:
        data.rsmanifest = read_json(_RSMANIFEST_PATH)
    except Exception as e:
        if pkio.exception_is_not_found(e):
            return
        raise


def user_create():
    """Create a user and initialize the directory

    Returns:
        str: New user id
    """
    uid = _random_id(user_path())['id']
    for simulation_type in feature_config.cfg().sim_types:
        _create_lib_and_examples(
            simulation_type,
            uid=uid,
        )
    return uid


def user_path(uid=None, check=False):
    """Path for uid or root of all users

    Args:
        uid (str): properly formated user name [None]
        check (bool): assert directory exists (only if uid) [False]
    Return:
        py.path: root user's
    """
    d = sirepo.srdb.root().join(USER_ROOT_DIR)
    if not uid:
        return d
    d = d.join(uid)
    if check and not d.check():
        sirepo.auth.user_dir_not_found(d, uid)
    return d


def validate_sim_db_file_path(path, uid):
    import sirepo.job

    assert re.search(
        re.compile(
            r'^{}/{}/{}/({})/{}/[a-zA-Z0-9-_\.]{{1,128}}$'.format(
                sirepo.job.SIM_DB_FILE_URI,
                USER_ROOT_DIR,
                uid,
                '|'.join(feature_config.cfg().sim_types),
                _ID_PARTIAL_RE_STR,
            )
        ),
        path,
    ), f'invalid path={path} or uid={uid}'


def validate_serial(req_data):
    """Verify serial in data validates

    Args:
        req_data (dict): request with serial and possibly models
    """
    if req_data.get('version') != SCHEMA_COMMON.version:
        raise util.SRException('serverUpgraded', None)
    with util.THREAD_LOCK:
        sim_type = sirepo.template.assert_sim_type(req_data.simulationType)
        sid = req_data.models.simulation.simulationId
        req_ser = req_data.models.simulation.simulationSerial
        curr = read_simulation_json(sim_type, sid=sid)
        curr_ser = curr.models.simulation.simulationSerial
        if not req_ser is None:
            if req_ser == curr_ser:
                return
            status = 'newer' if req_ser > curr_ser else 'older'
        raise util.Error(
            PKDict(
                sim_type=sim_type,
                error='invalidSerial',
                simulationData=req_data,
            ),
            '{}: incoming serial {} than stored serial={} sid={}, resetting client',
            req_ser,
            status,
            curr_ser,
            sid,
        )


def verify_app_directory(simulation_type, uid=None):
    """Ensure the app directory is present. If not, create it and add example files.

    Args:
        uid (str): user id
    """
    d = simulation_dir(simulation_type, uid=uid)
    if d.exists():
        return
    _create_lib_and_examples(simulation_type, uid=uid)


def write_json(filename, data):
    """Write data as json to filename

    pretty is true.

    Args:
        filename (py.path or str): will append sirepo.const.JSON_SUFFIX if necessary
    """
    util.json_dump(data, path=json_filename(filename), pretty=True)


def _create_lib_and_examples(simulation_type, uid=None):
    import sirepo.sim_data

    pkio.mkdir_parent(simulation_lib_dir(simulation_type, uid=uid))
    for s in examples(simulation_type):
        save_new_example(s, uid=uid)


def _files_in_schema(schema):
    """Relative paths of local and external files of the given load and file type listed in the schema
    The order matters for javascript files

    Args:
        schema (PKDict): schema (or portion thereof) to inspect

    Returns:
        str: combined list of local and external file paths, mapped by type
    """
    paths = PKDict(css=[], js=[])
    for source, path in (('externalLibs', 'ext'), ('sirepoLibs', '')):
        for file_type, files in schema[source].items():
            for f in files:
                paths[file_type].append(
                    sirepo.resource.static_url(file_type, path, f),
                )
    return paths


def _find_user_simulation_copy(simulation_type, sid, uid=None):
    rows = iterate_simulation_datafiles(
        simulation_type,
        process_simulation_list,
        PKDict({'simulation.outOfSessionSimulationId': sid}),
        uid=uid,
    )
    if len(rows):
        return rows[0]['simulationId']
    return None


def _init():
    import sirepo.mpi

    global cfg, JOB_RUN_MODE_MAP
    cfg = pkconfig.init(
        nfs_tries=(10, int, 'How many times to poll in hack_nfs_write_status'),
        nfs_sleep=(0.5, float, 'Seconds sleep per hack_nfs_write_status poll'),
        sbatch_display=(None, str, 'how to display sbatch cluster to user'),
        tmp_dir=(None, pkio.py_path, 'Used by utilities (not regular config)'),
    )
    _init_schemas()
    JOB_RUN_MODE_MAP = PKDict(
        sequential='Serial',
        parallel='{} cores (SMP)'.format(sirepo.mpi.cfg.cores),
    )
    if cfg.sbatch_display:
        JOB_RUN_MODE_MAP.sbatch = cfg.sbatch_display


def _init_schemas():
    global SCHEMA_COMMON
    SCHEMA_COMMON = json_load(sirepo.resource.static('json', f'schema-common{sirepo.const.JSON_SUFFIX}'))
    a = SCHEMA_COMMON.appInfo
    for t in sirepo.feature_config.cfg().sim_types:
        s = read_json(sirepo.resource.static('json', f'{t}-schema.json'))
        _merge_dicts(s.get('appInfo', PKDict()), a)
        s.update(SCHEMA_COMMON)
        s.feature_config = feature_config.for_sim_type(t)
        s.feature_config.update(feature_config.global_sim_cfg())
        s.simulationType = t

        #TODO(mvk): improve merging common and local schema
        _merge_dicts(s.common.dynamicFiles, s.dynamicFiles)
        s.dynamicModules = _files_in_schema(s.dynamicFiles)
        for i in [
                'appDefaults',
                'appModes',
                'constants',
                'cookies',
                'enum',
                'notifications',
                'localRoutes',
                'model',
                'strings',
                'view',
        ]:
            if i not in s:
                s[i] = PKDict()
            _merge_dicts(s.common[i], s[i])
            _merge_subclasses(s, i)
        srschema.validate(s)
        _SCHEMA_CACHE[t] = s
    SCHEMA_COMMON.appInfo = a
    for s in _SCHEMA_CACHE.values():
        s.appInfo = a
    # In development, any schema update creates a new version
    if pkconfig.channel_in('dev'):
        SCHEMA_COMMON.version = max([
            _timestamp(fn.mtime()) \
            for fn in sirepo.resource.static_paths_for_type('json')
        ])
    else:
        SCHEMA_COMMON.version = sirepo.__version__


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
        item_schema = schema[item]
        model = item_schema[m]
        subclasses = []
        _unnest_subclasses(schema, item, m, subclasses)
        for s in subclasses:
            _merge_dicts(item_schema[s], model)


def _unnest_subclasses(schema, item, key, subclass_keys):
    item_schema = schema[item]
    try:
        if _SCHEMA_SUPERCLASS_FIELD not in item_schema[key]:
            return
    except TypeError:
        # Ignore non-indexable types
        return
    sub_model = item_schema[key]
    sub_item = sub_model[_SCHEMA_SUPERCLASS_FIELD][1]
    sub_key = sub_model[_SCHEMA_SUPERCLASS_FIELD][2]
    assert sub_item in schema, util.err(sub_item, 'No such field in schema')
    assert sub_item == item, util.err(
        sub_item,
        'Superclass must be in same section of schema {}',
        item
    )
    assert sub_key in item_schema, util.err(sub_key, 'No such superclass')
    subclass_keys.append(sub_key)
    _unnest_subclasses(schema, item, sub_key, subclass_keys)


def _random_id(parent_dir, simulation_type=None, uid=None):
    """Create a random id in parent_dir

    Args:
        parent_dir (py.path): where id should be unique
        uid (str): user id
    Returns:
        dict: id (str) and path (py.path)
    """
    pkio.mkdir_parent(parent_dir)
    r = random.SystemRandom()
    # Generate cryptographically secure random string
    for _ in range(5):
        i = ''.join(r.choice(_ID_CHARS) for x in range(_ID_LEN))
        if simulation_type:
            if find_global_simulation(simulation_type, i, uid=uid):
                continue
        d = parent_dir.join(i)
        try:
            os.mkdir(str(d))
            return PKDict(id=i, path=d)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            raise
    raise RuntimeError('{}: failed to create unique directory'.format(parent_dir))


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
    with util.THREAD_LOCK:
        # Good enough assertion. Any collisions will also be detected
        # by parameter hash so order isn't only validation
        assert res > _serial_prev, \
            '{}: serial did not increase: prev={}'.format(res, _serial_prev)
        _serial_prev = res
    return res


def _sim_from_path(path):
    prev = None
    p = path
    # SECURITY: go up three levels at most (<type>/<id>/<report>/<output>)
    for _ in range(3):
        if p == prev:
            break
        i = p.basename
        if _ID_RE.search(i):
            return i, p
        prev = p
        p = p.dirpath()
    raise AssertionError('path={} is not valid simulation'.format(path))


def _timestamp(time=None):
    if not time:
        time = datetime.datetime.utcnow()
    elif not isinstance(time, datetime.datetime):
        time = datetime.datetime.fromtimestamp(time)
    return time.strftime('%Y%m%d.%H%M%S')


_init()
