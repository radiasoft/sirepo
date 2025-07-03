"""Simulation database

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import feature_config
from sirepo import srschema
from sirepo import srtime
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
import sirepo.const
import sirepo.file_lock
import sirepo.job
import sirepo.mpi
import sirepo.resource
import sirepo.srdb
import sirepo.template
import time

#: Names to display to use for jobRunMode

JOB_RUN_MODE_MAP = None

#: Schema common values, e.g. version
SCHEMA_COMMON = None

#: DEPRECATED use sirepo.const.SIM_DATA_BASENAME
SIMULATION_DATA_FILE = sirepo.const.SIM_DATA_BASENAME

#: where users live under db_dir
USER_ROOT_DIR = "user"

#: Valid characters in ID
_ID_CHARS = numconv.BASE62

#: length of ID
_ID_LEN = 8

#: Relative regexp from ID_Name
_ID_PARTIAL_RE_STR = "[{}]{{{}}}".format(_ID_CHARS, _ID_LEN)

#: Verify ID
_ID_RE = re.compile("^{}$".format(_ID_PARTIAL_RE_STR))

#: where users live under db_dir
_LIB_DIR = sirepo.const.LIB_DIR

#: lib relative to sim_dir
_REL_LIB_DIR = "../" + _LIB_DIR

#: Older than any other version
_OLDEST_VERSION = "20140101.000001"

#: Cache of schemas keyed by app name
_SCHEMA_CACHE = PKDict()

#: Special field to direct pseudo-subclassing of schema objects
_SCHEMA_SUPERCLASS_FIELD = "_super"

#: configuration
_cfg = None

#: begin alnum/under, end with alnum, 128 chars max
_SIM_DB_BASENAME_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_\.-]{1,126}[a-zA-Z0-9]$")

#: For re-entrant `user_lock`
_USER_LOCK = PKDict(paths=set())


_SERIAL_INITIALIZE = -1


def app_version():
    """Force the version to be dynamic if running in dev channel

    Returns:
        str: chronological version
    """
    if _cfg.dev_version:
        return _now_as_version()
    return SCHEMA_COMMON.version


def assert_sid(sid):
    if _ID_RE.search(sid) or sirepo.job.QUASI_SID_RE.search(sid):
        return sid
    raise AssertionError(f"invalid sid={sid}")


def assert_sim_db_basename(basename):
    assert _SIM_DB_BASENAME_RE.search(basename), f"basename={basename} is invalid"
    return basename


def assert_uid(uid):
    if _ID_RE.search(uid):
        return uid
    raise AssertionError(f"invalid uid={uid}")


def cfg():
    return _cfg


def default_data(sim_type):
    """New simulation base data

    Args:
        sim_type (str): simulation type

    Returns:
        dict: simulation data
    """
    from sirepo import sim_data

    return open_json_file(
        sim_type,
        path=sim_data.get_class(sim_type).resource_path(
            f"default-data{sirepo.const.JSON_SUFFIX}",
        ),
    )


def delete_simulation(simulation_type, sid, qcall=None):
    """Deletes the simulation's directory."""
    pkio.unchecked_remove(simulation_dir(simulation_type, sid, qcall=qcall))


def delete_user(qcall):
    """Deletes a user's directory."""
    pkio.unchecked_remove(user_path(qcall=qcall))


def examples(app):
    # TODO(robnagler) Need to update examples statically before build
    # and assert on build
    # example data is not fixed-up to avoid performance problems when searching examples by name
    # fixup occurs during save_new_example()
    from sirepo import sim_data

    return [
        open_json_file(app, path=f, fixup=False)
        for f in sim_data.get_class(app).example_paths()
    ]


def find_user_simulation_copy(sim_type, sid, qcall):
    """ONLY USED BY api_simulationData"""
    rows = iterate_simulation_datafiles(
        sim_type,
        process_simulation_list,
        PKDict({"simulation.outOfSessionSimulationId": sid}),
        qcall=qcall,
    )
    if len(rows):
        return rows[0]["simulationId"]
    return None


