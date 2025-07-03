"""Type-based simulation operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkconfig
from pykern import pkconst
from pykern import pkinspect
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdexc, pkdc, pkdformat
import hashlib
import os.path
import re
import sirepo.const
import sirepo.feature_config
import sirepo.job
import sirepo.resource
import sirepo.srdb
import sirepo.util
import subprocess
import urllib
import uuid

_cfg = None

#: default compute_model
_ANIMATION_NAME = "animation"

#: models which should not get persisted
_CLIENT_ONLY_MODELS = frozenset(
    (
        "completeRegistration",
        "emailLogin",
        "ldapLogin",
        "moderationRequest",
        "renameItem",
    )
)

_MODEL_RE = re.compile(r"^[\w-]+$")

_IS_PARALLEL_RE = re.compile("animation", re.IGNORECASE)

#: separates values in frame id
_FRAME_ID_SEP = "*"

#: common keys to frame id followed by code-specific values
_FRAME_ID_KEYS = (
    "frameIndex",
    # computeModel when passed from persistent/parallel
    # analysisModel when passe from transient/sequential
    # sim_data.compute_model() is idempotent to this.
    "frameReport",
    "simulationId",
    "simulationType",
    "computeJobHash",
    "computeJobSerial",
)

_TEMPLATE_RESOURCE_DIR = "template"

#: Absolute path of rsmanifest file
_RSMANIFEST_PATH = pkio.py_path("/rsmanifest" + sirepo.const.JSON_SUFFIX)


def audit_proprietary_lib_files(qcall, force=False, sim_types=None, uid=None):
    """Add/removes proprietary files based on a user's roles

    For example, add the Flash tarball if user has the flash role.

    Args:
      qcall (quest.API): logged in user
      force (bool): Overwrite existing lib files with the same name as new ones
      sim_types (set): Set of sim_types to audit (proprietary_sim_types if None)
    """
    from sirepo import simulation_db, sim_run

    def _add(proprietary_code_dir, sim_type, cls):
        p = proprietary_code_dir.join(cls.proprietary_code_tarball())
        with sim_run.tmp_dir(chdir=True, qcall=qcall) as t:
            d = t.join(p.basename)
            d.mksymlinkto(p, absolute=False)
            subprocess.check_output(
                [
                    "tar",
                    "--extract",
                    "--gunzip",
                    f"--file={d}",
                ],
                stderr=subprocess.STDOUT,
            )
            # lib_dir may not exist: git.radiasoft.org/ops/issues/645
            l = pkio.mkdir_parent(
                simulation_db.simulation_lib_dir(sim_type, qcall=qcall),
            )
            e = [f.basename for f in pkio.sorted_glob(l.join("*"))]
            for f in cls.proprietary_code_lib_file_basenames():
                if force or f not in e:
                    t.join(f).rename(l.join(f))

    def _iter(stypes, uid):
        for t in stypes:
            c = get_class(t)
            if not c.proprietary_code_tarball():
                continue
            d = sirepo.srdb.proprietary_code_dir(t)
            assert d.exists(), f"{d} proprietary_code_dir must exist" + (
                "; run: sirepo setup_dev" if pkconfig.in_dev_mode() else ""
            )
            r = qcall.auth_db.model("UserRole").has_active_role(
                role=sirepo.auth_role.for_sim_type(t),
                uid=uid,
            )
            if r:
                _add(d, t, c)
                continue
            # SECURITY: User no longer has access so remove all artifacts
            pkio.unchecked_remove(simulation_db.simulation_dir(t, qcall=qcall))

    def _sim_types():
        rv = sirepo.feature_config.proprietary_sim_types()
        if not sim_types:
            return rv
        if not sim_types.issubset(rv):
            raise AssertionError(
                f"sim_types={sim_types} not a subset of proprietary_sim_types={rv}"
            )
        return sim_types

    s = _sim_types()
    if uid:
        with qcall.auth.logged_in_user_set(uid):
            _iter(s, uid)
    else:
        _iter(s, qcall.auth.logged_in_user(check_path=False))


def get_class(type_or_data):
    """Simulation data class

    Args:
        type_or_data (str or dict): simulation type or description
    Returns:
        type: simulation data operation class
    """
    return sirepo.util.import_submodule("sim_data", type_or_data).SimData


def resource_path(filename):
    """Path to common (not specific to sim type) resource file"""
    return sirepo.resource.file_path(_TEMPLATE_RESOURCE_DIR, filename)


def template_globals(sim_type=None):
    """Initializer for templates

    Usage::
        _SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

    Args:
        sim_type (str): simulation type [calling module's basename]
    Returns:
        (class, str, object): SimData class, simulation type, and schema
    """
    c = get_class(sim_type or pkinspect.module_basename(pkinspect.caller_module()))
    return c, c.sim_type(), c.schema()


def parse_frame_id(frame_id):
    """Parse the frame_id and return it along with self

    Args:
        frame_id (str): values separated by "*"
    Returns:
        PKDict: frame_args
        SimDataBase: sim_data object for this simulationType
    """

    v = frame_id.split(_FRAME_ID_SEP)
    res = PKDict(zip(_FRAME_ID_KEYS, v[: len(_FRAME_ID_KEYS)]))
    res.frameIndex = int(res.frameIndex)
    res.computeJobSerial = int(res.computeJobSerial)
    s = get_class(res.simulationType)
    s.frameReport = s.parse_model(res)
    s.simulationId = s.parse_sid(res)
    # TODO(robnagler) validate these
    res.update(
        zip(
            s._frame_id_fields(res),
            [SimDataBase._frame_param_to_field(x) for x in v[len(_FRAME_ID_KEYS) :]],
        )
    )
    return res, s


class SimDataBase(object):
    ANALYSIS_ONLY_FIELDS = frozenset()

    WATCHPOINT_REPORT = "watchpointReport"

    WATCHPOINT_REPORT_RE = re.compile(r"^{}(\d+)$".format(WATCHPOINT_REPORT))

    _EXAMPLE_RESOURCE_DIR = "examples"

    _EXE_PERMISSIONS = 0o700

    LIB_DIR = sirepo.const.LIB_DIR

    @classmethod
    def compute_job_hash(cls, data, qcall):
        """Hash fields related to data and set computeJobHash

        Only needs to be unique relative to the report, not globally unique
        so MD5 is adequate. Long and cryptographic hashes make the
        cache checks slower.

        Args:
            data (dict): simulation data
            changed (callable): called when value changed
        Returns:
            bytes: hash value
        """
        cls._assert_server_side()
        c = cls.compute_model(data)
        if data.get("forceRun") or cls.is_parallel(c):
            return "HashIsUnused"
        m = data["models"]
        res = hashlib.md5()
        fields = sirepo.sim_data.get_class(data.simulationType)._compute_job_fields(
            data, data.report, c
        )
        # values may be string or PKDict
        fields.sort(key=lambda x: str(x))
        for f in fields:
            # assert isinstance(f, pkconfig.STRING_TYPES), \
            #     'value={} not a string_type'.format(f)
            # TODO(pjm): work-around for now
            if isinstance(f, pkconfig.STRING_TYPES):
                x = f.split(".")
                value = m[x[0]][x[1]] if len(x) > 1 else m[x[0]]
            else:
                value = f
            res.update(
                pkjson.dump_bytes(
                    value,
                    sort_keys=True,
                    allow_nan=False,
                )
            )
        res.update(
            "".join(
                (
                    str(cls.lib_file_abspath(b, data=data, qcall=qcall).mtime())
                    for b in sorted(cls.lib_file_basenames(data))
                ),
            ).encode()
        )
        return res.hexdigest()

    @classmethod
    def compute_model(cls, model_or_data):
        """Compute model for this model_or_data

        Args:
            model_or_data (): analysis model
        Returns:
            str: name of compute model for report
        """
        m = cls.parse_model(model_or_data)
        d = model_or_data if isinstance(model_or_data, dict) else None
        # TODO(robnagler) is this necesary since m is parsed?
        return cls.parse_model(cls._compute_model(m, d))

    @classmethod
    def does_api_reply_with_file(cls, api, method):
        """Identify which job_api calls expect files

        Args:
            api (str): job_api method, e.g. api_statelessCompute
            method (str): template sub-method of `api`, e.g. sample_preview
        Returns:
            bool: True if `method` can return a file
        """
        return False

    @classmethod
    def example_paths(cls):
        return sirepo.resource.glob_paths(
            _TEMPLATE_RESOURCE_DIR,
            cls.sim_type(),
            cls._EXAMPLE_RESOURCE_DIR,
            f"*{sirepo.const.JSON_SUFFIX}",
        )

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        """Update model data to latest schema

        Modifies `data` in place.

        Args:
            data (dict): simulation
        """
        raise NotImplementedError()

    @classmethod
    def frame_id(cls, data, response, model, index):
        """Generate a frame_id from values (unit testing)

        Args:
            data (PKDict): model data
            response (PKDict): JSON response
            model (str): animation name
            index (int): index of frame
        Returns:
            str: combined frame id
        """
        assert response.frameCount > index, pkdformat(
            "response={} does not contain enough frames for index={}", response, index
        )
        frame_args = response.copy()
        frame_args.frameReport = model
        m = data.models[model]
        return _FRAME_ID_SEP.join(
            [
                # POSIT: same order as _FRAME_ID_KEYS
                str(index),
                model,
                data.models.simulation.simulationId,
                data.simulationType,
                response.computeJobHash,
                str(response.computeJobSerial),
            ]
            + [pkjson.dump_str(m.get(k)) for k in cls._frame_id_fields(frame_args)],
        )

    @classmethod
    def is_parallel(cls, data_or_model):
        """Is this report a parallel (long) simulation?

        Args:
            data_or_model (dict): sim data or compute_model

        Returns:
            bool: True if parallel job
        """
        return bool(
            _IS_PARALLEL_RE.search(
                cls.compute_model(data_or_model)
                if isinstance(data_or_model, dict)
                else data_or_model
            ),
        )

    @classmethod
    def is_run_mpi(cls):
        raise NotImplementedError()

    @classmethod
    def is_watchpoint(cls, name):
        return cls.WATCHPOINT_REPORT in name

    @classmethod
    def lib_file_abspath(cls, basename, data=None, qcall=None):
        """Returns full, unique paths of simulation files

        Args:
            basename (str): lib file basename
            data: DEPRECATED
        Returns:
            object: py.path.local to files (duplicates removed) OR py.path.local
        """
        p = cls._lib_file_abspath_or_exists(basename, qcall=qcall)
        if p:
            return p

        raise sirepo.util.UserAlert(
            'Simulation library file "{}" does not exist'.format(basename),
            "basename={} not in lib or resource directories",
            basename,
        )

    @classmethod
    def lib_file_basenames(cls, data):
        """List files used by the simulation

        Args:
            data (dict): sim db
        Returns:
            set: list of str, sorted
        """
        # _lib_file_basenames may return duplicates
        return sorted(set(cls._lib_file_basenames(data)))

    @classmethod
    def lib_file_exists(cls, basename, qcall=None):
        """Does `basename` exist in library

        Args:
            basename (str): to test for existence
            qcall (quest.API): quest state
        Returns:
            bool: True if it exists
        """
        return cls._lib_file_abspath_or_exists(basename, qcall=qcall, exists_only=True)

    @classmethod
    def lib_file_is_zip(cls, basename):
        """Is this lib file a zip file?

        Args:
            basename (str): to search
        Returns:
            bool: True if is a zip file
        """
        return basename.endswith(".zip")

    @classmethod
    def lib_file_in_use(cls, data, basename):
        """Check if file in use by simulation

        Args:
            data (dict): simulation
            basename (str): to check
        Returns:
            bool: True if `basename` in use by `data`
        """
        return any(
            f
            for f in cls.lib_file_basenames(data)
            if cls.lib_file_name_without_type(f)
            == cls.lib_file_name_without_type(basename)
        )

    @classmethod
    def lib_file_names_for_type(cls, file_type, qcall=None):
        """Return sorted list of files which match `file_type`

        Args:
            file_type (str): in the format of ``model-field``
        Returns:
            list: sorted list of file names stripped of file_type
        """
        return sorted(
            (
                cls.lib_file_name_without_type(f.basename)
                for f in cls._lib_file_list("{}.*".format(file_type), qcall=qcall)
            )
        )

    @classmethod
    def lib_file_name_with_model_field(cls, model_name, field, filename):
        return "{}-{}.{}".format(model_name, field, filename)

    @classmethod
    def lib_file_name_with_type(cls, filename, file_type):
        return "{}.{}".format(file_type, filename)

    @classmethod
    def lib_file_name_without_type(cls, basename):
        """Strip the file type prefix

        See `lib_file_name` which prefixes with ``model-field.``

        Args:
            basename: lib file name with type
        Returns:
            str: basename without type prefix
        """
        return re.sub(r"^.*?-.*?\.(.+\..+)$", r"\1", basename)

    @classmethod
    def lib_file_resource_path(cls, basename):
        """Location of lib file in source distribution

        Args:
            basename (str): complete name of lib file
        Returns:
            py.path: Absolute path to file in source distribution
        """
        return sirepo.resource.file_path(
            _TEMPLATE_RESOURCE_DIR,
            cls.sim_type(),
            cls.LIB_DIR,
            basename,
        )

    @classmethod
    def lib_file_read_binary(cls, basename, qcall=None):
        """Get contents of `basename` from lib as bytes

        Args:
            basename (str): full name including suffix
            qcall (quest.API): logged in user
        Returns:
            bytes: contents of file
        """
        if cls._is_agent_side():
            return cls.sim_db_client().get(cls.LIB_DIR, basename)
        return cls._lib_file_abspath(basename, qcall=qcall).read_binary()

    @classmethod
    def lib_file_read_text(cls, *args, **kwargs):
        """Get contents of `basename` from lib as str

        Args:
            basename (str): full name including suffix
            qcall (quest.API): logged in user
        Returns:
            str: contents of file
        """
        return pkcompat.from_bytes(cls.lib_file_read_binary(*args, **kwargs))

    @classmethod
    def lib_file_save_from_url(cls, url, model_name, field):
        """Fetch `url` and save to lib

        Path to save to is `lib_file_name_with_model_field` is called
        with the basename of `url`.

        Args:
            url (str): web address
            model_name (str): model name
            field (str): field of the model
        """
        c = cls.sim_db_client()
        c.save_from_url(
            url,
            c.uri(
                cls.LIB_DIR,
                cls.lib_file_name_with_model_field(
                    model_name,
                    field,
                    os.path.basename(urllib.parse.urlparse(url).path),
                ),
            ),
        )

    @classmethod
    def lib_file_size(cls, basename, qcall=None):
        """Get size of `basename` from lib

        Args:
            basename (str): full name including suffix
            qcall (quest.API): logged in user
        Returns:
            int: size in bytes
        """
        if cls._is_agent_side():
            return cls.sim_db_client().size(cls.LIB_DIR, basename)
        return cls._lib_file_abspath(basename, qcall=qcall).size()

    @classmethod
    def lib_file_write(cls, basename, path_or_content, qcall=None):
        """Save `content` to `basename` in lib

        Args:
            basename (str): full name including suffix
            path_or_content (str|bytes|py.path): what to save, may be text or binary
            qcall (quest.API): logged in user
        """

        def _target():
            return (
                cls._simulation_db()
                .simulation_lib_dir(cls.sim_type(), qcall=qcall)
                .join(basename)
            )

        if cls._is_agent_side():
            cls.sim_db_client().put(cls.LIB_DIR, basename, path_or_content)
            return
        if isinstance(path_or_content, pkconst.PY_PATH_LOCAL_TYPE):
            path_or_content.copy(_target())
        else:
            _target().write_binary(pkcompat.to_bytes(path_or_content))

    @classmethod
    def lib_file_write_path(cls, basename, qcall=None):
        """DEPRECATED: Use `lib_file_write`"""

        return (
            cls._simulation_db()
            .simulation_lib_dir(cls.sim_type(), qcall=qcall)
            .join(basename)
        )

    @classmethod
    def lib_files_for_export(cls, data, qcall=None):
        cls._assert_server_side()
        res = []
        for b in cls.lib_file_basenames(data):
            f = cls.lib_file_abspath(b, data=data, qcall=qcall)
            if f.exists():
                res.append(f)
        return res

    @classmethod
    def lib_files_from_other_user(cls, data, other_lib_dir, qcall):
        """Copy auxiliary files to other user

        Does not copy resource files. Only works locally.

        Args:
            data (dict): simulation db
            other_lib_dir (py.path): source directory
        """
        t = cls._simulation_db().simulation_lib_dir(cls.sim_type(), qcall=qcall)
        for f in cls._lib_file_basenames(data):
            s = other_lib_dir.join(f)
            if s.exists():
                s.copy(t.join(f))

    @classmethod
    def lib_files_to_run_dir(cls, data, run_dir):
        """Copy auxiliary files to run_dir

        Args:
            data (dict): simulation db
            run_dir (py.path): where to copy to
        """
        for b in cls.lib_file_basenames(data):
            t = run_dir.join(b)
            s = cls.lib_file_abspath(b, data=data)
            if t != s:
                t.mksymlinkto(s, absolute=False)

    @classmethod
    def model_defaults(cls, name):
        """Returns a set of default model values from the schema.

        Some special cases:
            if the data type is "UUID" and the default value is empty, set the
            value to a new UUID string

            if the data type is "RandomId" and the default value is empty, set the
            value to a new Base62 string

            if the data type has the form "model.zzz", set the value to the default
            value of model "zzz"

        Args:
            name (str): model name
        """
        import copy

        res = PKDict()
        for f, d in cls.schema().model[name].items():
            if len(d) >= 3 and d[2] is not None:
                m = d[1].split(".")
                if len(m) > 1 and m[0] == "model" and m[1] in cls.schema().model:
                    res[f] = cls.model_defaults(m[1])
                    for ff, dd in d[2].items():
                        res[f][ff] = copy.deepcopy(d[2][ff])
                    continue
                res[f] = copy.deepcopy(d[2])
                if d[1] == "UUID" and not res[f]:
                    res[f] = str(uuid.uuid4())
                if d[1] == "RandomId" and not res[f]:
                    res[f] = sirepo.util.random_base62(length=16)
        return res

    @classmethod
    def parse_jid(cls, data, uid):
        """A Job is a tuple of user, sid, and compute_model.

        A jid is words and dashes.

        Args:
            data (dict): extract sid and compute_model
            uid (str): user id
        Returns:
            str: unique name (treat opaquely)
        """
        return sirepo.job.join_jid(uid, cls.parse_sid(data), cls.compute_model(data))

    @classmethod
    def parse_model(cls, obj):
        """Find the model in the arg

        Looks for `frameReport`, `report`, and `modelName`. Might be a compute or
        analysis model.

        Args:
            obj (str or dict): simulation type or description
        Returns:
            str: target of the request
        """
        if isinstance(obj, pkconfig.STRING_TYPES):
            res = obj
        elif isinstance(obj, dict):
            for i in ("frameReport", "report", "computeModel", "modelName"):
                if i in obj:
                    res = obj.get(i)
                    break
            else:
                res = None
        else:
            raise AssertionError("obj={} is unsupported type={}", obj, type(obj))
        assert res and _MODEL_RE.search(res), "invalid model={} from obj={}".format(
            res, obj
        )
        return res

    @classmethod
    def parse_sid(cls, obj):
        """Extract simulationId from obj

        Args:
            obj (object): may be data, req, resp, or string
        Returns:
            str: simulation id
        """
        if isinstance(obj, pkconfig.STRING_TYPES):
            res = obj
        elif isinstance(obj, dict):
            res = obj.get("simulationId") or obj.pknested_get(
                "models.simulation.simulationId"
            )
        else:
            raise AssertionError("obj={} is unsupported type={}", obj, type(obj))
        return cls._simulation_db().assert_sid(res)

    @classmethod
    def poll_seconds(cls, data):
        """Client poll period for simulation status

        TODO(robnagler) needs to be encapsulated

        Args:
            data (dict): must container report name
        Returns:
            int: number of seconds to poll
        """
        return 2 if cls.is_parallel(data) else 1

    @classmethod
    def prepare_import_file_args(cls, req):
        return cls._prepare_import_file_name_args(req).pkupdate(
            file_as_str=req.form_file.as_str(),
            import_file_arguments=req.import_file_arguments,
        )

    @classmethod
    def proprietary_code_tarball(cls):
        return None

    @classmethod
    def proprietary_code_lib_file_basenames(cls):
        return []

    @classmethod
    def put_sim_file(cls, sim_id, src_file_name, dst_basename):
        """Write a file to the simulation's database directory

        Args:
            sim_id (str): simulation id
            src_file_name (str or py.path): local file to send to sim_db
            dst_basename (str): name in sim repo dir
        """
        return cls.sim_db_client().put(
            sim_id,
            dst_basename,
            pkio.read_binary(src_file_name),
        )

    @classmethod
    def resource_path(cls, filename):
        """Static resource (package_data) file for simulation

        Returns:
            py.path.local: absolute path to file
        """
        return sirepo.resource.file_path(
            _TEMPLATE_RESOURCE_DIR, cls.sim_type(), filename
        )

    @classmethod
    def schema(cls):
        """Get schema for code

        Returns:
            PKDict: schema
        """
        # TODO(robnagler) cannot use cls._simulation_db, because needed in templates
        # schema should be available so move out of simulation_db.
        from sirepo import simulation_db

        return cls._memoize(simulation_db.get_schema(cls.sim_type()))

    @classmethod
    def sim_db_client(cls):
        """Low-level for sim_db_file ops for job agents

        Used to manipulate sim db files in job agent. Care should be
        taken to avoid inefficiencies as these are remote requests.
        Typically, these are done in job_cmd, not job_agent, because
        operations are synchronous.

        Returns:
            SimDbClient: interface to `sirepo.sim_db_file`
        """
        # This assertion is sufficient even though memoized, because
        # it is executed once per process.
        from sirepo import sim_db_file

        cls._assert_agent_side()
        return cls._memoize(sim_db_file.SimDbClient(cls))

    @classmethod
    def sim_db_read_sim(cls, sim_id, sim_type=None, qcall=None):
        """Read simulation sdata for `sim_id`

        Calls `simulation_db.read_simulation_json`

        Args:
            sim_id (str): which simulation
            sim_type (str): simulation type [`cls.sim_type()`]
            qcall (quest.API): quest [None]
        Returns:
            PKDict: sdata
        """
        if cls._is_agent_side():
            return cls.sim_db_client().read_sim(sim_id, sim_type=sim_type)
        return cls._simulation_db().read_simulation_json(
            sim_type or cls.sim_type(), sim_id, qcall=qcall
        )

    @classmethod
    def sim_db_save_sim(cls, sdata, qcall=None):
        """Save `sdata` to simulation db.

        Calls `simulation_db.save_simulation_json`

        Args:
            sdata (PKDict): what to write
            qcall (quest.API): quest [None]
        Returns:
            PKDict: updated sdata
        """
        if not isinstance(sdata, PKDict):
            raise AssertionError(f"sdata unexpected type={type(sdata)}")
        if cls._is_agent_side():
            return cls.sim_db_client().save_sim(sdata)
        # TODO(robnagler) normalize so that same code is used
        return cls._simulation_db().save_simulation_json(
            sdata,
            fixup=True,
            qcall=qcall,
            modified=True,
        )

    @classmethod
    def sim_file_basenames(cls, data):
        """List of files needed for this simulation

        Returns:
            list: basenames of sim repo dir
        """
        return cls._sim_file_basenames(data)

    @classmethod
    def sim_files_to_run_dir(cls, data, run_dir):
        """Copy files from sim repo dir to `run_dir`

        Calls `sim_file_basenames` to get list of sim files.

        Args:
            data (PKDict): used to identify simulation
            run_dir (py.path): directory to write to
        """
        for b in cls.sim_file_basenames(data):
            cls._read_binary_and_save(
                data.models.simulation.simulationId,
                b.basename,
                run_dir,
                is_exe=b.get("is_exe", False),
            )

    @classmethod
    def sim_run_dir_prepare(cls, run_dir, data=None):
        """Create and install files, update parameters, and generate command.

        Copies files into the simulation directory (``run_dir``)
        Updates the parameters in ``data`` and save.
        Generate the pkcli command.

        Args:
            run_dir (py.path.local or str): dir simulation will be run in
            data (PKDict): optional, will read from run_dir
        Returns:
            list: pkcli command to execute
        """
        from sirepo import sim_data

        def _cmd(run_dir, data, template):
            p = cls.is_parallel(data)
            if rv := template.write_parameters(data, run_dir=run_dir, is_parallel=p):
                return rv
            return [
                pkinspect.root_package(template),
                pkinspect.module_basename(template),
                "run-background" if p else "run",
                str(run_dir),
            ]

        def _data(run_dir, data):
            if rv := cls.sim_run_input(run_dir, checked=False):
                return rv
            if data:
                cls.sim_run_input_to_run_dir(data, run_dir)
                return data
            raise FileNotFoundError(f"path={cls.sim_run_input_path(run_dir)}")

        r = pkio.py_path(run_dir)
        d = _data(r, data)
        cls.support_files_to_run_dir(data=d, run_dir=r)
        return _cmd(r, d, sirepo.template.import_module(cls.sim_type()))

    @classmethod
    def sim_run_input(cls, run_dir, checked=True):
        """Read input from run dir

        Args:
            run_dir (py.path): directory containing input file
            checked (bool): raise if not found [True]
        Returns:
            PKDict: sim input data or None if not checked
        """
        try:
            return pkjson.load_any(run_dir.join(sirepo.const.SIM_RUN_INPUT_BASENAME))
        except Exception as e:
            if not checked and pkio.exception_is_not_found(e):
                return None
            raise

    @classmethod
    def sim_run_input_path(cls, run_dir):
        """Generate path from run_dir

        Args:
            run_dir (py.path): directory containing input file
        Returns:
            py.path: path to run input
        """
        return run_dir.join(sirepo.const.SIM_RUN_INPUT_BASENAME)

    @classmethod
    def sim_run_input_fixup(cls, data):
        """Fixup data for simulation input

        Args:
            data (PKDict): for a run or whole sim data
        Returns:
            PKDict: fixed up data
        """
        try:
            data.rsmanifest = pkjson.load_any(_RSMANIFEST_PATH)
        except Exception as e:
            if not pkio.exception_is_not_found(e):
                raise
        return data

    @classmethod
    def sim_run_input_to_run_dir(cls, data, run_dir):
        """Read input from run dir

        Args:
            data (PKDict): for a run or whole sim data
            run_dir (py.path): directory read from
        Returns:
            PKDict: fixed up sim input data
        """
        pkjson.dump_pretty(
            cls.sim_run_input_fixup(data),
            filename=cls.sim_run_input_path(run_dir),
        )
        return data

    @classmethod
    def sim_type(cls):
        return cls._memoize(pkinspect.module_basename(cls))

    @classmethod
    def support_files_to_run_dir(cls, data, run_dir):
        cls.lib_files_to_run_dir(data, run_dir)
        cls.sim_files_to_run_dir(data, run_dir)

    @classmethod
    def update_model_defaults(cls, model, name, dynamic=None):
        defaults = cls.model_defaults(name)
        if dynamic:
            defaults.update(dynamic(name))
        for f in defaults:
            if f not in model:
                model[f] = defaults[f]

    @classmethod
    def want_browser_frame_cache(cls, report):
        return True

    @classmethod
    def watchpoint_id(cls, report):
        m = cls.WATCHPOINT_REPORT_RE.search(report)
        if not m:
            raise RuntimeError("invalid watchpoint report name: ", report)
        return int(m.group(1))

    @classmethod
    def _assert_agent_side(cls):
        if not cls._is_agent_side():
            raise AssertionError(
                f"method={pkinspect.caller_func_name()} only in job_agent"
            )

    @classmethod
    def _assert_server_side(cls):
        if cls._is_agent_side():
            raise AssertionError(
                f"method={pkinspect.caller_func_name()} not available in job_agent"
            )

    @classmethod
    def _compute_model(cls, analysis_model, resp):
        """Returns ``animation`` for models with ``Animation`` in name

        Subclasses should override, but call this. The mapping of
        ``<name>Animation`` to ``animation`` should stay consistent here.

        Args:
            model (str): analysis model
            resp (PKDict): analysis model
        Returns:
            str: name of compute model for analysis_model
        """
        if _ANIMATION_NAME in analysis_model.lower():
            return _ANIMATION_NAME
        return analysis_model

    @classmethod
    def _force_recompute(cls):
        """Random value to force a compute_job to recompute.

        Used by `_compute_job_fields`

        Returns:
            str: random value same length as md5 hash
        """
        return sirepo.util.random_base62(32)

    @classmethod
    def _frame_id_fields(cls, frame_args):
        """Schema specific frame_id fields"""
        f = cls.schema().frameIdFields
        r = frame_args.frameReport
        return f[r] if r in f else f[cls.compute_model(r)]

    @classmethod
    def _frame_param_to_field(cls, param):
        from json.decoder import JSONDecodeError

        try:
            return pkjson.load_any(param)
        except JSONDecodeError:
            return param

    @classmethod
    def _init_models(cls, models, names=None, dynamic=None):
        if names:
            names = set(list(names) + ["simulation"])
        for n in names or cls.schema().model:
            if n in _CLIENT_ONLY_MODELS:
                continue
            cls.update_model_defaults(
                models.setdefault(n, PKDict()),
                n,
                dynamic=dynamic,
            )

    @classmethod
    def _is_agent_side(cls):
        from sirepo import sim_db_file

        return cls._memoize(bool(sim_db_file.in_job_agent()))

    @classmethod
    def _lib_file_abspath(cls, basename, qcall):
        """Path in user lib directory for `basename`"""
        return (
            cls._simulation_db()
            .simulation_lib_dir(cls.sim_type(), qcall=qcall)
            .join(basename)
        )

    @classmethod
    def _lib_file_abspath_or_exists(
        cls,
        basename,
        qcall=None,
        exists_only=False,
    ):
        """Absolute path of lib file

        On agent downloads file unless `exists_only`.

        For utilities (`cfg.lib_file_resource_only`) only checks
        resources (not user library).

        Args:
            basename (str): name to find
            qcall (quest.API): quest [None]
            exists_only (bool): if ``True`` do not download [False]

        Returns:
            object: bool if `exists_only` else py.path
        """
        if cls._is_agent_side():
            if exists_only:
                if cls.sim_db_client().exists(cls.LIB_DIR, basename):
                    return True
            else:
                try:
                    return cls._read_binary_and_save(
                        cls.LIB_DIR, basename, pkio.py_path()
                    )
                except Exception as e:
                    if not pkio.exception_is_not_found(e):
                        raise
                    # try to find below
        elif not _cfg.lib_file_resource_only:
            # Command line utility or server
            f = cls._lib_file_abspath(basename, qcall)
            if f.check(file=True):
                return exists_only or f
        try:
            # Lib file distributed with build
            f = cls.lib_file_resource_path(basename)
            if f.check(file=True):
                return exists_only or f
        except Exception as e:
            if not pkio.exception_is_not_found(e):
                raise
        return False if exists_only else None

    @classmethod
    def _lib_file_list(cls, pat, want_user_lib_dir=True, qcall=None):
        """Unsorted list of absolute paths matching glob pat

        Only works locally.
        """
        cls._assert_server_side()

        res = PKDict(
            (
                (f.basename, f)
                for f in sirepo.resource.glob_paths(
                    _TEMPLATE_RESOURCE_DIR,
                    cls.sim_type(),
                    cls.LIB_DIR,
                    pat,
                )
            )
        )
        if want_user_lib_dir:
            # lib_dir overwrites resource_dir
            res.update(
                (f.basename, f)
                for f in pkio.sorted_glob(cls._lib_file_abspath(pat, qcall))
            )
        return res.values()

    @classmethod
    def _memoize(cls, value):
        """Cache class method (no args)

        Example::

            @classmethod
            def something(cls):
                return cls._memoize(compute_something_once())

        Args:
            value (object): any object

        Returns:
            object: value
        """

        @classmethod
        def wrap(cls):
            return value

        setattr(cls, pkinspect.caller_func_name(), wrap)
        return value

    @classmethod
    def _non_analysis_fields(cls, data, model):
        """Get the non-analysis fields for model

        If the model has "analysis" fields, then return the full list of non-style fields
        otherwise returns the model name (which implies all model fields)

        Args:
            data (dict): simulation
            model (str): name of model to compute
        Returns:
            list: compute_fields fields for model or whole model
        """
        s = set(data.models.get(model, {}).keys()) - cls.ANALYSIS_ONLY_FIELDS
        if not s:
            return [model]
        return sorted(["{}.{}".format(model, x) for x in s])

    @classmethod
    def _organize_example(cls, data):
        dm = data.models
        if dm.simulation.get("isExample") and dm.simulation.folder == "/":
            dm.simulation.folder = "/Examples"

    @classmethod
    def _prepare_import_file_name_args(cls, req):
        res = PKDict(basename=os.path.basename(req.filename))
        res.purebasename, e = os.path.splitext(res.basename)
        res.ext_lower = e.lower()
        return res

    @classmethod
    def _proprietary_code_tarball(cls):
        return f"{cls.sim_type()}.tar.gz"

    @classmethod
    def _read_binary_and_save(
        cls, lib_sid_uri, basename, dst_dir, is_exe=False, sim_type=None
    ):
        p = dst_dir.join(basename)
        p.write_binary(
            cls.sim_db_client().get(lib_sid_uri, basename, sim_type=sim_type)
        )
        if is_exe:
            p.chmod(cls._EXE_PERMISSIONS)
        return p

    @classmethod
    def _sim_file_basenames(cls, data):
        return []

    @classmethod
    def _simulation_db(cls):
        cls._assert_server_side()
        from sirepo import simulation_db

        return simulation_db


_cfg = pkconfig.init(
    lib_file_resource_only=(False, bool, "used by utility programs"),
)
