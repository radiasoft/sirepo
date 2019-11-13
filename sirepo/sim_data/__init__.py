# -*- coding: utf-8 -*-
u"""Type-based simulation operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern import pkjson
from pykern import pkresource
from pykern.pkdebug import pkdp
import hashlib
import importlib
import inspect
import re
import sirepo.util
import sirepo.template


#: root directory for template resources
RESOURCE_DIR = pkio.py_path(pkresource.filename('template'))

#: default compute_model
_ANIMATION_NAME = 'animation'

#: use to separate components of job_id
_JOB_ID_SEP = '-'

_MODEL_RE = re.compile(r'^[\w-]+$')

_IS_PARALLEL_RE = re.compile('animation', re.IGNORECASE)

#: separates values in frame id
_FRAME_ID_SEP = '*'

#: common keys to frame id followed by code-specific values
_FRAME_ID_KEYS = (
    'frameIndex',
    # computeModel when passed from persistent/parallel
    # analysisModel when passe from transient/sequential
    # sim_data.compute_model() is idempotent to this.
    'frameReport',
    'simulationId',
    'simulationType',
    'computeJobHash',
    'computeJobStart',
)

def get_class(type_or_data):
    """Simulation data class

    Args:
        type_or_data (str or dict): simulation type or description
    Returns:
        type: simulation data operation class
    """
    return importlib.import_module(
        '.' + sirepo.template.assert_sim_type(
            type_or_data['simulationType'] if isinstance(
                type_or_data,
                dict,
            ) else type_or_data
        ),
        __name__,
    ).SimData


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
    res = PKDict(zip(_FRAME_ID_KEYS, v[:len(_FRAME_ID_KEYS)]))
    res.frameIndex = int(res.frameIndex)
    res.computeJobStart = int(res.computeJobStart)
    s = get_class(res.simulationType)
    s.frameReport = s.parse_model(res)
    s.simulationId = s.parse_sid(res)
#TODO(robnagler) validate these
    res.update(zip(s._frame_id_fields(res), v[len(_FRAME_ID_KEYS):]))
    return res, s


class SimDataBase(object):

    ANALYSIS_ONLY_FIELDS = frozenset()

    WATCHPOINT_REPORT = 'watchpointReport'

    WATCHPOINT_REPORT_RE = re.compile('^{}(\d+)$'.format(WATCHPOINT_REPORT))

    _TEMPLATE_FIXUP = 'sim_data_template_fixup'

    @classmethod
    def compute_job_hash(cls, data):
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
        m = data['models']
        res = hashlib.md5()
        for f in sorted(
            sirepo.sim_data.get_class(data.simulationType)._compute_job_fields(
                data,
                data.report,
                cls.compute_model(data),
            ),
        ):
            # assert isinstance(f, pkconfig.STRING_TYPES), \
            #     'value={} not a string_type'.format(f)
            #TODO(pjm): work-around for now
            if isinstance(f, pkconfig.STRING_TYPES):
                x = f.split('.')
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
        # lib_files already returns sorted list
        res.update(''.join(str(f.mtime()) for f in cls.lib_files(data)).encode())
        return res.hexdigest()

    @classmethod
    def compute_model(cls, model_or_data):
        """Compute model for this model_or_data

        Args:
            model_or_data (): analysis model
        Returns:
            str: name of compute model for report
        """
        if model_or_data is None:
            # Only called in a few places (jspec & elegant)
            # and this preserves old behavior.
            return _ANIMATION_NAME
        m = cls.parse_model(model_or_data)
        d = model_or_data if isinstance(model_or_data, dict) else None
        #TODO(robnagler) is this necesary since m is parsed?
        return cls.parse_model(cls._compute_model(m, d))

    @classmethod
    def fixup_old_data(cls, data):
        """Update model data to latest schema

        Modifies `data` in place.

        Args:
            data (dict): simulation
        """
        raise NotImplemented()

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
        assert response.frameCount > index
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
                str(response.computeJobStart),
            ] + [str(m.get(k)) for k in cls._frame_id_fields(frame_args)],
        )

    @classmethod
    def is_file_used(cls, data, filename):
        """Check if file in use by simulation

        Args:
            data (dict): simulation
            filename (str): to check
        Returns:
            bool: True if `filename` in use by `data`
        """
        return any(f for f in cls.lib_files(data, validate_exists=False) if f.basename == filename)

    @classmethod
    def is_parallel(cls, data):
        """Is this report a parallel (long) simulation?

        Args:
            data (dict): report and models

        Returns:
            bool: True if parallel job
        """
        return bool(_IS_PARALLEL_RE.search(cls.compute_model(data)))


    @classmethod
    def is_watchpoint(cls, name):
        return cls.WATCHPOINT_REPORT in name

    @classmethod
    def lib_file_basename(cls, path, file_type):
        """Strip the file type prefix

        See `lib_file_name` which prefixes with ``model-field.``

        Args:
            path (py.path): path to file
            file_type (str): type of file being searched for
        Returns:
            str: basename without type prefix
        """
        return path.basename[len(file_type) + 1:]

    @classmethod
    def lib_file_name(cls, model_name, field, value):
        return '{}-{}.{}'.format(model_name, field, value)

    @classmethod
    def lib_file_abspath(cls, files_or_file, source_lib=None):
        """Returns full, unique paths of simulation files

        Args:
            files_or_fil (iter): lib file names iterable or just one file
            source_lib (py.path): path to lib (simulation_lib_dir)
        Returns:
            object: py.path.local to files (duplicates removed) OR py.path.local
        """
        from sirepo import simulation_db

        if not source_lib:
            source_lib = simulation_db.simulation_lib_dir(cls.sim_type())
        if isinstance(files_or_file, pkconfig.STRING_TYPES):
            return source_lib.join(files_or_file, abs=1)
        return sorted(set((source_lib.join(f, abs=1) for f in files_or_file)))

    @classmethod
    def lib_files(cls, data, source_lib=None, run_dir=None, validate_exists=True):
        """Return list of files used by the simulation

        Args:
            data (dict): sim db

        Returns:
            list: py.path.local to files
        """
        from sirepo import simulation_db

        if run_dir:
            assert not source_lib
            source_lib = simulation_db.lib_dir_from_sim_dir(run_dir)
        res = []
        for f in cls.lib_file_abspath(
            cls._lib_files(data),
            source_lib or simulation_db.simulation_lib_dir(cls.sim_type()),
        ):
            res.append(f)
            if f.check(file=True):
                continue
            r = cls.resource_path(f.basename)
            if not r.check(file=True):
                if validate_exists:
                    raise sirepo.util.UserAlert(
                        'Simulation library file "{}" does not exist'.format(f.basename),
                        'file={} not found, and no resource={}',
                        f,
                        r,
                    )
                continue
            pkio.mkdir_parent_only(f)
            r.copy(f)
        return res

    @classmethod
    def lib_files_copy(cls, data, source, target, symlink=False):
        """Copy auxiliary files to target

        Args:
            data (dict): simulation db
            source (py.path): source directory
            target (py.path): destination directory
            symlink (bool): if True, symlink, don't copy
        """
        assert source
        for s in cls.lib_files(data, source):
            t = target.join(s.basename)
            pkio.mkdir_parent_only(t)
            if symlink:
                t.mksymlinkto(s, absolute=False)
            else:
                s.copy(t)

    @classmethod
    def lib_files_for_type(cls, file_type):
        """Return sorted list of files which match `file_type`

        Args:
            file_type (str): in the format of ``model-field``
        Returns:
            list: sorted list of files stripped of file_type
        """
        from sirepo import simulation_db

        res = []
        d = simulation_db.simulation_lib_dir(cls.sim_type())
        for f in pkio.sorted_glob(d.join('{}.*'.format(file_type))):
            if f.check(file=1):
                res.append(cls.lib_file_basename(f, file_type))
        return sorted(res)

    @classmethod
    def model_defaults(cls, name):
        """Returns a set of default model values from the schema."""
        res = pkcollections.Dict()
        for f, d in cls.schema().model[name].items():
            if len(d) >= 3 and d[2] is not None:
                res[f] = d[2]
        return res

    @classmethod
    def parse_jid(cls, data):
        """A Job is a tuple of user, sid, and compute_model.

        A jid is words and dashes.

        Args:
            data (dict): extract sid and compute_model
        Returns:
            str: unique name (treat opaquely)
        """
        import sirepo.auth

        return _JOB_ID_SEP.join((
            sirepo.auth.logged_in_user(),
            cls.parse_sid(data),
            cls.compute_model(data),
        ))

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
            res = obj.get('frameReport') or obj.get('report')
        else:
            raise AssertionError('obj={} is unsupported type={}', obj, type(obj))
        assert res and _MODEL_RE.search(res), \
            'invalid model={} from obj={}'.format(res, obj)
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
            res = obj.get('simulationId') or obj.pknested_get('models.simulation.simulationId')
        else:
            raise AssertionError('obj={} is unsupported type={}', obj, type(obj))
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
    def resource_dir(cls):
        return cls._memoize(RESOURCE_DIR.join(cls.sim_type()))

    @classmethod
    def resource_files(cls):
        """Files to copy for a new user

        Returns:
            list: path of resource files
        """
        return []

    @classmethod
    def resource_glob(cls, pattern):
        """Match `pattern` in `resource_dir`

        Returns:
            patter: absolute path to folder
        """
        return pkio.sorted_glob(cls.resource_path(pattern))

    @classmethod
    def resource_path(cls, filename):
        """Static resource (package_data) files for simulation

        Returns:
            py.path.local: absolute path to folder
        """
        return cls.resource_dir().join(filename)

    @classmethod
    def schema(cls):
        from sirepo import simulation_db

        return cls._memoize(simulation_db.get_schema(cls.sim_type()))

    @classmethod
    def sim_type(cls):
        return cls._memoize(pkinspect.module_basename(cls))

    @classmethod
    def template_fixup_get(cls, data):
        if data.get(cls._TEMPLATE_FIXUP):
            del data[cls._TEMPLATE_FIXUP]
            return True
        return False

    @classmethod
    def update_model_defaults(cls, model, name, dynamic=None):
        defaults = cls.model_defaults(name)
        if dynamic:
            defaults.update(dynamic(name))
        for f in defaults:
            if f not in model:
                model[f] = defaults[f]

    @classmethod
    def want_browser_frame_cache(cls):
        return True

    @classmethod
    def watchpoint_id(cls, report):
        m = cls.WATCHPOINT_REPORT_RE.search(report)
        if not m:
            raise RuntimeError('invalid watchpoint report name: ', report)
        return int(m.group(1))

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
            str: random value
        """
        return sirepo.util.random_base62()

    @classmethod
    def _frame_id_fields(cls, frame_args):
        """Schema specific frame_id fields"""
        f = cls.schema().frameIdFields
        r = frame_args.frameReport
        return f[r] if r in f else f[cls.compute_model(r)]

    @classmethod
    def _init_models(cls, models, names=None, dynamic=None):
        for n in names or cls.schema().model:
            cls.update_model_defaults(
                models.setdefault(n, pkcollections.Dict()),
                n,
                dynamic=dynamic,
            )

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
        return ['{}.{}'.format(model, x) for x in s]

    @classmethod
    def _organize_example(cls, data):
        dm = data.models
        if 'isExample' in dm.simulation and dm.simulation.isExample:
            if dm.simulation.folder == '/':
                dm.simulation.folder = '/Examples'

    @classmethod
    def _template_fixup_set(cls, data):
        data[cls._TEMPLATE_FIXUP] = True


def _init():
    global cfg
    cfg = pkconfig.init(
        job_file_uri=(None, str, 'where to get files from'),
    )