def find_global_simulation(sim_type, sid, checked=False):
    paths = pkio.sorted_glob(user_path_root().join("*", sim_type, sid))
    if len(paths) == 1:
        return str(paths[0])
    if len(paths) == 0:
        if checked:
            raise util.NotFound(
                "{}/{}: global simulation not found",
                sim_type,
                sid,
            )
        return None
    raise util.NotFound(
        "{}: more than one path found for simulation={}/{}",
        paths,
        sim_type,
        sid,
    )


def fixup_old_data(data, force=False, path=None, qcall=None):
    """Upgrade data to latest schema and updates version.

    Args:
        data (dict): to be updated (destructively)
        force (bool): force validation
        path (py.path): simulation path, only in a few cases [None]

    Returns:
        dict: upgraded `data`
        bool: True if data changed
    """

    def _last_modified(data, path):
        if not path:
            return srtime.utc_now_as_milliseconds()
        m = 0.0
        for p in pkio.sorted_glob(
            # POSIT: same format as simulation_run_dir
            json_filename(
                sirepo.const.SIM_RUN_INPUT_BASENAME, run_dir=path.dirpath().join("*")
            ),
        ):
            if p.mtime() > m:
                m = p.mtime()
        if m <= 0.0:
            m = path.mtime()
        return int(m * 1000)

    try:
        pkdc(
            "sid={} force={}, version={} SCHEMA_COMMON.version={}",
            data.pkunchecked_nested_get("models.simulation.simulationId"),
            force,
            data.get("version"),
            SCHEMA_COMMON.version,
        )
        if not force and "version" in data and data.version == SCHEMA_COMMON.version:
            return data, False
        try:
            data.fixup_old_version = data.version
        except AttributeError:
            data.fixup_old_version = _OLDEST_VERSION
        data.version = SCHEMA_COMMON.version
        if "simulationType" not in data:
            if "sourceIntensityReport" in data.models:
                data.simulationType = "srw"
            elif "fieldAnimation" in data.models:
                data.simulationType = "warppba"
            elif "bunchSource" in data.models:
                data.simulationType = "elegant"
            else:
                pkdlog("simulationType: not found; data={}", data)
                raise AssertionError("must have simulationType")
        elif data.simulationType == "warp":
            data.simulationType = "warppba"
        elif data.simulationType == "fete":
            data.simulationType = "warpvnd"
        elif data.simulationType == "ml":
            data.simulationType = "activait"
        if "simulationSerial" not in data.models.simulation:
            data.models.simulation.simulationSerial = 0
        if "lastModified" not in data.models.simulation:
            data.models.simulation.lastModified = _last_modified(data, path)
        from sirepo import sim_data

        sim_data.get_class(data.simulationType).fixup_old_data(data, qcall=qcall)
        data.pkdel("fixup_old_version")
        return data, True
    except Exception as e:
        pkdlog("exception={} data={} stack={}", e, data, pkdexc())
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
    t = (
        util.assert_sim_type(sim_type)
        if sim_type is not None
        else list(feature_config.cfg().sim_types)[0]
    )
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


def init_module():
    pass


def iterate_simulation_datafiles(simulation_type, op, search=None, qcall=None):
    res = []
    sim_dir = simulation_dir(simulation_type, qcall=qcall)
    for p in pkio.sorted_glob(sim_dir.join("*", sirepo.const.SIM_DATA_BASENAME)):
        try:
            data = open_json_file(
                simulation_type,
                path=p,
                fixup=True,
                qcall=qcall,
            )
            if search and not _search_data(data, search):
                continue
            op(res, p, data)
        except ValueError as e:
            pkdlog("{}: error: {}", p, e)
    return res


