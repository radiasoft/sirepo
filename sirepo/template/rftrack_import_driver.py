"""Execute a self-contained RF-Track script under the call recorder.

Stage 2 (subprocess side) of importing an arbitrary RF-Track Python script
into a Sirepo rftrack simulation (see rftrack-import-plan.md). Invoked as
`python3 -m sirepo.template.rftrack_import_driver <script_path>
<result_path>` by `rftrack_import_runner.run()`, in a fresh subprocess so a
hand-written script's crash, timeout, or heavy resource use can't affect
the Sirepo process driving the import.

Always writes a JSON result to `result_path` (see `_write_result`), and
exits 0 only when the script under import ran to completion -- the caller
should treat a non-zero exit with no readable result file as a crash this
driver itself did not survive (e.g. killed by the parent on timeout), and
treat a 0 exit as "see the result file's own status field".

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import RF_Track
import ast
import builtins
import importlib.abc
import importlib.machinery
import importlib.util
import numpy
import os.path
import pykern.pkjson
import sirepo.template.rftrack_import_recorder
import sys
import traceback
import types

#: modules the self-contained-script assumption (see rftrack-import-plan.md)
#: allows beyond the standard library, without a dependency error
_ALWAYS_ALLOWED_MODULES = frozenset(["RF_Track", "matplotlib", "numpy"])

#: skip resolving an array larger than this via accessors/args -- keeps the
#: JSON result bounded for a bunch built from a large raw particle matrix
_MAX_ARRAY_ELEMENTS = 1000


def main(script_path, result_path):
    missing = _missing_dependencies(script_path)
    if missing:
        return _write_result(
            result_path,
            PKDict(status="error", reason="missing_dependencies", missing=missing),
        )
    _stub_notebook_artifacts()
    _stub_missing_data_files()
    sirepo.template.rftrack_import_recorder.install()
    # a plain dict this driver keeps its own reference to (not
    # runpy.run_path()'s returned globals, which is unreachable once an
    # exception propagates out of the run before it returns) -- see
    # _resolve_pc_mev(), the one piece of data this needs that survives
    # only in the script's own top-level globals, nowhere RF_Track itself
    # ever sees it
    g = {"__name__": "__main__", "__file__": script_path}
    partial_error = None
    try:
        with open(script_path) as f:
            exec(compile(f.read(), script_path, "exec"), g)
    except Exception as e:
        if not sirepo.template.rftrack_import_recorder.calls():
            # nothing useful was ever captured -- a real failure, not
            # tail code this import never needed in the first place
            return _write_result(
                result_path,
                PKDict(
                    status="error",
                    reason="script_exception",
                    message=str(e),
                    traceback=traceback.format_exc(),
                ),
            )
        # tolerated, not a failure: track()/btrack()/autophase() are
        # no-ops now (see rftrack_import_recorder._NOOP_METHODS), not an
        # abort, specifically so a script can keep going past them --
        # setting up space charge, tracking the real bunch, and so on --
        # instead of losing all of that the way stopping dead at the
        # first track() call used to. Whatever now comes after is far
        # more likely to be tail code this import never needed anyway
        # (plotting a None "tracked bunch", saving files, ...) than a
        # sign the lattice/bunch/settings already captured are wrong.
        partial_error = str(e)
    return _write_result(
        result_path,
        PKDict(
            status="ok",
            calls=[
                _resolve_call(c)
                for c in sirepo.template.rftrack_import_recorder.calls()
            ],
            number_of_threads=RF_Track.cvar.number_of_threads,
            pc_mev=_resolve_pc_mev(g),
            partial_error=partial_error,
        ),
    )


def _imported_module_names(node):
    if isinstance(node, ast.Import):
        return [a.name.split(".")[0] for a in node.names]
    if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
        return [node.module.split(".")[0]]
    return []


def _is_allowed_module(name):
    return name in _ALWAYS_ALLOWED_MODULES or name in sys.stdlib_module_names


def _json_safe(value):
    if isinstance(value, (bool, int, float, str)) or value is None:
        return value
    if isinstance(value, numpy.generic):
        return value.item()
    if isinstance(value, numpy.ndarray):
        if value.size > _MAX_ARRAY_ELEMENTS:
            return PKDict(
                truncated=True, shape=list(value.shape), dtype=str(value.dtype)
            )
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    return repr(value)


def _missing_dependencies(script_path):
    with open(script_path) as f:
        tree = ast.parse(f.read(), filename=script_path)
    names = set()
    for node in ast.walk(tree):
        names.update(_imported_module_names(node))
    return sorted(
        n
        for n in names
        if not _is_allowed_module(n) and not importlib.util.find_spec(n)
    )


def _resolve_call(call):
    return PKDict(
        kind=call.kind,
        # id(), not the object itself: a live RF_Track object can't cross
        # the subprocess boundary, but the mapper (stage 4, in the parent
        # process) still needs to tell that e.g. this Volume.add record's
        # element is the very same object as an earlier Drift record --
        # id() is stable across every call recorded in this one process
        obj_id=id(call.obj),
        args=[_json_safe(a) for a in call.args],
        kwargs={k: _json_safe(v) for k, v in call.kwargs.items()},
        fields=_resolve_fields(call.obj),
        # already plain (mode: str, value: float) or None -- computed
        # against the live field array in the recorder itself, so it
        # never needs _json_safe's own array-size truncation
        rescale=call.get("rescale"),
        # already a plain int or None -- which Volume/Lattice (if any)
        # this call belongs to, so the mapper can tell a script's
        # *last* build apart from an earlier one it discarded (see
        # rftrack_import_mapper.map_elements())
        container_id=call.get("container_id"),
    )


def _resolve_fields(obj):
    """Read back whatever plain data `obj` exposes, generically.

    RF_Track objects populate their state two different ways depending on
    the class: an element (Drift, Quadrupole, ...) exposes get_*()
    accessor methods; a bunch-parameter object (Bunch6dT_Generator,
    Bunch6d_twiss) is instead a plain attribute struct the script sets
    directly (`g.species = "electron"`), with no get_*() methods at all.
    This covers both without needing a per-class field list here --
    deciding which of these fields actually matter for a given kind is a
    later stage's job, once this is back in the parent process as plain
    JSON-safe data.
    """
    res = PKDict()
    for n in sorted(dir(obj)):
        if n.startswith("_") or n in ("this", "thisown"):
            continue
        v = getattr(obj, n)
        if callable(v) and not n.startswith("get_"):
            continue
        try:
            # POSIT: RF_Track's accessors are SWIG-bound C++ methods with
            # no documented exception contract, and some (e.g. get_field)
            # take required arguments and are not valid to call with
            # none -- one incompatible accessor must not lose every
            # other one, so this catches broadly and moves on.
            res[n] = _json_safe(v() if callable(v) else v)
        except Exception:
            pass
    return res


def _resolve_pc_mev(g):
    """Read BUNCH.pc_mev straight from the just-executed script's own
    top-level globals, bypassing RF_Track entirely.

    `pc` is never actually passed to any RF_Track call for a Cathode
    bunch with no RBEND elements -- there's no execution trace to
    recover it from at all, unlike every other field this driver
    resolves (see rftrack-import-plan.md). But a script Sirepo itself
    generated always assigns a top-level `BUNCH = PKDict(pc_mev=...,
    ...)` (see parameters.py.jinja) before ever reaching any of that --
    whether or not the rest of the script got that far, or raised
    partway through tail code, `g` already has it. An arbitrary
    hand-written script simply won't define a
    `BUNCH` dict with this key at all, so this is a no-op for that case,
    not a guess -- and if the script was Sirepo's own export but the
    user hand-edited some other field before reimporting, this still
    only ever fills in `pc` specifically, never overriding anything the
    exec-based recorder/mapper path already derived from what the script
    actually does.
    """
    b = g.get("BUNCH")
    if not isinstance(b, dict):
        return None
    v = b.get("pc_mev")
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _stub_missing_data_files():
    """Don't let a missing field-map data file crash the whole import.

    A field-map element's source file was never passed to RF_Track at
    all -- the script's own `numpy.loadtxt(filename)` already loaded it
    into a plain array before ever calling `Static_Magnetic_FieldMap_1d`/
    `RF_FieldMap_1d` (see rftrack-import-plan.md's stage 3/4 notes) -- so
    if that file isn't present in this subprocess's working directory
    (always true today: nothing about the uploaded script's own data
    files is copied in), `numpy.loadtxt` raises `FileNotFoundError`
    before the RF_Track call it was leading up to ever happens, and nothing
    gets recorded at all.

    Substituting a small placeholder array instead lets the script keep
    running far enough to actually construct the field-map element, so
    the mapper still has something to build a SOLENOID/CAVITY record
    from -- recording the attempted filename (found or not) alongside it,
    in call order, is what then lets the mapper tell the generic
    `latticeImportDialog` UI (the same "missing files" prompt every other
    lattice-code importer already gets) which file that element actually
    needs.

    Also hands the loaded data's own field column (real or placeholder)
    to the recorder's `note_loadtxt_raw()`, so the very next field-map
    element construction can detect whether its rescaleMode/scaleFactor/
    maxField are recoverable (see rftrack_import_recorder._resolve_rescale)
    -- this works even against the placeholder, since its column is
    still nonzero and the detection math doesn't care which it is.
    """
    real_loadtxt = numpy.loadtxt

    def _loadtxt(fname, *args, **kwargs):
        found = os.path.exists(fname)
        t = (
            real_loadtxt(fname, *args, **kwargs)
            if found
            else numpy.array([[0.0, 0.0], [1.0, 1.0]])
        )
        sirepo.template.rftrack_import_recorder.record(
            "numpy.loadtxt", None, (str(fname),), PKDict(found=found)
        )
        if t.ndim == 2 and t.shape[1] > 1:
            sirepo.template.rftrack_import_recorder.note_loadtxt_raw(t[:, 1])
        return t

    numpy.loadtxt = _loadtxt


def _stub_notebook_artifacts():
    """Tolerate `jupyter nbconvert --to script` output.

    A notebook export calls `get_ipython().run_line_magic(...)` wherever
    the original notebook used a magic (`%matplotlib inline` is the
    common one in lattice-design notebooks); `get_ipython` only exists
    inside a real IPython kernel otherwise. Plotting the lattice is also
    common and irrelevant to the data being extracted.

    A real lattice-design notebook's own helper libraries commonly import
    matplotlib submodules this driver can't predict in advance (e.g.
    `rftrack_utils.posproc` does `import matplotlib.colors`, not just
    `matplotlib.pyplot`) -- a sys.meta_path finder that stubs out *any*
    matplotlib submodule, recursively, on first import handles all of
    them generically instead of this needing its own ever-growing list.
    Pre-registering a fixed list in sys.modules doesn't: a plain stub
    module's __getattr__ makes `from matplotlib import colors` work (it
    never raises AttributeError, so Python never even tries importing
    "matplotlib.colors" as a real submodule), but `import
    matplotlib.colors` is a dotted import -- that form always resolves
    "matplotlib.colors" via matplotlib's own __path__/finders, which a
    plain __getattr__ stub has no part in at all, regardless of what it
    returns for the name "colors".

    A stub call returning plain `None` also isn't enough on its own: a
    real plotting idiom routinely destructures or chains off the
    result (`fig, ax = plt.subplots()`; `line, = ax.plot(...)`;
    `ax.twinx().set_ylabel(...)`), and unpacking/attribute access on
    `None` raises -- see _Sink below.
    """

    def _no_op(*args, **kwargs):
        return None

    class _IPythonStub:
        def __getattr__(self, name):
            return _no_op

    class _Sink:
        """A universal no-op object: any attribute access, call, or
        indexing on it returns itself, so an arbitrary (and otherwise
        irrelevant) chain of plotting calls --
        `fig.add_subplot(...).plot(...).set_xlabel(...)`, and so on --
        keeps working instead of crashing on `None`. Also iterable as
        exactly one item, covering the common `line, = ax.plot(...)`
        idiom (a real Axes.plot() returns a list of Line2D objects) --
        `plt.subplots()` specifically needs exactly two instead, so
        that one case is special-cased in _NoOpModule below rather than
        here.
        """

        def __call__(self, *args, **kwargs):
            return self

        def __getattr__(self, name):
            return self

        def __getitem__(self, key):
            return self

        def __iter__(self):
            yield self

        def __bool__(self):
            return False

    _sink = _Sink()

    class _NoOpModule(types.ModuleType):
        def __getattr__(self, name):
            if name == "subplots":
                # fig, ax = plt.subplots(...) -- exactly two, regardless
                # of nrows/ncols (which would only change whether a real
                # `ax` is a single Axes or a grid of them -- irrelevant
                # here, since _sink already tolerates being indexed,
                # iterated, or called as if it were either)
                return lambda *a, **kw: (_sink, _sink)
            return _sink

    class _MatplotlibFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
        def find_spec(self, name, path, target=None):
            if name == "matplotlib" or name.startswith("matplotlib."):
                # is_package=True unconditionally: a stub needs to be a
                # package too, in case something imports one of *its*
                # submodules in turn (e.g. matplotlib.backends.backend_agg)
                return importlib.machinery.ModuleSpec(name, self, is_package=True)
            return None

        def create_module(self, spec):
            return _NoOpModule(spec.name)

        def exec_module(self, module):
            pass

    sys.meta_path.insert(0, _MatplotlibFinder())
    builtins.get_ipython = lambda: _IPythonStub()


def _write_result(result_path, result):
    pykern.pkjson.dump_pretty(result, filename=result_path)
    return 0 if result.status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
