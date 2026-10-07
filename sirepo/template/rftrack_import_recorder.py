"""Record RF_Track constructor and lattice-building calls for script import.

Stage 1 of importing an arbitrary, self-contained RF-Track Python script
into a Sirepo rftrack simulation (see rftrack-import-plan.md). `install()`
replaces the element/bunch classes and `Volume.add`/`Lattice.append` on the
real `RF_Track` module with recording wrappers, so that when the script
under import is exec'd against this same `RF_Track` module, every call
that builds the lattice or the bunch is captured in order, with the live
RF_Track object attached for later introspection (stage 3: resolve).

Must be installed before the script under import is exec'd, since both
`import RF_Track as rft` and `from RF_Track import Quadrupole` resolve
against whatever is already in `sys.modules["RF_Track"]` at that point.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import RF_Track
import numpy

#: RF_Track classes that construct a lattice element; recorded by
#: wrapping __init__, since Volume has no generic "all elements in
#: original order" accessor -- Volume.add (below) is what recovers order
#: and position, this is what recovers each element's own kind and args
_ELEMENT_CLASS_NAMES = (
    "Corrector",
    "Drift",
    "Pillbox_Cavity",
    "Quadrupole",
    "RF_FieldMap_1d",
    "Screen",
    "Solenoid",
    "Static_Magnetic_FieldMap_1d",
)

#: the element classes whose first constructor arg is a field array that
#: may have just been produced by rescaling the most recently loaded raw
#: field-map column -- see note_loadtxt_raw()/_resolve_rescale()
_FIELD_MAP_CLASS_NAMES = ("RF_FieldMap_1d", "Static_Magnetic_FieldMap_1d")

#: RF_Track classes that hold bunch/distribution parameters, constructed
#: with no args and then populated via plain attribute assignment (e.g.
#: `g = rft.Bunch6dT_Generator(); g.species = "electron"`) -- recording the
#: constructor call only identifies which one was used; the attribute
#: values are read back by stage 3 after the script has finished running
_BUNCH_PARAMETER_CLASS_NAMES = (
    "Bunch6d_twiss",
    "Bunch6dT_Generator",
)

#: RF_Track classes that construct the final bunch object passed to
#: Volume.track(); args are either (parameter_object, population) or a
#: raw per-particle numpy matrix, depending on which the script used
_BUNCH_CLASS_NAMES = (
    "Bunch6d",
    "Bunch6dT",
)

#: RF_Track names that are plain functions, not classes, despite looking
#: like an element/bunch constructor -- each is a SWIG overload-dispatch
#: factory with no __init__ to wrap, so it needs the function wrapper
#: instead of the class wrapper. RBend(...) in particular returns an
#: RF_Track.SBend instance with full get_angle()/get_length() accessors,
#: contrary to this plan's earlier assumption (based on checking
#: dir(RF_Track.RBend) itself, the factory function, rather than what it
#: returns) that RBend elements have no accessors at all.
_FUNCTION_NAMES = (
    "Bunch6d_QR",
    "RBend",
)

#: RF_Track space-charge engine classes -> any of their own methods
#: (beyond __init__) that matter for simulationSettings -- e.g.
#: SpaceCharge_PIC_FreeSpace(nx, ny, nz) then .set_smooth()/.set_mirror()
#: -- rft.cvar.SC_engine (where a script assigns the constructed engine)
#: is a process-global, read back post-construction as a type-erased
#: base SpaceCharge with none of these, so the only way to recover them
#: is capturing the calls that built it as they happen
_SPACE_CHARGE_CLASS_METHODS = PKDict(
    SpaceCharge_P2P=(),
    SpaceCharge_PIC_FreeSpace=("set_smooth", "set_mirror"),
)

#: container class name -> the one method on it that places an element
#: into the lattice, in order, with its position/offsets
_CONTAINER_METHODS = PKDict(Lattice="append", Volume="add")

#: container class name -> any other methods on it (beyond the placement
#: one above) to record and still actually call -- Volume.set_s0()/
#: set_s1() set the tracking range, needed for simulationSettings
_RECORDED_METHODS = PKDict(Volume=("set_s0", "set_s1"))

#: container class name -> plain attribute names to record on assignment
#: (also still actually assigned) -- Volume.sc_dt_mm is a plain
#: attribute, not a method call, and is the one Volume-level setting
#: with a schema field that isn't also a hardcoded literal in the
#: generated script (odeint_algorithm/dt_mm/tt_dt_mm/verbosity are)
_RECORDED_ATTRS = PKDict(Volume=("sc_dt_mm",))

#: Volume/Lattice.track()/autophase()/btrack() -- each arbitrarily
#: expensive, and completely unnecessary for import, which only wants
#: the lattice/bunch *structure* that's already fully built by the time
#: a script calls any of them; all three are recorded and turned into
#: harmless no-ops instead of actually running.
#:
#: track() used to abort the whole script right here (raising
#: TrackingSkipped), on the assumption that nothing useful ever follows
#: a real generated script's own, single, final track() call -- true
#: for a script Sirepo itself generates, false for a real hand-written
#: exploratory notebook (see rftrack-import-plan.md): one real example
#: calls track() on a cheap reference bunch just to verify autophase
#: worked, *before* setting up space charge and tracking the real
#: bunch -- aborting there discarded all of that. A script that
#: rebuilds a second Volume/Lattice this way instead of reusing the
#: first is unsupported outright (see map_elements() in
#: rftrack_import_mapper.py), rather than this guessing which build the
#: user meant; the driver separately tolerates a crash in whatever
#: unrelated tail code (plotting, saving, ...) a no-op'd track() no
#: longer prevents from running (see rftrack_import_driver.main()).
_NOOP_METHODS = ("autophase", "btrack", "track")

#: real classes/functions captured once at module load, before any
#: patching, so install() always wraps from the true originals and is
#: safe to call more than once in the same process
_ORIGINAL_CLASSES = PKDict(
    {
        n: getattr(RF_Track, n)
        for n in _ELEMENT_CLASS_NAMES
        + _BUNCH_PARAMETER_CLASS_NAMES
        + _BUNCH_CLASS_NAMES
        + tuple(_SPACE_CHARGE_CLASS_METHODS)
    }
)
_ORIGINAL_CONTAINERS = PKDict({n: getattr(RF_Track, n) for n in _CONTAINER_METHODS})
_ORIGINAL_FUNCTIONS = PKDict({n: getattr(RF_Track, n) for n in _FUNCTION_NAMES})

_calls = []

#: the raw (pre-rescale) field-map column most recently passed to
#: note_loadtxt_raw(), waiting to be consumed by whichever field-map
#: element construction happens next -- see _resolve_rescale()
_last_loadtxt_raw = None


def calls():
    """Return the calls recorded so far, in call order.

    Returns:
        list: PKDict(kind, obj, args, kwargs) per call
    """
    return list(_calls)


def install():
    """Replace RF_Track's classes with recording wrappers.

    Discards any previously recorded calls, so this also serves as the
    reset point between separate import attempts in the same process.
    """
    reset()
    for n, c in _ORIGINAL_CLASSES.items():
        setattr(
            RF_Track,
            n,
            _wrap_class(
                c,
                n,
                extra_methods=_SPACE_CHARGE_CLASS_METHODS.get(n, ()),
                detect_rescale=n in _FIELD_MAP_CLASS_NAMES,
            ),
        )
    for n, f in _ORIGINAL_FUNCTIONS.items():
        setattr(RF_Track, n, _wrap_function(f, n))
    for n, m in _CONTAINER_METHODS.items():
        setattr(
            RF_Track,
            n,
            _wrap_container(
                _ORIGINAL_CONTAINERS[n],
                m,
                recorded_methods=_RECORDED_METHODS.get(n, ()),
                recorded_attrs=_RECORDED_ATTRS.get(n, ()),
            ),
        )


def note_loadtxt_raw(raw):
    """Record the just-loaded raw field-map column, for rescale detection.

    Called by the driver's `numpy.loadtxt()` wrapper with the live array
    (before stage 2's JSON-safe conversion, which would truncate an
    array over its size limit) -- consumed once, by whichever field-map
    element construction is recorded next (see _resolve_rescale()), then
    discarded either way.
    """
    global _last_loadtxt_raw
    _last_loadtxt_raw = raw


def record(kind, obj, args, kwargs):
    """Record a call that isn't an RF_Track class/function construction.

    For anything the driver itself wraps outside of `install()` -- e.g.
    the script's own `numpy.loadtxt()` call to load a field-map data file
    -- but that still needs to appear in `calls()` in its correct
    position relative to the RF_Track calls around it, for the mapper
    (stage 4) to later correlate against.
    """
    _record(kind, obj, args, kwargs)


def reset():
    """Discard any calls recorded so far, without undoing install()."""
    global _last_loadtxt_raw
    _calls.clear()
    _last_loadtxt_raw = None


def _record(kind, obj, args, kwargs, rescale=None, container_id=None):
    _calls.append(
        PKDict(
            kind=kind,
            obj=obj,
            args=args,
            kwargs=kwargs,
            rescale=rescale,
            container_id=container_id,
        )
    )


def _resolve_rescale(final):
    """Recover both possible rescale values from the most recently
    loaded raw field-map column (see note_loadtxt_raw()), without
    guessing which mode actually produced `final`.

    `final` is the live field array a field-map element was just
    constructed with. Both rescale modes reduce to one uniform scalar
    multiply of the raw array -- "factor" mode (`field * scale_factor`)
    literally is one, and "peak" mode (`field / max(abs(field)) *
    target_field`) collapses to the same shape, since `max(abs(field))`
    is a single scalar computed once over the whole array, not per
    element. That means final[i]/raw[i] is *always* constant regardless
    of which mode ran -- there is no output-only test that tells the two
    apart (ratio == scaleFactor if "factor" was used; ratio ==
    target_field/max(abs(raw)) if "peak" was used -- indistinguishable).

    What's still recoverable: both numbers a caller would need *assuming*
    one mode or the other -- `ratio` (exactly scaleFactor, if "factor")
    and `peak` (exactly target_field, if "peak" -- note max(abs(final))
    always equals this regardless of which mode actually ran, so it's
    free either way). Deciding which one to surface as truth (e.g. by
    element type) is the mapper's job, not this function's.

    The one thing this function *does* still validate: that final/raw
    actually is a uniform multiple at all -- confirming this element's
    construction really followed the numpy.loadtxt() call immediately
    before it the way the generated script's own `_load_field_map()`
    does, not some unrelated array from an arbitrary script that doesn't
    follow that convention.

    Returns:
        PKDict: `ratio` and `peak` (see above), or None if no loadtxt
            call preceded this construction, or the two arrays don't
            line up at all (shape mismatch, or not a uniform multiple)
    """
    raw = _take_loadtxt_raw()
    if raw is None:
        return None
    f = numpy.asarray(final, dtype=float)
    if f.shape != raw.shape:
        return None
    nonzero = raw != 0
    if not nonzero.any():
        return None
    ratio = f[nonzero] / raw[nonzero]
    if not numpy.allclose(ratio, ratio[0]):
        return None
    return PKDict(ratio=float(ratio[0]), peak=float(numpy.max(numpy.abs(f))))


def _take_loadtxt_raw():
    global _last_loadtxt_raw
    raw = _last_loadtxt_raw
    _last_loadtxt_raw = None
    return raw


def _wrap_class(real_class, kind, extra_methods=(), detect_rescale=False):
    def _init(self, *args, **kwargs):
        # not super().__init__(): a zero-arg super() relies on a
        # __class__ cell that only a textual `class` statement sets up;
        # a class built dynamically via type() has no such cell
        real_class.__init__(self, *args, **kwargs)
        _record(
            kind,
            self,
            args,
            kwargs,
            rescale=_resolve_rescale(args[0]) if detect_rescale and args else None,
        )

    overrides = {"__init__": _init}
    for n in extra_methods:
        overrides[n] = _make_recorded_method(real_class, n, kind=kind)
    return type(real_class.__name__, (real_class,), overrides)


def _wrap_container(
    real_class, placement_method, recorded_methods=(), recorded_attrs=()
):
    def _make_placement_wrapper():
        real_method = getattr(real_class, placement_method)

        def _wrapped(self, element, *args, **kwargs):
            # container_id=id(self): the only way map_elements() (see
            # rftrack_import_mapper.py) can tell whether a script built
            # more than one Volume/Lattice -- unsupported, since there's
            # no reliable way to guess which one the user meant
            _record(
                f"{real_class.__name__}.{placement_method}",
                element,
                args,
                kwargs,
                container_id=id(self),
            )
            return real_method(self, element, *args, **kwargs)

        return _wrapped

    def _make_noop_wrapper(method_name):
        def _wrapped(self, *args, **kwargs):
            # obj=None, not self: stage 2's driver reflects over every
            # get_*() accessor it finds on a recorded call's object, and
            # a Volume/Lattice that was never actually tracked (the whole
            # point of skipping this call) segfaults on several of its
            # own accessors (e.g. get_bunch_at_s1(), get_transport_table())
            # that assume a completed track() already ran -- unlike an
            # element's accessors, which stay safe to probe even unused
            _record(f"{real_class.__name__}.{method_name}", None, args, kwargs)
            return None

        return _wrapped

    overrides = {placement_method: _make_placement_wrapper()}
    for n in _NOOP_METHODS:
        if hasattr(real_class, n):
            overrides[n] = _make_noop_wrapper(n)
    for n in recorded_methods:
        overrides[n] = _make_recorded_method(real_class, n)
    if recorded_attrs:
        real_setattr = real_class.__setattr__

        def _setattr(self, name, value):
            if name in recorded_attrs:
                _record(f"{real_class.__name__}.{name}", None, (value,), {})
            real_setattr(self, name, value)

        overrides["__setattr__"] = _setattr
    return type(real_class.__name__, (real_class,), overrides)


def _make_recorded_method(real_class, method_name, kind=None):
    """A method override that records every call (obj=None -- see
    _wrap_container's _make_noop_wrapper for why self is never exposed
    here) and then actually performs it.
    """
    real_method = getattr(real_class, method_name)
    k = f"{kind or real_class.__name__}.{method_name}"

    def _wrapped(self, *args, **kwargs):
        _record(k, None, args, kwargs)
        return real_method(self, *args, **kwargs)

    return _wrapped


def _wrap_function(real_function, kind):
    def _wrapped(*args, **kwargs):
        res = real_function(*args, **kwargs)
        _record(kind, res, args, kwargs)
        return res

    return _wrapped
