# -*- coding: utf-8 -*-
"""Type-based simulation operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdexc, pkdc, pkdformat
import hashlib
import inspect
import re
import requests
import sirepo.const
import sirepo.feature_config
import sirepo.job
import sirepo.resource
import sirepo.srdb
import sirepo.template
import sirepo.util
import subprocess
import uuid

_cfg = None

#: default compute_model
_ANIMATION_NAME = "animation"

#: prefix for auth header of sim_db_file requests
_AUTH_HEADER_PREFIX = f"{sirepo.util.AUTH_HEADER_SCHEME_BEARER} "

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


def audit_proprietary_lib_files(qcall, force=False, sim_types=None):
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

    s = sirepo.feature_config.proprietary_sim_types()
    if sim_types:
        assert sim_types.issubset(
            s
        ), f"sim_types={sim_types} not a subset of proprietary_sim_types={s}"
        s = sim_types
    for t in s:
        c = get_class(t)
        if not c.proprietary_code_tarball():
            continue
        d = sirepo.srdb.proprietary_code_dir(t)
        assert d.exists(), f"{d} proprietary_code_dir must exist" + (
            "; run: sirepo setup_dev" if pkconfig.in_dev_mode() else ""
        )
        r = qcall.auth_db.model("UserRole").has_role(
            role=sirepo.auth_role.for_sim_type(t),
        )
        if r:
            _add(d, t, c)
            continue
        # SECURITY: User no longer has access so remove all artifacts
        pkio.unchecked_remove(simulation_db.simulation_dir(t, qcall=qcall))


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
    res.update(zip(s._frame_id_fields(res), v[len(_FRAME_ID_KEYS) :]))
    return res, s


class SimDataBase(object):
    ANALYSIS_ONLY_FIELDS = frozenset()

    WATCHPOINT_REPORT = "watchpointReport"

    WATCHPOINT_REPORT_RE = re.compile(r"^{}(\d+)$".format(WATCHPOINT_REPORT))

    _EXAMPLE_RESOURCE_DIR = "examples"

    _EXE_PERMISSIONS = 0o700

    _LIB_RESOURCE_DIR = "lib"

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
    def delete_sim_file(cls, sim_id, basename):
        return cls._delete_sim_db_file(cls._sim_file_uri(sim_id, basename))

    @classmethod
    def does_api_reply_with_file(cls, api, method):
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
    def react_format_data(cls, data):
        pass

    @classmethod
    def react_unformat_data(cls, data):
        pass

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
            + [str(m.get(k)) for k in cls._frame_id_fields(frame_args)],
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
        Returns:
            object: py.path.local to files (duplicates removed) OR py.path.local
        """
        p = cls._lib_file_abspath(basename, data=data, qcall=qcall)
        if p:
            return p
        from sirepo import auth

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
        cls._assert_server_side()
        return bool(cls._lib_file_abspath(basename, qcall=qcall))

    @classmethod
    def lib_file_in_use(cls, data, basename):
        """Check if file in use by simulation

        Args:
            data (dict): simulation
            basename (str): to check
        Returns:
            bool: True if `basename` in use by `data`
        """
        return any(f for f in cls.lib_file_basenames(data) if f == basename)

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
    def lib_file_resource_path(cls, path):
        return sirepo.resource.file_path(
            _TEMPLATE_RESOURCE_DIR,
            cls.sim_type(),
            cls._LIB_RESOURCE_DIR,
            path,
        )

    @classmethod
    def lib_file_write_path(cls, basename, qcall=None):
        cls._assert_server_side()
        from sirepo import simulation_db

        return simulation_db.simulation_lib_dir(cls.sim_type(), qcall=qcall).join(
            basename
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
        cls._assert_server_side()
        from sirepo import simulation_db

        t = simulation_db.simulation_lib_dir(cls.sim_type(), qcall=qcall)
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
        from sirepo import simulation_db

        if isinstance(obj, pkconfig.STRING_TYPES):
            res = obj
        elif isinstance(obj, dict):
            res = obj.get("simulationId") or obj.pknested_get(
                "models.simulation.simulationId"
            )
        else:
            raise AssertionError("obj={} is unsupported type={}", obj, type(obj))
        return simulation_db.assert_sid(res)

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
    def proprietary_code_tarball(cls):
        return None

    @classmethod
    def proprietary_code_lib_file_basenames(cls):
        return []

    @classmethod
    def put_sim_file(cls, sim_id, file_path, basename):
        return cls._put_sim_db_file(file_path, cls._sim_file_uri(sim_id, basename))

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
        from sirepo import simulation_db

        return cls._memoize(simulation_db.get_schema(cls.sim_type()))

    @classmethod
    def sim_file_basenames(cls, data):
        return cls._sim_file_basenames(data)

    @classmethod
    def sim_files_to_run_dir(cls, data, run_dir):
        for b in cls.sim_file_basenames(data):
            cls._sim_file_to_run_dir(
                data.models.simulation.simulationId,
                b.basename,
                run_dir,
                is_exe=b.get("is_exe", False),
            )

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
    def _assert_server_side(cls):
        assert (
            not _cfg.lib_file_uri
        ), f"method={pkinspect.caller()} may only be called on server"

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
    def _delete_sim_db_file(cls, uri):
        _request(
            "DELETE",
            _cfg.supervisor_sim_db_file_uri + uri,
        ).raise_for_status()

    @classmethod
    def _init_models(cls, models, names=None, dynamic=None):
        if names:
            names = set(list(names) + ["simulation"])
        for n in names or cls.schema().model:
            cls.update_model_defaults(
                models.setdefault(n, PKDict()),
                n,
                dynamic=dynamic,
            )

    @classmethod
    def _lib_file_abspath(cls, basename, data=None, qcall=None):
        import sirepo.simulation_db

        if _cfg.lib_file_uri:
            # In agent
            if basename in _cfg.lib_file_list:
                # User generated lib file
                p = pkio.py_path(basename)
                r = _request("GET", _cfg.lib_file_uri + basename)
                r.raise_for_status()
                p.write_binary(r.content)
                return p
        elif not _cfg.lib_file_resource_only:
            # Command line utility or server
            f = sirepo.simulation_db.simulation_lib_dir(
                cls.sim_type(),
                qcall=qcall,
            ).join(basename)
            if f.check(file=True):
                return f
        try:
            # Lib file distributed with build
            f = cls.lib_file_resource_path(basename)
            if f.check(file=True):
                return f
        except Exception as e:
            if not pkio.exception_is_not_found(e):
                raise
        return None

    @classmethod
    def _lib_file_list(cls, pat, want_user_lib_dir=True, qcall=None):
        """Unsorted list of absolute paths matching glob pat

        Only works locally.
        """
        cls._assert_server_side()
        from sirepo import simulation_db

        res = PKDict(
            (
                (f.basename, f)
                for f in sirepo.resource.glob_paths(
                    _TEMPLATE_RESOURCE_DIR,
                    cls.sim_type(),
                    cls._LIB_RESOURCE_DIR,
                    pat,
                )
            )
        )
        if want_user_lib_dir:
            # lib_dir overwrites resource_dir
            res.update(
                (f.basename, f)
                for f in pkio.sorted_glob(
                    simulation_db.simulation_lib_dir(cls.sim_type(), qcall=qcall).join(
                        pat
                    ),
                )
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

        setattr(
            cls,
            inspect.currentframe().f_back.f_code.co_name,
            wrap,
        )
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
    def _proprietary_code_tarball(cls):
        return f"{cls.sim_type()}.tar.gz"

    @classmethod
    def _put_sim_db_file(cls, file_path, uri):
        _request(
            "PUT",
            _cfg.supervisor_sim_db_file_uri + uri,
            data=pkio.read_binary(file_path),
        ).raise_for_status()

    @classmethod
    def _sim_file_basenames(cls, data):
        return []

    @classmethod
    def _sim_db_file_to_run_dir(cls, uri, run_dir, is_exe=False):
        p = run_dir.join(uri.split("/")[-1])
        r = _request("GET", _cfg.supervisor_sim_db_file_uri + uri)
        r.raise_for_status()
        p.write_binary(r.content)
        if is_exe:
            p.chmod(cls._EXE_PERMISSIONS)
        return p

    @classmethod
    def _sim_file_to_run_dir(cls, sim_id, basename, run_dir, is_exe=False):
        return cls._sim_db_file_to_run_dir(
            cls._sim_file_uri(sim_id, basename),
            run_dir,
            is_exe=is_exe,
        )

    @classmethod
    def _sim_file_uri(cls, sim_id, basename):
        from sirepo import simulation_db

        return simulation_db.sim_db_file_uri(
            cls.sim_type(),
            sim_id,
            basename,
        )


class SimDbFileNotFound(Exception):
    """A sim db file could not be found"""

    pass


def _request(method, uri, data=None):
    r = requests.request(
        method,
        uri,
        data=data,
        verify=sirepo.job.cfg().verify_tls,
        headers=PKDict(
            {
                sirepo.util.AUTH_HEADER: _AUTH_HEADER_PREFIX
                + _cfg.supervisor_sim_db_file_token,
            }
        ),
    )
    if method == "GET" and r.status_code == 404:
        raise SimDbFileNotFound(f"uri={uri} not found")
    return r


_cfg = pkconfig.init(
    lib_file_resource_only=(False, bool, "used by utility programs"),
    lib_file_list=(
        None,
        lambda v: pkio.read_text(v).splitlines(),
        "directory listing of remote lib",
    ),
    lib_file_uri=(None, str, "where to get files from when remote"),
    supervisor_sim_db_file_uri=(
        None,
        str,
        "where to get/put simulation db files from/to supervisor",
    ),
    supervisor_sim_db_file_token=(
        None,
        str,
        "token for supervisor simulation file access",
    ),
)
