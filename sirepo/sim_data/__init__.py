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


#: root directory for template resources
RESOURCE_DIR = pkio.py_path(pkresource.filename('template'))


def get_class(type_or_data):
    """Simulation data class

    Args:
        type_or_data (str or dict): simulation type or description
    Returns:
        type: simulation data operation class
    """
    if isinstance(type_or_data, dict):
        type_or_data = type_or_data['simulationType']
    return importlib.import_module('.' + type_or_data, __name__).SimData


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


class SimDataBase(object):
    ANALYSIS_ONLY_FIELDS = frozenset()

    WATCHPOINT_REPORT = 'watchpointReport'

    WATCHPOINT_REPORT_RE = re.compile('^{}(\d+)$'.format(WATCHPOINT_REPORT))

    _TEMPLATE_FIXUP = 'sim_data_template_fixup'

    @classmethod
    def compute_job_hash(cls, data, changed=None):
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
        c = PKDict(changed=False)

        def _op():
            c.changed = True
            pkcollections.unchecked_del(data, 'reportParametersHash')
            res = hashlib.md5()
            m = data['models']
            for f in sorted(
                sirepo.sim_data.get_class(data.simulationType)._compute_job_fields(data),
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
            # lib_files returns sorted list
            res.update(''.join(str(f.mtime()) for f in cls.lib_files(data)).encode())
            # this is good enough versioning, because "v" does not
            # exist in hex, and we know we only need a few numbers.
            # We don't want anything but characters, because the
            # way animation_args and other serializations of this value
            # are used.
            return 'v2' + res.hexdigest()

        try:
            # note - this is broken in this version of sirepo, added work-around
            # return data.pksetdefault(computeJobHash=_op)
            if 'computeJobHash' not in data:
                data.computeJobHash = _op()
            return data.computeJobHash
        finally:
            if changed and c.changed:
                changed()

    @classmethod
    def fixup_old_data(cls, data):
        """Update model data to latest schema

        Modifies `data` in place.

        Args:
            data (dict): simulation
        """
        raise NotImplemented()

    @classmethod
    def animation_name(cls, data):
        """Animation report

        Args:
            data (dict): simulation
        Returns:
            str: name of report
        """
        return 'animation'

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
    def lib_file_abspath(cls, files, source_lib):
        """Returns full, unique paths of simulation files

        Args:
            files (iter): lib file names
            source_lib (py.path): path to lib (simulation_lib_dir)
        Returns:
            list: py.path.local to files (duplicates removed)
        """
        return sorted(set((source_lib.join(f, abs=1) for f in files)))

    @classmethod
    def lib_files(cls, data, source_lib=None, validate_exists=True):
        """Return list of files used by the simulation

        Args:
            data (dict): sim db

        Returns:
            list: py.path.local to files
        """
        from sirepo import simulation_db

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
    def watchpoint_id(cls, report):
        m = cls.WATCHPOINT_REPORT_RE.search(report)
        if not m:
            raise RuntimeError('invalid watchpoint report name: ', report)
        return int(m.group(1))

    @classmethod
    def _force_recompute(cls):
        """Random value to force a compute_job to recompute.

        Used by `_compute_job_fields`

        Returns:
            str: random value
        """
        return sirepo.util.random_base62()

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