def json_filename(filename, run_dir=None):
    """Append sirepo.const.JSON_SUFFIX if necessary and convert to str

    Args:
        filename (py.path or str): to convert
        run_dir (py.path): which directory to join (only if filename is str)
    Returns:
        py.path: filename.json
    """

    def _path():
        if not isinstance(filename, str):
            if run_dir:
                raise AssertionError(
                    f"filename={filename} is a py.path, cannot join run_dir={run_dir}"
                )
            return filename
        if not run_dir:
            return pkio.py_path(filename)
        if os.path.isabs(filename):
            raise AssertionError(
                f"filename={filename} is absolute, cannot join run_dir={run_dir}"
            )
        return run_dir.join(filename)

    p = _path()
    if p.ext == sirepo.const.JSON_SUFFIX:
        return p
    # Do not replace using new, because may already have suffix
    return p + sirepo.const.JSON_SUFFIX


def json_load(*args, **kwargs):
    return pkjson.load_any(*args, **kwargs)


def lib_dir_from_sim_dir(sim_dir):
    """Path to lib dir from simulation dir

    Args:
        sim_dir (py.path): simulation dir or below

    Return:
        py.path: directory name
    """
    return _sim_from_path(sim_dir)[1].join(_REL_LIB_DIR)


def mkdir_random(parent_dir, simulation_type=None):
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
        i = "".join(r.choice(_ID_CHARS) for x in range(_ID_LEN))
        if simulation_type:
            if find_global_simulation(simulation_type, i):
                continue
        d = parent_dir.join(i)
        try:
            os.mkdir(str(d))
            return PKDict(id=i, path=d)
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            raise
    raise RuntimeError("{}: failed to create unique directory".format(parent_dir))


def migrate_guest_to_persistent_user(guest_uid, to_uid, qcall):
    """Moves all non-example simulations `guest_uid` into `to_uid`.

    Only moves non-example simulations. Doesn't delete the guest_uid.

    Args:
        guest_uid (str): source user
        to_uid (str): dest user
    """
    with user_lock(uid=guest_uid, qcall=qcall) as g:
        with user_lock(uid=to_uid, qcall=qcall):
            for p in glob.glob(
                str(g.join("*", "*", sirepo.const.SIM_DATA_BASENAME)),
            ):
                if read_json(p).models.simulation.get("isExample"):
                    continue
                o = os.path.dirname(p)
                n = o.replace(guest_uid, to_uid)
                pkio.mkdir_parent(n)
                os.rename(o, n)


def open_json_file(sim_type, path=None, sid=None, fixup=True, qcall=None):
    """Read a db file and return result

    Args:
        sim_type (str): simulation type (app)
        path (py.path.local): where to read the file
        sid (str): simulation id
        fixup (bool): run fixup_old_data [True]
        save (bool): save_simulation_json if data changed [False]
    Returns:
        dict: data
    """
    p = path or sim_data_file(sim_type, sid, qcall=qcall)
    if not p.exists():
        if path:
            raise util.NotFound("path={} not found", path)
        raise util.SPathNotFound(sim_type=sim_type, sid=sid, uid=_uid_arg(qcall))
    data = None
    # TODO: no need for lock
    try:
        with p.open() as f:
            data = json_load(f)
        # ensure the simulationId matches the path
        if sid:
            data.models.simulation.simulationId = _sim_from_path(p)[0]
    except Exception as e:
        pkdlog("{}: error: {}", p, pkdexc())
        raise
    if not fixup:
        return data
    d, _ = fixup_old_data(data, path=p, qcall=qcall)
    return d


def parse_sim_ser(data):
    """Extract simulationSerial from data

    Args:
        data (dict): models or request

    Returns:
        int: simulationSerial
    """
    try:
        return int(data["simulationSerial"])
    except KeyError:
        try:
            return int(data["models"]["simulation"]["simulationSerial"])
        except KeyError:
            return None


def process_simulation_list(res, path, data):
    sim = data["models"]["simulation"]
    res.append(
        PKDict(
            appMode=sim.get("appMode", "default"),
            simulationId=_sim_from_path(path)[0],
            name=sim["name"],
            folder=sim["folder"],
            isExample=sim["isExample"] if "isExample" in sim else False,
            simulation=sim,
        )
    )


