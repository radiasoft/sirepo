"""Public functions from sirepo

Use this to call sirepo from other packages or Python notebooks.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template import lattice
from sirepo.template.lattice import LatticeUtil
import copy
import inspect
import py.error
import pykern.pkio
import sirepo.sim_data
import sirepo.util


class LibAdapterBase:
    """Common functionality between code specific LibAdapter implementations."""

    def __init__(self, ignore_files=None):
        m = inspect.getmodule(self)
        self._sim_data, _, self._schema = sirepo.sim_data.template_globals(m.SIM_TYPE)
        self._code_var = m.code_var
        self._ignore_files = ignore_files if ignore_files else []

    def _convert(self, data):
        def _model(model, name):
            s = self._schema.model[name]

            k = x = v = None
            try:
                for k, x in s.items():
                    t = x[1]
                    v = model[k] if k in model else x[2]
                    if t == "RPNValue":
                        t = "Float"
                        if cv.is_var_value(v):
                            model[k] = cv.eval_var_with_assert(v)
                            continue
                    if t == "Float":
                        model[k] = float(v) if v else 0.0
                    elif t == "Integer":
                        model[k] = int(v) if v else 0
            except Exception as e:
                pkdlog(
                    "model={} field={} decl={} value={} exception={}", name, k, x, v, e
                )
                raise

        cv = self._code_var(data.models.rpnVariables)
        for x in data.models.rpnVariables:
            x.value = cv.eval_var_with_assert(x.value)
        for k, v in data.models.items():
            if k in self._schema.model:
                _model(v, k)
        for x in ("elements", "commands"):
            for m in data.models[x]:
                _model(m, LatticeUtil.model_name_for_data(m))
        for bl in data.models.beamlines:
            if "positions" in bl:
                for p in bl.positions:
                    p.elemedge = cv.eval_var_with_assert(p.elemedge)
        return data

    def _verify_files(self, path, filenames):
        for f in filenames:
            if f in self._ignore_files:
                continue
            p = path.dirpath().join(f)
            assert p.check(file=True), f"file={f} missing"

    def _write_input_files(self, data, source_path, dest_dir):
        for f in set(
            LatticeUtil(data, self._schema)
            .iterate_models(
                lattice.InputFileIterator(self._sim_data, update_filenames=False),
            )
            .result,
        ):
            f = self._sim_data.lib_file_name_without_type(f)
            try:
                d = dest_dir.join(f)
                pykern.pkio.mkdir_parent_only(d)
                if f not in self._ignore_files:
                    d.mksymlinkto(source_path.dirpath().join(f), absolute=False)
            except py.error.EEXIST:
                pass


class GenerateBase:
    """Common functionality between code specific Generate implementations."""

    @property
    def util(self):
        from sirepo.template.lattice import LatticeUtil

        if not hasattr(self, "_util"):
            self._util = LatticeUtil(self.data, self._schema)
        return self._util


class Importer:
    """
    Imports a code's native files into Sirepo representation

    Args:
        sim_type (str): type of simulation (eg. 'elegant' or 'madx')
        ignore_files (list): files ignored during verification and symlink routines [None]
    """

    def __init__(self, sim_type, ignore_files=None):
        import sirepo.template

        self.__adapter = sirepo.template.import_module(sim_type).LibAdapter(
            ignore_files or []
        )

    def parse_file(self, path):
        p = pykern.pkio.py_path(path)
        with pykern.pkio.save_chdir(p.dirpath()):
            return SimData(
                self.__adapter.parse_file(p),
                p,
                self.__adapter,
            )


class SimData(PKDict):
    """Represents data of simulation"""

    def __init__(self, data, source, adapter):
        super().__init__(data)
        self.pkdel("report")
        self.__source = source
        self.__adapter = adapter

    def copy(self):
        """Allows copy.deepcopy"""
        return self.__class__(self, self.__source, self.__adapter)

    def write_files(self, dest_dir):
        """Writes files for simulation state

        Args:
            dest_dir (str or py.path): where to write files
        Returns:
            PKDict: files written (debugging only)
        """
        return self.__adapter.write_files(
            # need to make a copy, b/c generate_parameters_file modifies
            copy.deepcopy(self),
            self.__source,
            pykern.pkio.py_path(dest_dir),
        )
