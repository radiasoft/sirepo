"""Map resolved RF_Track script-import calls onto Sirepo's rftrack schema.

Stage 4 of importing an arbitrary RF-Track Python script into a Sirepo
rftrack simulation (see rftrack-import-plan.md): the exact inverse of
`_element_spec()`/`_field_map_spec()`/`_bunch_spec()` in
`sirepo/template/rftrack.py`, given the JSON-safe result
`rftrack_import_runner.run()` returns.

`map_elements()` produces a flat list with `elemedge` on each element
directly, rather than the `elements`/`beamlines[].positions` split
`sirepo.template.lattice.LatticeUtil` actually stores -- there is only
ever one beamline right after a fresh import, so that split is a
mechanical follow-up for whichever code wires this into
`stateful_compute_import_file`, not a decision this stage needs to make.

`map_bunch()` only covers a cathode-emission bunch (a Bunch6dT_Generator)
-- a Twiss or FromFile bunch needs a field mapping this stage hasn't
verified yet.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import math
import os.path
import sirepo.sim_data

#: the two RF_Track calls that place an already-constructed element into
#: the lattice, in order, with its position/misalignment
_CONTAINER_KINDS = frozenset(["Lattice.append", "Volume.add"])

#: default aperture half-width/height, matching _ELEMENT's schema default
_DEFAULT_APERTURE = 0.015

#: Bunch6dT_Generator's `species` attribute -> schema's `particle`, the
#: inverse of rftrack.py's _CATHODE_SPECIES
_SPECIES_TO_PARTICLE = PKDict(
    electrons="electron", positrons="positron", protons="proton"
)


def map_bunch(calls):
    """Build `data.models.beam` fields from a recorded cathode-emission
    bunch generator.

    Args:
        calls (list): PKDict(kind, obj_id, args, kwargs, fields) per call,
            exactly as `rftrack_import_runner.run()` returns in `calls`

    Returns:
        PKDict: `data.models.beam` fields, or None if no recognized bunch
            generator was recorded (e.g. a Twiss or FromFile bunch,
            neither of which this stage maps yet)
    """
    g = _first(calls, "Bunch6dT_Generator")
    if g is None:
        return None
    f = g.fields
    b = _first(calls, "Bunch6dT")
    return PKDict(
        particle=_SPECIES_TO_PARTICLE.get(f.get("species"), f.get("species")),
        charge_nC=f.get("q_total"),
        cutoffT=f.get("c_sig_t"),
        cutoffX=f.get("c_sig_x"),
        cutoffY=f.get("c_sig_y"),
        ePhoton=f.get("e_photon"),
        flatTopLength=f.get("lt"),
        noiseReduc="1" if f.get("noise_reduc") else "0",
        # not f.get("np"): BUNCH.np is never set onto the generator at
        # all (matching rftrack.py's own build_bunch()) -- it's only
        # ever the population count passed as Bunch6dT(g, population)'s
        # second arg
        np=b.args[1] if b and len(b.args) > 1 else None,
        phiEff=f.get("phi_eff"),
        riseTime=f.get("rt"),
        sigX=f.get("sig_x"),
    )


def map_elements(calls):
    """Build one Sirepo element dict per `Volume.add`/`Lattice.append`
    record, in call order, with `elemedge` set directly on each (see the
    module docstring for why).

    `Volume.add(el, dx, dy, z, rz, rx, ry)` carries its element's absolute
    position and misalignment as explicit args. `Lattice.append(el)`
    takes none at all -- a Lattice places each element sequentially,
    right after the previous one ends -- so its elemedge has to be
    reconstructed as a running total of the lengths of whatever this
    stage already placed before it, exactly mirroring what
    `_sequential_elements()` does for Lattice mode on the way out.

    Args:
        calls (list): as in `map_bunch`

    Returns:
        tuple: (list of PKDict element records, "absolute" or "relative"
            for `data.models.simulation.elementPosition` -- whichever of
            Volume.add/Lattice.append was actually used, list of str
            warnings for anything that couldn't be resolved -- e.g. a
            field-map element, whose source file path isn't recoverable
            once the script has already loaded it into a plain numpy
            array before ever calling RF_Track)

    Raises:
        IOError: the script built more than one Volume/Lattice -- e.g. a
            rough lattice to autophase against, then a real one rebuilt
            from the computed phases. There's no reliable way to tell
            which one the user actually wants a sim built from, so this
            is unsupported outright rather than silently guessing (see
            `_container_count()`).
    """
    n = _container_count(calls)
    if n > 1:
        raise IOError(
            f"script builds {n} separate Volume/Lattice instances;"
            " only a single one is supported for import"
        )
    by_id = PKDict()
    last_loadtxt = None
    for c in calls:
        if c.kind == "numpy.loadtxt":
            # a field-map element's own constructor never sees its source
            # filename at all -- the script's numpy.loadtxt(filename) call
            # immediately before it is the only place that filename still
            # exists, so it has to be carried forward from here
            last_loadtxt = PKDict(
                filename=c.args[0] if c.args else None,
                found=c.kwargs.get("found"),
            )
            continue
        if c.kind not in _CONTAINER_KINDS:
            by_id[c.obj_id] = c
            if c.kind in ("RF_FieldMap_1d", "Static_Magnetic_FieldMap_1d"):
                c.loadtxt = last_loadtxt
    res = []
    warnings = []
    element_position = "absolute"
    sequential_elemedge = 0
    for c in calls:
        if c.kind not in _CONTAINER_KINDS:
            continue
        el = by_id.get(c.obj_id)
        resolver = _ELEMENT_RESOLVERS.get(el.kind) if el else None
        if resolver is None:
            warnings.append(
                f"skipped an element of unsupported kind={el.kind if el else '?'}"
            )
            continue
        spec, warning = resolver(
            el.fields, el.args, el.kwargs, el.get("loadtxt"), el.get("rescale")
        )
        if warning:
            warnings.append(f'"{el.fields.get("get_name")}": {warning}')
        if c.kind == "Lattice.append":
            element_position = "relative"
            dx = dy = rz = rx = ry = 0
            elemedge = sequential_elemedge
            sequential_elemedge += spec.get("l") or 0
        else:
            dx, dy, elemedge, rz, rx, ry = (list(c.args) + [0] * 6)[:6]
        spec.update(
            name=el.fields.get("get_name") or f"{spec.type}{len(res) + 1}",
            aperture_x=el.fields.get("get_aperture_x", _DEFAULT_APERTURE),
            aperture_y=el.fields.get("get_aperture_y", _DEFAULT_APERTURE),
            dx=dx,
            dy=dy,
            # not recoverable: add()/append() only ever see elemedge+dz
            # already summed into one z value, never the two separately
            dz=0,
            rx=rx,
            ry=ry,
            rz=rz,
            elemedge=elemedge,
        )
        res.append(spec)
    return res, element_position, warnings


def map_settings(calls):
    """Build `data.models.simulationSettings` fields from the recorded
    `Volume`-level calls (`set_s0`/`set_s1`, the `sc_dt_mm` attribute
    assignment, and whichever space-charge engine class was built), or
    None if no `Volume.set_s0`/`set_s1` call was ever recorded at all
    (e.g. a Lattice-only script, which has no such settings, or a
    bunchReport-only one that never builds a beamline).

    Args:
        calls (list): as in `map_bunch`

    Returns:
        PKDict: `data.models.simulationSettings` fields, or None
    """
    s0 = _first(calls, "Volume.set_s0")
    s1 = _first(calls, "Volume.set_s1")
    if s0 is None and s1 is None:
        return None
    res = PKDict(
        trackingS0=s0.args[0] if s0 and s0.args else 0.0,
        trackingS1=s1.args[0] if s1 and s1.args else 10.0,
        # not "1": an explicit value was captured either way, so there's
        # no reason to let the schema recompute a different one
        autoTrackingRange="0",
        autophase="1" if _first(calls, "Volume.autophase") else "0",
    )
    pic = _first(calls, "SpaceCharge_PIC_FreeSpace")
    if pic:
        res.spaceCharge = "pic"
        grid = (list(pic.args) + [8, 8, 16])[:3]
        res.scGridNx, res.scGridNy, res.scGridNz = grid
        smooth = _first(calls, "SpaceCharge_PIC_FreeSpace.set_smooth")
        mirror = _first(calls, "SpaceCharge_PIC_FreeSpace.set_mirror")
        res.scSmooth = smooth.args[0] if smooth and smooth.args else 0.5
        res.scMirror = mirror.args[0] if mirror and mirror.args else 0.0
        dt = _first(calls, "Volume.sc_dt_mm")
        res.scDtMm = dt.args[0] if dt and dt.args else 3.0
    elif _first(calls, "SpaceCharge_P2P"):
        res.spaceCharge = "p2p"
    else:
        res.spaceCharge = "none"
    return res


#: fallback when the recorder's _resolve_rescale() couldn't run at all
#: (e.g. the field array was computed inline, with no preceding
#: numpy.loadtxt() call to detect against, or an arbitrary script's own
#: column convention didn't match the one that detection assumes) --
#: rescaleMode/scaleFactor/maxField truly are unrecoverable in that case,
#: since the rescale arithmetic that consumed them already ran, as plain
#: Python, before the field array ever reached an RF_Track constructor
_RESCALE_NOT_RECOVERABLE = (
    "rescale mode/scale factor/peak field couldn't be detected"
    " (no numpy.loadtxt() call preceded this element, or its data"
    " didn't line up with the final field array); defaulted to"
    " peak/1/0 -- check these"
)


def _container_count(calls):
    """How many distinct Volume/Lattice instances a script's own
    `Volume.add`/`Lattice.append` calls belong to -- see
    `rftrack_import_recorder._wrap_container()` for where each one's
    `container_id` comes from.

    Returns:
        int: 0 if `calls` has no placement call at all (e.g. a
            bunchReport-only script)
    """
    return len({c.get("container_id") for c in calls if c.kind in _CONTAINER_KINDS})


def _field_map_file(element_type, loadtxt):
    """Resolve a field-map element's `fieldMapFile` and any warning for it.

    `loadtxt` is the script's own `numpy.loadtxt(filename)` call
    immediately preceding this element's construction (see
    `map_elements()`) -- the only place that filename still exists, since
    the element's own constructor never receives it, only the already-
    loaded array. `os.path.basename()` first: an arbitrary script
    routinely passes a full (often absolute) path, not a bare filename,
    and `lib_file_name_without_type()` -- which only strips rftrack.py's
    own `{type}-fieldMapFile.` lib-file prefix off the *front* of its
    arg -- would otherwise leave the whole path in place (never matching
    that prefix, but also never matching whatever lib file with the same
    bare name might already exist, wrongly asking to re-upload it).
    """
    if loadtxt is None or not loadtxt.filename:
        return "", "field map source file isn't recoverable; re-select it after import"
    filename = sirepo.sim_data.get_class("rftrack").lib_file_name_without_type(
        os.path.basename(loadtxt.filename),
        model_name=element_type,
        field="fieldMapFile",
    )
    if loadtxt.found:
        return filename, None
    return filename, f'needs "{filename}" uploaded as its field map file'


def _field_map_length(fields, loadtxt):
    """Resolve a field-map element's `l`, honestly, when the file wasn't
    actually there to read.

    `get_length()` reflects whatever array the element was actually
    constructed with. That's trustworthy both when the file was found
    and when there was no file at all (the script computed the field
    array inline) -- only when a `numpy.loadtxt()` call happened *and*
    its file wasn't there is the array `_stub_missing_data_files()`'s
    placeholder, whose made-up s range (0 to 1) would otherwise silently
    become this element's length. 0 (`_ELEMENT`'s own schema default) is
    an honest "unknown" for that one case; a specific-looking fabricated
    number is not. (`l` is cosmetic for a field-map element either way --
    `_element_spec()` never reads it back out for this kind, since the
    generated script always re-derives the real length from the actual
    uploaded file at run time -- but cosmetic is still not the same as
    correct, especially for Sequential/Lattice mode's gap-filling, which
    does use it.)
    """
    if loadtxt and not loadtxt.found:
        return 0
    return fields.get("get_length")


def _field_map_warning(file_warning, rescale_warning):
    """Combine a field-map element's file-specific warning (if any) with
    its rescale-detection warning (if any), or None if neither applies.
    """
    return "; ".join(w for w in (file_warning, rescale_warning) if w) or None


def _first(calls, kind):
    for c in calls:
        if c.kind == kind:
            return c
    return None


def _max_abs(nested):
    res = 0.0
    for v in nested:
        res = max(res, _max_abs(v) if isinstance(v, list) else abs(v))
    return res


def _resolve_cavity_analytic(fields, args, kwargs, loadtxt, rescale):
    return (
        PKDict(
            type="CAVITY",
            fieldSource="analytic",
            l=fields.get("get_length"),
            frequency=fields.get("get_frequency"),
            gradient=_max_abs(fields.get("get_coefficients") or [0]) / 1e6,
            phase=fields.get("get_phid"),
        ),
        None,
    )


def _resolve_cavity_fieldmap(fields, args, kwargs, loadtxt, rescale):
    filename, file_warning = _field_map_file("CAVITY", loadtxt)
    rescale_fields, rescale_warning = _resolve_rescale_fields(rescale, is_cavity=True)
    spec = PKDict(
        type="CAVITY",
        fieldSource="fieldMap",
        l=_field_map_length(fields, loadtxt),
        frequency=fields.get("get_frequency"),
        phase=fields.get("get_phid"),
        fieldMapFile=filename,
    )
    spec.update(rescale_fields)
    return spec, _field_map_warning(file_warning, rescale_warning)


def _resolve_corrector(fields, args, kwargs, loadtxt, rescale):
    h, v = fields.get("get_strength") or (0, 0)
    return (
        PKDict(type="CORRECTOR", l=fields.get("get_length"), h_kick=h, v_kick=v),
        None,
    )


def _resolve_drift(fields, args, kwargs, loadtxt, rescale):
    return PKDict(type="DRIFT", l=fields.get("get_length")), None


def _resolve_quadrupole(fields, args, kwargs, loadtxt, rescale):
    if len(args) > 1 and isinstance(args[1], float) and math.isnan(args[1]):
        # matches rftrack.py's own _build_element: Quadrupole(l, nan, 0.0)
        # + set_gradient(...) is how a gradient-strength quad is built
        return (
            PKDict(
                type="QUADRUPOLE",
                strengthType="gradient",
                l=fields.get("get_length"),
                gradient=fields.get("get_gradient"),
            ),
            None,
        )
    return (
        PKDict(
            type="QUADRUPOLE",
            strengthType="k1",
            l=fields.get("get_length"),
            # get_K1() takes a required argument RF_Track doesn't
            # document (like get_kick()), so it isn't a usable zero-arg
            # accessor -- and get_gradient() reflects RF_Track's own k1
            # -> gradient conversion against whatever rigidity was in
            # effect at the time, not the schema's stored k1 -- only the
            # captured constructor arg is the actual value the script set
            k1=args[1] if len(args) > 1 else None,
        ),
        None,
    )


def _resolve_rbend(fields, args, kwargs, loadtxt, rescale):
    return (
        PKDict(type="RBEND", l=fields.get("get_length"), angle=fields.get("get_angle")),
        None,
    )


def _resolve_rescale_fields(rescale, is_cavity):
    """Build `rescaleMode`/`maxField`/`scaleFactor`, *assuming* a CAVITY
    used "peak" mode and a SOLENOID used "factor" mode -- matching every
    real sim seen so far (see rftrack-import-plan.md), but genuinely not
    verifiable: both modes collapse to the same uniform-scalar-multiply
    shape, so there is no way to confirm which one a given script
    actually used (see `rftrack_import_recorder._resolve_rescale()`).
    Falls back to the honest-unknown defaults (with a warning) when
    `_resolve_rescale()` couldn't even recover the numbers this
    assumption needs.

    Args:
        rescale (PKDict): `ratio` and `peak`, or None -- as attached to
            a field-map element's own call by
            `rftrack_import_recorder._resolve_rescale()`
        is_cavity (bool): True for CAVITY (whose maxField is stored in
            MV/m, the inverse of `_field_map_spec()`'s own `*1e6`),
            False for SOLENOID (already Tesla, no conversion)

    Returns:
        tuple: (PKDict of the three fields, warning str or None)
    """
    if rescale is None:
        return (
            PKDict(rescaleMode="peak", maxField=0, scaleFactor=1),
            _RESCALE_NOT_RECOVERABLE,
        )
    if is_cavity:
        return (
            PKDict(rescaleMode="peak", maxField=rescale.peak / 1e6, scaleFactor=1),
            None,
        )
    return PKDict(rescaleMode="factor", maxField=0, scaleFactor=rescale.ratio), None


def _resolve_screen(fields, args, kwargs, loadtxt, rescale):
    return PKDict(type="SCREEN"), None


def _resolve_solenoid_analytic(fields, args, kwargs, loadtxt, rescale):
    return (
        PKDict(
            type="SOLENOID",
            fieldSource="analytic",
            l=fields.get("get_length"),
            # no get_* accessor exists for an analytic Solenoid's B field
            # (get_KS requires args RF_Track doesn't document) -- only
            # the captured constructor arg carries it back out
            b_field=args[1] if len(args) > 1 else None,
        ),
        None,
    )


def _resolve_solenoid_fieldmap(fields, args, kwargs, loadtxt, rescale):
    filename, file_warning = _field_map_file("SOLENOID", loadtxt)
    rescale_fields, rescale_warning = _resolve_rescale_fields(rescale, is_cavity=False)
    spec = PKDict(
        type="SOLENOID",
        fieldSource="fieldMap",
        l=_field_map_length(fields, loadtxt),
        fieldMapFile=filename,
    )
    spec.update(rescale_fields)
    return spec, _field_map_warning(file_warning, rescale_warning)


#: RF_Track construction "kind" -> function(fields, args, kwargs, loadtxt,
#: rescale) -> (PKDict of that element's type + kind-specific fields,
#: warning or None) -- loadtxt/rescale are only non-None for the two
#: field-map kinds (see map_elements()); every other resolver ignores them
_ELEMENT_RESOLVERS = PKDict(
    Corrector=_resolve_corrector,
    Drift=_resolve_drift,
    Pillbox_Cavity=_resolve_cavity_analytic,
    Quadrupole=_resolve_quadrupole,
    RBend=_resolve_rbend,
    RF_FieldMap_1d=_resolve_cavity_fieldmap,
    Screen=_resolve_screen,
    Solenoid=_resolve_solenoid_analytic,
    Static_Magnetic_FieldMap_1d=_resolve_solenoid_fieldmap,
)