def read_json(filename):
    """Read data from json file

    Args:
        filename (py.path or str): will append sirepo.const.JSON_SUFFIX if necessary

    Returns:
        object: json converted to python
    """
    return json_load(json_filename(filename))


def read_simulation_json(sim_type, sid, qcall):
    """Calls `open_json_file` and fixes up data, possibly saving

    Args:
        sim_type (str): simulation type
        sid (str): simulation id

    Returns:
        data (dict): simulation data
    """
    p = sim_data_file(sim_type, sid, qcall=qcall)
    if not p.exists():
        raise util.SPathNotFound(sim_type=sim_type, sid=sid, uid=_uid_arg(qcall))
    data = None
    with user_lock(qcall=qcall):
        try:
            with p.open() as f:
                data = json_load(f)
            # ensure the simulationId matches the path
            if sid:
                data.models.simulation.simulationId = _sim_from_path(p)[0]
        except Exception as e:
            pkdlog("{}: error: {}", p, pkdexc())
            raise
        d, c = fixup_old_data(data, path=p, qcall=qcall)
        if c:
            return save_simulation_json(d, fixup=False, do_validate=False, qcall=qcall)
    return d


def save_new_example(data, qcall=None):
    data.models.simulation.isExample = True
    return save_new_simulation(
        data,
        do_validate=False,
        qcall=qcall,
    )


def save_new_simulation(data, do_validate=True, qcall=None):
    d = simulation_dir(data.simulationType, qcall=qcall)
    sid = mkdir_random(d, data.simulationType).id
    data.models.simulation.simulationId = sid
    data.models.simulation.simulationSerial = _SERIAL_INITIALIZE
    data.pkdel("version")
    return save_simulation_json(
        data,
        do_validate=do_validate,
        qcall=qcall,
        fixup=True,
        modified=True,
    )


def save_simulation_json(data, fixup, do_validate=True, qcall=None, modified=False):
    """Prepare data and save to json db

    Args:
        data (dict): what to write (contains simulationId)
        fixup (bool): whether to run fixup_old_data
        uid (str): user id [None]
        do_validate (bool): call srschema.validate_name [True]
        modified (bool): call prepare_for_save and update lastModified [False]
    """

    def _serial(incoming, on_disk):
        # Serial numbers are 16 digits (time represented in microseconds
        # since epoch) which are always less than Javascript's
        # Number.MAX_SAFE_INTEGER (9007199254740991=2*53-1).
        #
        # Timestamps are not guaranteed to be sequential so verify
        # against incoming and on_disk and assure is greater than both.
        res = int(time.time() * 1000000)
        if on_disk is None:
            return res
        o = _serial_validate(incoming.simulationSerial, on_disk.simulationSerial)
        if res <= o:
            res = o + 1
        return res

    def _serial_validate(incoming, on_disk):
        if incoming == _SERIAL_INITIALIZE or incoming == on_disk:
            return on_disk
        raise util.SRException(
            "serverUpgraded",
            PKDict(
                reason="invalidSimulationSerial",
                simulationType=data.get("simulationType"),
            ),
            "{}: incoming serial {} than stored serial={} sid={}, resetting client",
            incoming,
            "newer" if incoming > on_disk else "older",
            on_disk,
            data.pkunchecked_nested_get("models.simulation.simulationId"),
        )

    def _version_validate(data):
        # If there is no version, ignore.
        if data.get("version", SCHEMA_COMMON.version) != SCHEMA_COMMON.version:
            raise util.SRException(
                "serverUpgraded",
                PKDict(reason="newRelease", simulationType=data.get("simulationType")),
                "data={} != server={}",
                data.get("version"),
                SCHEMA_COMMON.version,
            )

    _version_validate(data)
    if fixup:
        data = fixup_old_data(data, qcall=qcall)[0]
        if modified:
            t = sirepo.template.import_module(data.simulationType)
            if hasattr(t, "prepare_for_save"):
                # TODO(robnagler) only case seems to be srw.import_file
                data = t.prepare_for_save(data, qcall=qcall)
    # old implementation value
    data.pkdel("computeJobHash")
    s = data.models.simulation
    sim_type = data.simulationType
    fn = sim_data_file(sim_type, s.simulationId, qcall=qcall)
    with user_lock(qcall=qcall):
        need_validate = True
        on_disk = None
        try:
            # OPTIMIZATION: If folder/name same, avoid reading entire folder
            on_disk = read_json(fn).models.simulation
            need_validate = not (on_disk.folder == s.folder and on_disk.name == s.name)
        except Exception:
            pass
        if need_validate and do_validate:
            srschema.validate_name(
                data,
                iterate_simulation_datafiles(
                    sim_type,
                    lambda res, _, d: res.append(d),
                    PKDict({"simulation.folder": s.folder}),
                    qcall=qcall,
                ),
                SCHEMA_COMMON.common.constants.maxSimCopies,
            )
            srschema.validate_fields(data, get_schema(data.simulationType))
        s.simulationSerial = _serial(s, on_disk)
        # Do not write simulationStatus or computeJobCacheKey
        d = copy.deepcopy(data)
        pkcollections.unchecked_del(d.models, "simulationStatus", "computeJobCacheKey")
        if modified:
            d.models.simulation.lastModified = srtime.utc_now_as_milliseconds()
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


def sim_data_file(sim_type, sim_id, qcall=None):
    """Simulation data file name

    Args:
        sim_type (str): simulation type
        sim_id (str): simulation id
        uid (str): user id

    Returns:
        py.path.local: simulation path
    """
    return simulation_dir(sim_type, sim_id, qcall=qcall).join(SIMULATION_DATA_FILE)


def sim_from_path(path):
    return _sim_from_path(path)


def simulation_dir(simulation_type, sid=None, qcall=None):
    """Generates simulation directory from sid and simulation_type

    Args:
        simulation_type (str): srw, warppba, ...
        sid (str): simulation id (optional)
        uid (str): user id
    """
    p = user_path(qcall=qcall, check=True)
    d = p.join(sirepo.template.assert_sim_type(simulation_type))
    if not d.exists():
        with user_lock(uid=uid_from_dir_name(p), qcall=qcall):
            if not d.exists():
                _create_lib_and_examples(p, d.basename, qcall=qcall)
    if not sid:
        return d
    return d.join(assert_sid(sid))


def simulation_lib_dir(simulation_type, qcall=None):
    """String name for user library dir

    Args:
        simulation_type: which app is this for

    Return:
        py.path: directory name
    """
    # POSIT: _create_lib_and_examples
    return simulation_dir(simulation_type, qcall=qcall).join(_LIB_DIR)


def simulation_run_dir(req_or_data, remove_dir=False, qcall=None):
    """Where to run the simulation

    Args:
        req_or_data (dict): may be simulation data or a request
        remove_dir (bool): remove the directory [False]

    Returns:
        py.path: directory to run
    """
    from sirepo import sim_data

    t = req_or_data.simulationType
    s = sim_data.get_class(t)
    d = simulation_dir(
        t,
        s.parse_sid(req_or_data),
        qcall=qcall,
    ).join(s.compute_model(req_or_data))
    if remove_dir:
        pkio.unchecked_remove(d)
    return d


def srunit_logged_in_user(uid):
    from pykern import pkunit

    if not pkunit.is_test_run():
        raise AssertionError("must be in pkunit test run")
    _cfg.logged_in_user = uid


def static_libs():
    return _files_in_schema(SCHEMA_COMMON.common.staticFiles)


def uid_from_dir_name(dir_name):
    """Extract user id from user_path

    Args:
        dir_name (py.path): must be top level user dir or sim_dir

    Return:
        str: user id
    """
    r = re.compile(
        r"^{}/({})(?:$|/)".format(
            re.escape(str(user_path_root())),
            _ID_PARTIAL_RE_STR,
        ),
    )
    m = r.search(str(dir_name))
    assert m, "{}: invalid user or sim dir; did not match re={}".format(
        dir_name,
        r.pattern,
    )
    return m.group(1)


def user_create():
    """Create a user and initialize the directory

    Returns:
        str: New user id
    """
    return mkdir_random(user_path_root())["id"]


@contextlib.contextmanager
def user_lock(uid=None, qcall=None):
    """Lock the user's directory (re-entrant)

    Args:
        uid (str): user to lock (or logged in user)
        qcall (sirepo.quest.API): request state
    Returns:
        py.path: user's directory
    """
    assert qcall
    p = user_path(uid=uid, qcall=qcall, check=True)
    if p in _USER_LOCK.paths:
        # re-enter, already locked path
        yield p
    else:
        try:
            _USER_LOCK.paths.add(p)
            with sirepo.file_lock.FileLock(p):
                yield p
        finally:
            _USER_LOCK.paths.discard(p)


def user_path(uid=None, qcall=None, check=False):
    """Path for uid or root of all users

    Args:
        uid (str): user id (qcall is preferred)
        qcall (quest.API): logged in user
        check (bool): assert directory exists
    Return:
        py.path: root user's directory
    """
    uid = _uid_arg(uid, qcall)
    d = user_path_root().join(uid)
    if check and not d.check():
        raise util.UserDirNotFound(user_dir=d, uid=uid)
    return d


def user_path_root():
    """Path for uid or root of all users

    Return:
        py.path: root of all users
    """
    return sirepo.srdb.root().join(USER_ROOT_DIR)


def write_json(filename, data):
    """Write data as json to filename

    pretty is true.

    Args:
        filename (py.path or str): will append sirepo.const.JSON_SUFFIX if necessary
    """
    util.json_dump(data, path=json_filename(filename), pretty=True)


def _create_lib_and_examples(user_dir, sim_type, qcall=None):
    # POSIT: simulation_lib_dir
    pkio.mkdir_parent(user_dir.join(sim_type).join(_LIB_DIR))
    # POSIT: user_dir structure
    uid = user_dir.basename
    for s in examples(sim_type):
        save_new_example(s, qcall=qcall)


def _extend_no_dupes(arr1, arr2):
    arr1.extend(x for x in arr2 if x not in arr1)


def _files_in_schema(schema):
    """Relative paths of local and external files of the given load and file type listed in the schema
    The order matters for javascript files

    Args:
        schema (PKDict): schema (or portion thereof) to inspect

    Returns:
        str: combined list of local and external file paths, mapped by type
    """
    paths = PKDict(css=[], js=[])
    for source, path in (("externalLibs", "ext"), ("sirepoLibs", "")):
        for file_type, files in schema[source].items():
            for f in files:
                paths[file_type].append(
                    sirepo.resource.static_url(file_type, path, f),
                )
    return paths


def _init():
    global _cfg, JOB_RUN_MODE_MAP

    _cfg = pkconfig.init(
        dev_version=(
            pkconfig.in_dev_mode(),
            bool,
            "Use time for schema and app version",
        ),
        logged_in_user=(None, str, "Used in agents"),
        sbatch_display=(None, str, "how to display sbatch cluster to user"),
    )
    _init_schemas()
    JOB_RUN_MODE_MAP = PKDict(
        sequential="Serial",
        parallel="{} cores (SMP)".format(sirepo.mpi.cfg().cores),
    )
    if _cfg.sbatch_display:
        JOB_RUN_MODE_MAP.sbatch = _cfg.sbatch_display


def _init_schemas():
    global SCHEMA_COMMON
    SCHEMA_COMMON = json_load(
        sirepo.resource.static("json", f"schema-common{sirepo.const.JSON_SUFFIX}")
    )
    SCHEMA_COMMON.pkupdate(sirepo.const.SCHEMA_COMMON)
    a = SCHEMA_COMMON.appInfo
    for t in sirepo.feature_config.cfg().sim_types:
        s = read_json(sirepo.resource.static("json", f"{t}-schema.json"))
        _merge_dicts(s.get("appInfo", PKDict()), a)
        s.update(SCHEMA_COMMON)
        s.feature_config = feature_config.for_sim_type(t)
        s.simulationType = t

        # TODO(mvk): improve merging common and local schema
        _merge_dicts(s.common.dynamicFiles, s.dynamicFiles)
        s.dynamicModules = _files_in_schema(s.dynamicFiles)
        for i in [
            "appDefaults",
            "appModes",
            "constants",
            "enum",
            "localRoutes",
            "model",
            "strings",
            "view",
        ]:
            if i not in s:
                s[i] = PKDict()
            _merge_dicts(s.common[i], s[i])
        _merge_subclasses(s, "model", extend_arrays=False)
        _merge_subclasses(s, "view", extend_arrays=True)
        srschema.validate(s)
        _SCHEMA_CACHE[t] = s
    SCHEMA_COMMON.appInfo = a
    for s in _SCHEMA_CACHE.values():
        s.appInfo = a
    # In development, any schema update creates a new version
    if _cfg.dev_version:
        SCHEMA_COMMON.version = _now_as_version()
    else:
        SCHEMA_COMMON.version = max(
            [m.__version__ for m in sirepo.resource.root_modules()]
        )


def _merge_dicts(base, derived, depth=-1, extend_arrays=True):
    """Copy the items in the base dictionary into the derived dictionary, to the specified depth

    Args:
        base (dict): source
        derived (dict): receiver
        depth (int): how deep to recurse:
            >= 0:  <depth> levels
            < 0:   all the way
        extend_arrays (bool): if True, merging will extend arrays that exist in both
        dicts. Otherwise, the arrays are replaced
    """
    if depth == 0:
        return
    for key in base:
        # Items with the same name are not replaced
        if key not in derived:
            derived[key] = base[key]
        else:
            try:
                if extend_arrays:
                    _extend_no_dupes(derived[key], base[key])
            except AttributeError:
                # The value was not an array
                pass
        try:
            _merge_dicts(base[key], derived[key], depth - 1 if depth > 0 else depth)
        except TypeError:
            # The value in question is not itself a dict, move on
            pass


def _merge_subclasses(schema, item, extend_arrays=True):
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
        assert sub_item in schema, util.err(sub_item, "No such field in schema")
        assert sub_item == item, util.err(
            sub_item, "Superclass must be in same section of schema {}", item
        )
        assert sub_key in item_schema, util.err(sub_key, "No such superclass")
        subclass_keys.append(sub_key)
        _unnest_subclasses(schema, item, sub_key, subclass_keys)

    for m in schema[item]:
        item_schema = schema[item]
        model = item_schema[m]
        subclasses = []
        _unnest_subclasses(schema, item, m, subclasses)
        for s in subclasses:
            _merge_dicts(item_schema[s], model, extend_arrays=extend_arrays)
        # _super is a special case
        if subclasses:
            _extend_no_dupes(model[_SCHEMA_SUPERCLASS_FIELD], subclasses)


def _now_as_version():
    return srtime.utc_now().strftime("%Y%m%d.%H%M%S")


def _search_data(data, search):
    for field, expect in search.items():
        path = field.split(".")
        if len(path) == 1:
            # TODO(robnagler) is this a bug? Why would you supply a search path
            # value that didn't want to be searched.
            continue
        path.insert(0, "models")
        v = data
        for key in path:
            if key in v:
                v = v[key]
        if v != expect:
            return False
    return True


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
    raise AssertionError("path={} is not valid simulation".format(path))


def _uid_arg(uid=None, qcall=None):
    if uid:
        return uid
    if qcall:
        # Avoid recursion to user_path with check_path=False
        return qcall.auth.logged_in_user(check_path=False)
    uid = _cfg.logged_in_user
    assert uid, "uid not supplied and no logged_in_user config"
    return uid


_init()
