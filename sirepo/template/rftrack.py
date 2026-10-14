"""RF-Track execution template.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import beamphysics
import numpy
import pykern.pkio
import re
import scipy.constants
import sirepo.mpi
import sirepo.sim_data
import sirepo.template.lattice
import sirepo.util


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


# (mass-energy equivalent in MeV, charge in units of e)
_PARTICLE_MASS_AND_CHARGE = PKDict(
    electron=(
        scipy.constants.physical_constants["electron mass energy equivalent in MeV"][0],
        -1.0,
    ),
    positron=(
        scipy.constants.physical_constants["electron mass energy equivalent in MeV"][0],
        1.0,
    ),
    proton=(
        scipy.constants.physical_constants["proton mass energy equivalent in MeV"][0],
        1.0,
    ),
)

# Column order of the stats file `rslume.rftrack_utils.save_stats()` writes
# (Volume and Lattice transport tables map onto the same columns).
_STAT_COLUMNS = [
    "s",
    "beta_x",
    "beta_y",
    "alpha_x",
    "alpha_y",
    "emitt_x",
    "emitt_y",
    "emitt_4d",
    "beta_z",
    "alpha_z",
    "emitt_z",
    "sigma_x",
    "sigma_y",
    "sigma_z",
    "sigma_Pz",
    "sigma_E",
    "disp_x",
    "disp_y",
    "disp_px",
    "disp_py",
    "mean_x",
    "mean_y",
    "mean_Px",
    "mean_Py",
    "mean_K",
    "mean_E",
    "mean_P",
    "rmax",
    "rmax90",
    "rmax99",
    "rmax99.9",
    "N",
    "Ez",
    "Bz",
]
_STAT_LABELS = PKDict(
    s="s [m]",
    beta_x="beta_x [m]",
    beta_y="beta_y [m]",
    alpha_x="alpha_x",
    alpha_y="alpha_y",
    emitt_x="emitt_x [m*rad]",
    emitt_y="emitt_y [m*rad]",
    emitt_4d="emitt_4d [m*rad]",
    beta_z="beta_z [m]",
    alpha_z="alpha_z",
    emitt_z="emitt_z [m*rad]",
    sigma_x="sigma_x [m]",
    sigma_y="sigma_y [m]",
    sigma_z="sigma_z [m]",
    sigma_Pz="sigma_Pz [eV/c]",
    sigma_E="sigma_E [eV]",
    disp_x="disp_x [m]",
    disp_y="disp_y [m]",
    disp_px="disp_px [rad]",
    disp_py="disp_py [rad]",
    mean_x="mean_x [m]",
    mean_y="mean_y [m]",
    mean_Px="mean_Px [eV/c]",
    mean_Py="mean_Py [eV/c]",
    mean_K="mean_K [eV]",
    mean_E="mean_E [eV]",
    mean_P="mean_P [eV/c]",
    rmax="rmax [m]",
    rmax90="rmax90 [m]",
    rmax99="rmax99 [m]",
    **{"rmax99.9": "rmax99.9 [m]"},
    N="N",
    Ez="Ez [V/m]",
    Bz="Bz [T]",
)

# Column order of the particle files `rslume.rftrack_utils.save_particles()`
# writes, in the base SI units `rslume.rftrack_utils.PHASE_SPACE_SCALE` gives.
_PHASE_SPACE_COLUMNS = ["x", "xp", "y", "yp", "z", "t", "Px", "Py", "Pz", "P", "E", "K"]

# RF_Track Bunch6dT_Generator.species values, keyed by our BeamParticle enum
_CATHODE_SPECIES = PKDict(
    electron="electrons",
    positron="positrons",
    proton="protons",
)
_AXIS_LABELS = PKDict(
    x="x [m]",
    xp="x' [rad]",
    y="y [m]",
    yp="y' [rad]",
    z="z [m]",
    t="t [s]",
    Px="Px [eV/c]",
    Py="Py [eV/c]",
    Pz="Pz [eV/c]",
    P="P [eV/c]",
    E="E [eV]",
    K="K [eV]",
)

_STATS_FILE = "stats.npy"
_BPMS_FILE = "bpms.npy"
_INITIAL_PARTICLES_FILE = "initial_particles.npy"
_FINAL_PARTICLES_FILE = "final_particles.npy"
_SCREEN_FILE_PREFIX = "screen-"
_NONE = "None"

#: RF_Track's own verbosity=1 tracking-progress line (see
#: parameters.py.jinja's `v.verbosity`), e.g.
#: "info: tracking in progress, t = 500000.0 mm/c" -- written to run.log
#: with ANSI "clear line" escapes between updates, not plain newlines,
#: but those don't interfere with finding this substring anywhere in it
_VERBOSITY_T_RE = re.compile(r"t = ([0-9.eE+-]+) mm/c")


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=_rough_percent_complete(run_dir),
            frameCount=0,
        )
    r = _output_info(_read_data(run_dir), run_dir)
    return PKDict(
        percentComplete=100,
        frameCount=1 if len(r) else 0,
        reports=r,
    )


def _rough_percent_complete(run_dir):
    """A rough running estimate from RF_Track's own verbosity progress
    output, not an exact one: `t` (mm/c) is `c * t_phys`, the distance
    light would travel in the elapsed time, and a particle moving at
    close to c covers very nearly that same physical distance -- true
    for all but a brief low-energy stretch near a cathode, negligible
    against a typical multi-meter tracking range -- so the last `t`
    printed so far, divided by the tracking range's own end position
    (both in mm), stands in for actual progress through it.

    Returns:
        float: 0 whenever that's not yet knowable -- run.log doesn't
            exist yet, has no progress line in it yet, or this report
            has no Volume tracking range at all (e.g. a bunchReport)
    """
    log = run_dir.join(template_common.RUN_LOG)
    if not log.exists():
        return 0
    s1_mm = (
        _read_data(run_dir).models.get("simulationSettings", PKDict()).get("trackingS1")
        or 0
    ) * 1e3
    if not s1_mm:
        return 0
    m = _VERBOSITY_T_RE.findall(pykern.pkio.read_text(log))
    if not m:
        return 0
    # not 100: is_running is still True, and the true final t can run a
    # little past this rough estimate's own denominator (see the
    # docstring's "brief low-energy stretch" caveat) -- 100 is reserved
    # for the one time this is actually known, once the job is done
    return min(99, float(m[-1]) * 100.0 / s1_mm)


def get_data_file(run_dir, model, frame, options):
    if "bunchReport" in model:
        fn = _INITIAL_PARTICLES_FILE
    elif frame < 0:
        return template_common.text_data_file(template_common.RUN_LOG, run_dir)
    else:
        fn = _file_name_for_element_animation(
            run_dir,
            model,
            simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME)),
        )
    if options and options.get("suffix") == "openpmd":
        return _openpmd_job_cmd_file(run_dir, fn)
    return fn


def prepare_sequential_output_file(run_dir, data):
    report = data["report"]
    if "bunchReport" in report:
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            try:
                save_sequential_report_data(data, run_dir)
            except IOError:
                # the output file isn't readable
                pass


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def save_sequential_report_data(data, run_dir):
    template_common.write_sequential_result(
        _phase_space_plot(
            data.models[data.report],
            numpy.load(str(run_dir.join(_INITIAL_PARTICLES_FILE))),
        ),
        run_dir=run_dir,
    )


def sim_frame(frame_args):
    # elementAnimations (SCREEN output)
    return _phase_space_plot(
        frame_args,
        numpy.load(
            str(
                frame_args.run_dir.join(
                    _file_name_for_element_animation(
                        frame_args.run_dir, frame_args.frameReport, frame_args.sim_in
                    )
                )
            )
        ),
    )


def sim_frame_bpmAnimation(frame_args):
    v = numpy.load(str(frame_args.run_dir.join(_BPMS_FILE)))
    return PKDict(
        rows=[
            [f"{s:.3f}", f"{q:.3e}", f"{x:.4f}", f"{y:.4f}"] for s, x, y, q in v
        ],
    )


def sim_frame_statAnimation(frame_args):
    return _stat_animation_plot(frame_args)


def sim_frame_stat2Animation(frame_args):
    return _stat_animation_plot(frame_args)


def _stat_animation_plot(frame_args):
    v = numpy.load(str(frame_args.run_dir.join(_STATS_FILE)))
    plots = []
    for f in ("y1", "y2", "y3", "y4", "y5"):
        if frame_args[f] == _NONE:
            continue
        plots.append(
            PKDict(
                label=_STAT_LABELS[frame_args[f]],
                dim=f,
                points=v[:, _STAT_COLUMNS.index(frame_args[f])].tolist(),
            )
        )
    x_name = frame_args.x if frame_args.x != _NONE else "s"
    return template_common.parameter_plot(
        x=v[:, _STAT_COLUMNS.index(x_name)].tolist(),
        plots=plots,
        model=frame_args,
        plot_fields=PKDict(
            dynamicYLabel=True,
            title="",
            y_label="",
            x_label=_STAT_LABELS[x_name],
        ),
    )


def stat_columns():
    return [_NONE] + sorted(_STAT_COLUMNS, key=str.lower)


def build_imported_data(
    elements,
    beamline_class,
    bunch_type,
    particle_group,
    distribution_file,
    name,
    autophase,
    space_charge,
    qcall,
):
    """Build the full imported sirepo data from an rslume.rftrack HDF5
    archive's already-parsed `elements` (a list of flat attrs dicts,
    the same shape `RFTrackSimulator.archive()` writes), the archive's
    own `beamline_class`/`bunch_type` attrs, the bunch's already
    -written-to-a-lib-file `particle_group`/`distribution_file` (see
    `write_distribution_lib_file`), `autophase` (bool, inferred by
    `archive()` itself from whether any cavity had a nonzero `t0` --
    see `rslume.rftrack_archive._infer_autophase`), and `space_charge` (a dict
    shaped like `RFTrackSimulator.archive()`'s own `space_charge`
    argument, or `None` if the archive didn't carry one).

    Each cavity's `phase` is simply its archived `phid`, nothing folded
    in -- wiring `autophase` through to `simulationSettings.autophase`
    is what makes the generated script's own, already-existing
    `autophase(volume)` function re-derive each cavity's (and Screen's)
    real `t0` itself before tracking, the same deterministic search
    that produced the original archived result in the first place, so
    there's no need to carry `t0` through this import at all. Space
    charge has no such per-element signal to derive from, so it can
    only be restored from this archived setting.

    Called from `sirepo.sim_data.rftrack.SimData.prepare_import_file_args`
    -- on the server, not from `stateful_compute_import_file` below (the
    job agent), since a CAVITY/SOLENOID element with a baked field array
    (not a file reference) needs `qcall` to write a new lib file (see
    `_write_field_map_lib_file`), and only the server has one. See that
    method's own docstring for the full reasoning.
    """
    res = simulation_db.default_data(SIM_TYPE)
    res.models.simulation.name = name
    # elementPosition controls Lattice ("relative") vs. Volume
    # ("absolute") -- the archive's own beamline_class says which the
    # original beamline was (RF_Track's Lattice.track() has no Bunch6dT
    # support at all, so a Bunch6dT-bunch archive is always a Volume,
    # but a Bunch6d-bunch archive could legitimately be either).
    res.models.simulation.elementPosition = (
        "relative" if beamline_class == "Lattice" else "absolute"
    )
    els = []
    items = []
    positions = []
    elemedge = 0.0
    # shared across every element below: see _write_field_map_lib_file()
    field_map_cache = {}
    for i, e in enumerate(elements):
        el = _rslume_element_to_sirepo(e, _id=i + 1, qcall=qcall, field_map_cache=field_map_cache)
        els.append(el)
        items.append(el._id)
        if "z" in e:
            # Volume mode: each element's own absolute position was
            # archived directly (_position_to_attrs(), only written
            # for a Volume beamline) -- using that instead of a
            # cumulative length sum is required here, not just more
            # accurate: Volume elements can be at arbitrary, even
            # overlapping z (e.g. a gun cavity and a bucking solenoid
            # occupying the same physical space), so a sequential
            # pack-end-to-end placement is simply wrong for this mode.
            positions.append(PKDict(elemedge=float(e["z"])))
        else:
            positions.append(PKDict(elemedge=elemedge))
            elemedge += el.l
    res.models.elements = els
    res.models.beamlines = [
        PKDict(id=len(els) + 1, name="Beamline1", items=items, positions=positions)
    ]
    # only one beamline is ever built here, so it's both the active
    # (Lattice editor selection) and visualization (report) beamline --
    # same pairing LatticeParser._set_default_beamline() uses for
    # command-based (Elegant/MAD-X) imports, which this HDF5 import
    # doesn't go through.
    res.models.simulation.activeBeamlineId = res.models.simulation.visualizationBeamlineId = (
        len(els) + 1
    )
    res.models.beam = _rslume_bunch_to_sirepo(bunch_type, particle_group, distribution_file)
    res.models.simulationSettings.autophase = "1" if autophase else "0"
    if space_charge:
        s = res.models.simulationSettings
        s.spaceCharge = space_charge["kind"]
        if space_charge["kind"] == "pic":
            s.scDtMm = float(space_charge["dt_mm"])
            s.scGridNx, s.scGridNy, s.scGridNz = (int(n) for n in space_charge["grid"])
            s.scMirror = float(space_charge["mirror_m"])
            s.scSmooth = float(space_charge["smooth"])
    sirepo.template.lattice.LatticeUtil(res, SCHEMA).sort_elements_and_beamlines()
    return res


def stateful_compute_import_file(data, **kwargs):
    """Trivial passthrough: `sirepo.sim_data.rftrack.SimData.
    prepare_import_file_args` already built the full imported data (via
    `build_imported_data` above), on the server, before this was ever
    called -- see that method's docstring for why. This hook still has
    to exist (api_importFile's own dispatch in sirepo/server.py requires
    it for any non-.json/.zip import), even though there's nothing left
    for it to do here, in the job agent.
    """
    return PKDict(imported_data=data.args.imported_data)


def validate_file(file_type, path, sim_id, qcall):
    """Recompute `l` for every CAVITY/SOLENOID element referencing a
    field-map file that was just uploaded, since that's the one
    field-map value genuinely derivable from the file's own content:
    two numeric columns (s [m], field) for a 1D map, or (for a CAVITY's
    2D map) a SUPERFISH-style file whose first column is Z [cm].
    """
    m = re.match(r"^(CAVITY|SOLENOID)-(fieldMapFile|fieldMapFile2d)$", file_type)
    if not m:
        return None
    el_type, field = m.group(1), m.group(2)
    try:
        # numpy.loadtxt() already skips `#`-commented header lines on
        # its own, same as a SUPERFISH 2D map's two header lines
        s = numpy.loadtxt(str(path))[:, 0]
        length = s.max() - s.min()
        if field == "fieldMapFile2d":
            length /= 100  # Z is in cm, not m
    except Exception:
        return (
            f"{path.basename} is not a valid field map file"
            " (expecting two numeric columns: s [m], field)"
            if field == "fieldMapFile"
            else (
                f"{path.basename} is not a valid 2D field map file"
                " (expecting a SUPERFISH-style file: two commented header"
                " lines, then rows of Z [cm], R [cm], Ez [MV/m], Er [MV/m],"
                " |E| [MV/m], H [A/m])"
            )
        )
    try:
        data = simulation_db.open_json_file(SIM_TYPE, sid=sim_id, qcall=qcall)
    except Exception as e:
        # best-effort: sim_id isn't always a real, already-saved
        # simulation (e.g. a lib file uploaded ahead of any sim, as a
        # shared library entry) -- nothing to update in that case, not
        # an error worth failing the upload itself over
        pkdlog("validate_file sim_id={} error={}", sim_id, e)
        return None
    changed = False
    for el in data.models.elements:
        if el.get("type") == el_type and el.get(field) == path.basename:
            el.l = length
            changed = True
    if changed:
        simulation_db.save_simulation_json(
            data, fixup=False, qcall=qcall, modified=True
        )
    return None


def write_distribution_lib_file(f, name, qcall):
    """Extract the archive's own particle data from `f` (the still-open
    archive file -- itself a valid standalone openPMD file, see
    `RFTrackSimulator.archive()`'s docstring) and write it out as a
    brand new lib file for `beam.distributionFile`. Reuses the same
    write-a-new-lib-file-during-import mechanism as
    `_write_field_map_lib_file`, just for the beam model instead of a
    CAVITY/SOLENOID element.

    Only callable with a real `qcall` -- see
    `sirepo.sim_data.rftrack.SimData.prepare_import_file_args`'s own
    docstring for why this has to happen on the server, not in
    `stateful_compute_import_file` (the job agent).

    Returns:
        (str, beamphysics.ParticleGroup): the plain basename to store in
            `beam.distributionFile`, and the particle data itself, so
            the caller doesn't have to re-read it to get mass/charge/
            particle species for the rest of the `beam` model (see
            `_rslume_bunch_to_sirepo`).

    Raises:
        sirepo.util.UserAlert: a lib file of the same name already
            exists with *different* content -- same reason
            `_write_field_map_lib_file` guards against this: the lib
            directory is shared across every simulation this user has
            of this sim type, so re-importing the very same archive (a
            normal thing to do while iterating) would otherwise
            collide with itself on every single retry.
    """
    import beamphysics
    import tempfile

    particle_group = beamphysics.ParticleGroup(h5=f)
    with tempfile.NamedTemporaryFile(suffix=".h5") as t:
        particle_group.write(t.name)
        t.flush()
        # a portion of the file's own md5 in the basename, same
        # convention as track_parser.validate_file()'s _hashed_name()
        # -- this lib file is shared across every simulation this user
        # has of this sim type (not per-simulation), so without this,
        # re-importing a different archive that happens to reuse the
        # same `name` (e.g. two sims both imported from a file called
        # "archive.h5") would silently overwrite an unrelated sim's
        # distribution file.
        basename = f"{name}-{pykern.pkio.py_path(t.name).computehash()[:8]}.h5"
        with open(t.name, "rb") as bf:
            content = bf.read()
    full_name = _SIM_DATA.lib_file_name_with_model_field(
        "beam", "distributionFile", basename
    )
    if _SIM_DATA.lib_file_exists(full_name, qcall=qcall):
        if _SIM_DATA.lib_file_read_binary(full_name, qcall=qcall) == content:
            return basename, particle_group
        raise sirepo.util.UserAlert(
            f"distribution file='{basename}' already exists with "
            "different content; rename and import again"
        )
    _SIM_DATA.lib_file_write(full_name, content, qcall=qcall)
    return basename, particle_group


def write_parameters(data, run_dir, is_parallel):
    pykern.pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _axis_label(name):
    return _AXIS_LABELS[name]


def _bunch_spec(dm, v, from_file_z_offset):
    """Build the BUNCH data record: every value build_bunch()/autophase()/
    _build_element() (for RBEND's rigidity) need, keyed by the field names
    those generated-script functions reference.
    """
    beam = dm.beam
    mass, charge = _PARTICLE_MASS_AND_CHARGE.get(beam.particle) or (
        beam.mass,
        beam.charge,
    )
    res = PKDict(
        charge=charge,
        mass_mev=mass,
        pc_mev=beam.pc,
        random_seed=beam.randomSeed,
    )
    if v.isCathode:
        res.update(
            c_sig_t=beam.cutoffT,
            c_sig_x=beam.cutoffX,
            c_sig_y=beam.cutoffY,
            cathode=True,
            dist_pz="fd_300",
            dist_x="r",
            dist_y="g",
            dist_z="plateau",
            e_photon=beam.ePhoton,
            lt=beam.flatTopLength,
            noise_reduc=beam.noiseReduc == "1",
            np=beam.np,
            phi_eff=beam.phiEff,
            q_total_nc=beam.charge_nC,
            ref_clock=0,
            ref_ekin=0,
            ref_zpos=0,
            rt=beam.riseTime,
            sig_x=beam.sigX,
            species=_CATHODE_SPECIES.get(beam.particle, "electrons"),
        )
    elif v.isFromFile:
        res.update(
            distribution_file=_SIM_DATA.lib_file_name_with_model_field(
                "beam", "distributionFile", beam.distributionFile
            ),
            from_file_z_offset=from_file_z_offset,
        )
    else:
        res.update(
            alpha_x=beam.alpha_x,
            alpha_y=beam.alpha_y,
            beta_x=beam.beta_x,
            beta_y=beam.beta_y,
            charge_nc=beam.charge_nC,
            emit_x=beam.emit_x,
            emit_y=beam.emit_y,
            np=beam.np,
            sigma_pt=beam.sigma_pt,
            sigma_t=beam.sigma_t,
        )
    return res


def _element_spec(el):
    """Build the ELEMENTS data record for one lattice element: a "kind"
    discriminator plus whatever fields the generated script's
    _build_element() and `rslume.rftrack_utils.load_field_map()` need for
    that kind, and the aperture/misalignment fields every kind has.

    Returns (spec, is_cavity).
    """
    res = PKDict(
        name=el.name,
        elemedge=el.elemedge,
        set_aperture=el.setAperture == "1",
        aperture_x=el.aperture_x,
        aperture_y=el.aperture_y,
        aperture_type="circular",
        dx=el.dx,
        dy=el.dy,
        dz=el.dz,
        rx=el.rx,
        ry=el.ry,
        rz=el.rz,
    )
    is_cavity = False
    if el.type == "DRIFT":
        res.kind = "drift"
        res.l = el.l
    elif el.type == "QUADRUPOLE":
        if el.get("strengthType") == "k1":
            res.kind = "quadrupole_k1"
            res.l = el.l
            res.k1 = el.k1
        else:
            res.kind = "quadrupole_gradient"
            res.l = el.l
            res.gradient = el.gradient
    elif el.type == "RBEND":
        res.kind = "rbend"
        res.l = el.l
        res.angle = el.angle
    elif el.type == "SOLENOID":
        if el.get("fieldSource") == "fieldMap":
            res.kind = "solenoid_fieldmap"
            res.update(_field_map_spec(el, is_cavity=False))
        else:
            res.kind = "solenoid_analytic"
            res.l = el.l
            res.b_field = el.b_field
            res.radius = el.aperture_x or el.aperture_y or 0.05
    elif el.type == "CORRECTOR":
        res.kind = "corrector"
        res.l = el.l
        res.h_kick = el.h_kick
        res.v_kick = el.v_kick
    elif el.type == "CAVITY":
        is_cavity = True
        if el.get("fieldSource") == "fieldMap":
            res.kind = "cavity_fieldmap"
            res.update(_field_map_spec(el, is_cavity=True))
        elif el.get("fieldSource") == "2dFieldMap":
            res.kind = "cavity_fieldmap_2d"
            res.update(_field_map_2d_spec(el))
        else:
            res.kind = "cavity_analytic"
            res.l = el.l
            res.frequency_hz = el.frequency
            res.gradient_v_per_m = el.gradient * 1e6
        res.phase_deg = float(el.phase)
    elif el.type == "SCREEN":
        res.kind = "screen"
    elif el.type == "BPM":
        res.kind = "bpm"
        res.l = el.l
    else:
        raise AssertionError(f"unsupported element type={el.type}")
    return res, is_cavity


def _field_map_spec(el, is_cavity):
    res = PKDict(
        file=_SIM_DATA.lib_file_name_with_model_field(
            el.type, "fieldMapFile", el.fieldMapFile
        ),
    )
    if el.get("rescaleMode") == "factor":
        res.rescale_mode = "factor"
        res.scale_factor = el.scaleFactor
    else:
        res.rescale_mode = "peak"
        res.target_field = el.maxField * 1e6 if is_cavity else el.maxField
    if is_cavity:
        res.frequency_hz = el.frequency
    return res


def _field_map_2d_spec(el):
    # no rescale_mode/scale_factor/target_field, unlike _field_map_spec():
    # a 2D (r, z) SUPERFISH-style map is already in absolute physical
    # units (MV/m), with no peak-normalize-or-multiply step applied to it
    return PKDict(
        file=_SIM_DATA.lib_file_name_with_model_field(
            "CAVITY", "fieldMapFile2d", el.fieldMapFile2d
        ),
        frequency_hz=el.frequency,
    )


def _file_name_for_element_animation(run_dir, report, data):
    for info in _output_info(data, run_dir):
        if info.modelKey == report:
            return info.filename
    raise AssertionError(f"no output for frame={report}")


def _format_value(value, indent):
    """Render `value` as Python source: a dict becomes a multi-line
    PKDict(key=value, ...) call (recursively, for nested dicts/lists/
    tuples), matching the hand-written style of test-sim.py, so every
    value the generated script's functions use is visible in one of
    ELEMENTS/BUNCH/SETTINGS rather than injected as a bare literal.
    """
    if isinstance(value, dict):
        pad = " " * (indent + 4)
        return (
            "PKDict(\n"
            + "".join(
                f"{pad}{k}={_format_value(v, indent + 4)},\n" for k, v in value.items()
            )
            + " " * indent
            + ")"
        )
    if isinstance(value, (list, tuple)):
        pad = " " * (indent + 4)
        o, c = ("[", "]") if isinstance(value, list) else ("(", ")")
        return (
            o
            + "\n"
            + "".join(f"{pad}{_format_value(v, indent + 4)},\n" for v in value)
            + " " * indent
            + c
        )
    return repr(value)


_OPENPMD_SPECIES = frozenset(("electron", "positron", "proton"))


def _openpmd_job_cmd_file(run_dir, npy_filename):
    """Convert a saved phase-space file to an OpenPMD-BeamPhysics HDF5 file.

    _PHASE_SPACE_COLUMNS is already in the units ParticleGroup expects
    (x/y/z in m, Px/Py/Pz in eV/c, t in s), so no unit conversion is needed
    here -- only a column selection and reshuffle.
    """
    dm = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME)).models
    ps = numpy.load(str(run_dir.join(npy_filename)))
    n = len(ps)
    species = dm.beam.particle if dm.beam.particle in _OPENPMD_SPECIES else "electron"
    c = _PHASE_SPACE_COLUMNS.index
    pg = beamphysics.ParticleGroup(
        data=PKDict(
            x=ps[:, c("x")],
            y=ps[:, c("y")],
            z=ps[:, c("z")],
            px=ps[:, c("Px")],
            py=ps[:, c("Py")],
            pz=ps[:, c("Pz")],
            t=ps[:, c("t")],
            # ParticleGroup.weight is the (always positive) macroparticle
            # charge in C; the species name carries the sign.
            weight=numpy.full(n, abs(dm.beam.charge_nC) * 1e-9 / n) if n else ps[:, 0],
            species=species,
            status=numpy.ones(n),
        )
    )
    fn = re.sub(r"\.npy$", "", npy_filename) + "_openpmd.h5"
    p = run_dir.join(fn)
    if p.exists():
        p.remove()
    pg.write(str(p))
    return template_common.JobCmdFile(reply_path=p, reply_uri=fn)


def _sequential_elements(elements):
    """Convert absolute (possibly gapped) elemedge positions into a
    strictly sequential list, as required by rft.Lattice.append(), which
    has no notion of position -- each appended element simply begins where
    the previous one ended.

    A gap between two elements becomes a synthetic Drift; elements are
    otherwise unaware of this, so it doesn't affect the true beamline in
    Volume mode. Overlapping elements have no sequential representation at
    all (e.g. a gun cavity and a bucking solenoid occupying the same
    physical space) and are rejected here, rather than silently
    mis-tracked.
    """
    res = []
    prev_end = None
    prev_name = None
    for i, el in enumerate(elements):
        if prev_end is not None:
            gap = el.elemedge - prev_end
            if gap < -1e-9:
                raise sirepo.util.UserAlert(
                    f'"{el.name}" (starting at {el.elemedge} m) overlaps'
                    f' "{prev_name}" (ending at {prev_end} m) -- overlapping'
                    " elements require Absolute (Volume) positioning,"
                    " not Sequential (Lattice).",
                    "elements overlap in lattice mode",
                )
            if gap > 1e-9:
                res.append(
                    PKDict(
                        type="DRIFT",
                        name=f"_gap{i}",
                        l=gap,
                        elemedge=prev_end,
                        setAperture=el.setAperture,
                        aperture_x=el.aperture_x,
                        aperture_y=el.aperture_y,
                        dx=0,
                        dy=0,
                        dz=0,
                        rx=0,
                        ry=0,
                        rz=0,
                    )
                )
        res.append(el)
        prev_end = el.elemedge + el.l
        prev_name = el.name
    return res


def _generate_lattice(util, beamline_id, result):
    beamline = util.get_item(abs(beamline_id))
    for idx, item_id in enumerate(beamline["items"]):
        item = util.get_item(abs(item_id))
        if "type" in item:
            item = PKDict(item)
            # the beamline (not the element) is the source of truth for an
            # element's absolute position, matching how impactt reads
            # beamline.positions[idx].elemedge -- this is what lets the
            # same element in principle appear in different beamlines at
            # different positions, and is what the lattice editor's
            # "absolute" element-positioning UI edits.
            item.elemedge = beamline.positions[idx].elemedge
            result.append(item)
        else:
            _generate_lattice(util, item.id, result)
    return result


def _generate_parameters_file(data):
    util = sirepo.template.lattice.LatticeUtil(data, SCHEMA)
    res, v = template_common.generate_parameters_file(data)
    dm = data.models
    v.spaceCharge = dm.simulationSettings.spaceCharge
    v.autophase = dm.simulationSettings.autophase == "1"
    v.hasCavity = False
    # Volume and Lattice are both valid RF_Track tracking objects -- Volume
    # places every element at its own explicit (possibly overlapping)
    # position; Lattice appends elements sequentially (see
    # _sequential_elements()) and has no absolute-position concept at all.
    # This is a beamline-construction choice, not a tracking difference,
    # so it's locked at simulation creation (simulationView's watchFields)
    # rather than editable, since Volume- and Lattice-only settings (the
    # tracking range; per-element step counts vs. a continuous ODE step
    # size) aren't interchangeable once a beamline is built around one.
    v.isLattice = dm.simulation.elementPosition == "relative"
    v.isCathode = dm.beam.distributionType == "cathode"
    v.isFromFile = dm.beam.distributionType == "fromFile"
    # From File is constructed as a Bunch6dT, like Cathode, when the file
    # holds a near-rest bunch (e.g. a Cathode Emission snapshot): this
    # preserves the file's actual 3D momentum, avoiding the small-angle
    # approximation a Bunch6d's x'/y' would otherwise need (invalid when
    # Pz is comparable to the transverse momentum). For an
    # already-accelerated bunch (e.g. re-injecting a previous sim's own
    # tracked output downstream, where Pz dominates), that approximation is
    # fine, and Bunch6d is used instead since it's the only bunch type
    # Lattice.track() supports at all (see the isLattice/isBunch6dT check
    # below). fromFileNearRest is user-controlled, not auto-detected from
    # the file, so this choice is explicit rather than a heuristic guess.
    v.isBunch6dT = v.isCathode or (v.isFromFile and dm.beam.fromFileNearRest == "1")
    if v.isLattice and v.isBunch6dT:
        # Lattice.track() only accepts a Bunch6d (or the generic Beam
        # supertype) -- verified empirically, it has no Bunch6dT overload
        # at all, unlike Volume.track(), which accepts either.
        raise sirepo.util.UserAlert(
            "Sequential (Lattice) positioning does not support a Bunch6dT"
            " distribution -- switch Distribution to Twiss Parameters,"
            " uncheck From File's Near-Rest Bunch, or use Absolute (Volume)"
            " positioning.",
            "Lattice mode incompatible with Bunch6dT distribution",
        )
    v.isBunchReport = "bunchReport" in data.get("report", "")

    # A From File bunch's Z is rebased to (Z - mean(Z)) + from_file_z_offset;
    # 0.0 is the only sensible choice when previewing the bunch alone (no
    # volume exists yet to place it relative to), when the destination is
    # a Lattice (which has no absolute position -- it always begins at
    # its own local s=0, so there's no elemedge value to rebase onto), or
    # for a Bunch6dT (cathode/near-rest) bunch: its Z is a fixed emission
    # convention RF-Track's own emission tracking expects (confirmed
    # empirically -- a freshly-built cathode bunch's Z is always 0
    # regardless of volume_s0, and shifting a reconstructed Bunch6dT's Z
    # away from that, e.g. to volume_s0, causes RF-Track to lose the
    # first particle during emission tracking and corrupts the whole
    # run), unlike an already-moving Bunch6d, where Z genuinely is a
    # physical position meaningful to rebase onto the new destination.
    from_file_z_offset = 0.0
    volume_s0, volume_s1 = 0.0, 1.0
    if not v.isBunchReport:
        elements = _generate_lattice(util, util.select_beamline().id, [])
        if v.isLattice:
            elements = _sequential_elements(elements)
        elif dm.simulationSettings.autoTrackingRange == "1":
            # Volume.set_s0()/set_s1() gate which portion of every element's
            # field is active during tracking (not merely where particles
            # are reported), so an element positioned to start before the
            # beam origin -- e.g. a solenoid whose field map's own s=0
            # reference sits upstream of the cathode -- needs the range
            # widened to its full extent or that leading portion is
            # silently excluded from the field the beam feels.
            volume_s0 = min((e.elemedge for e in elements), default=0.0)
            volume_s1 = max((e.elemedge + e.l for e in elements), default=1.0)
            if not v.isBunch6dT:
                from_file_z_offset = volume_s0
        else:
            volume_s0 = dm.simulationSettings.trackingS0
            volume_s1 = dm.simulationSettings.trackingS1
            if not v.isBunch6dT:
                from_file_z_offset = volume_s0

        specs = []
        for e in elements:
            s, is_cavity = _element_spec(e)
            specs.append(s)
            v.hasCavity = v.hasCavity or is_cavity
        v.elementsCode = _format_value(specs, 0)
        settings = PKDict(
            num_threads=sirepo.mpi.cfg().cores,
            space_charge=_space_charge_spec(dm.simulationSettings),
        )
        if not v.isLattice:
            settings.tracking_range_m = (volume_s0, volume_s1)
            settings.volume_dt_mm = 0.5
            settings.volume_tt_dt_mm = 10.0
        v.settingsCode = _format_value(settings, 0)

    v.bunchCode = _format_value(_bunch_spec(dm, v, from_file_z_offset), 0)
    return res + template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )


def _space_charge_spec(simulation_settings):
    if simulation_settings.spaceCharge == "p2p":
        return PKDict(kind="p2p")
    if simulation_settings.spaceCharge == "pic":
        return PKDict(
            kind="pic",
            dt_mm=simulation_settings.scDtMm,
            grid=(
                simulation_settings.scGridNx,
                simulation_settings.scGridNy,
                simulation_settings.scGridNz,
            ),
            mirror_m=simulation_settings.scMirror,
            smooth=simulation_settings.scSmooth,
        )
    return PKDict()


def _output_info(data, run_dir):
    res = []
    if run_dir.join(_STATS_FILE).exists():
        for model_key in ("statAnimation", "stat2Animation"):
            res.append(
                PKDict(
                    columns=stat_columns(),
                    name="Beam Variables",
                    modelKey=model_key,
                    report=model_key,
                    frameCount=1,
                )
            )
    if run_dir.join(_BPMS_FILE).exists():
        res.append(
            PKDict(
                name="Beam Position at Monitors",
                modelKey="bpmAnimation",
                report="bpmAnimation",
                frameCount=1,
            )
        )
    names = _screen_names(data)
    for idx, name in enumerate(names):
        fn = f"{_SCREEN_FILE_PREFIX}{idx}.npy"
        if run_dir.join(fn).exists():
            res.append(
                PKDict(
                    modelKey=f"elementAnimation{idx}",
                    reportIndex=idx,
                    report="elementAnimation",
                    name=name,
                    frameCount=1,
                    filename=fn,
                )
            )
    # Always show the final tracked beam as its own plot, regardless of
    # whether the beamline happens to end with a SCREEN element.
    if run_dir.join(_FINAL_PARTICLES_FILE).exists():
        idx = len(names)
        res.append(
            PKDict(
                modelKey=f"elementAnimation{idx}",
                reportIndex=idx,
                report="elementAnimation",
                name="Final Particles",
                frameCount=1,
                filename=_FINAL_PARTICLES_FILE,
            )
        )
    return res


def _phase_space_plot(model, values):
    return template_common.heatmap(
        values=[
            values[:, _PHASE_SPACE_COLUMNS.index(model.x)],
            values[:, _PHASE_SPACE_COLUMNS.index(model.y)],
        ],
        model=model,
        plot_fields=PKDict(
            x_label=_axis_label(model.x),
            y_label=_axis_label(model.y),
            title="",
            # TODO(pjm): should be a different setting (show empty space as alpha=0)
            threshold=[1e-20, 1e20],
        ),
    )


def _read_data(run_dir):
    return simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))


def _infer_particle(mass_mev, charge):
    """Match (`mass_mev`, `charge`) against `_PARTICLE_MASS_AND_CHARGE`'s
    known species, returning the matching `beam.particle` value, or
    "other" if nothing matches. `mass`/`charge` are archived exactly (not
    a statistical fit, unlike the Twiss values this doesn't touch), so an
    exact-ish match is a reliable identification, not a guess.
    """
    for name, (mass, charge_e) in _PARTICLE_MASS_AND_CHARGE.items():
        if numpy.isclose(mass_mev, mass, rtol=1e-6) and charge == charge_e:
            return name
    return "other"


def _rslume_bunch_to_sirepo(bunch_type, particle_group, distribution_file):
    """Build the `beam` model for an rslume.rftrack archive's bunch --
    always "fromFile": it already handles both Bunch6d and Bunch6dT (via
    fromFileNearRest), so no separate distributionType/field set is
    needed for either, unlike a Twiss-style statistical-moment summary
    (which Bunch6dT has no schema fields for at all).

    `particle`/`mass`/`charge` are still set explicitly here, not left
    to the file alone: every "fromFile" branch in build_bunch() (the
    generated script) builds the tracked bunch's mass/charge from
    BUNCH.mass_mev/BUNCH.charge (the beam model's own fields), not from
    the file's embedded species, same as every other distributionType.
    `randomSeed` isn't in the archive at all (RF-Track's own API has no
    getter for it), so it's left for fixup_old_data()'s own
    schema-default backfill, same as every other `beam` field this
    doesn't set explicitly.
    """
    mass_mev = particle_group.mass / 1e6
    charge = particle_group.species_charge / scipy.constants.e
    return PKDict(
        particle=_infer_particle(mass_mev, charge),
        mass=mass_mev,
        charge=charge,
        distributionType="fromFile",
        distributionFile=distribution_file,
        fromFileNearRest="1" if bunch_type == "Bunch6dT" else "0",
    )


def _write_field_map_lib_file(el_type, element_name, field, hz, qcall, field_map_cache):
    """Write `field` (a 1D RF-Track field-map array, sampled every `hz`
    meters) as a brand new lib file -- two columns (s [m], field value),
    the same two-column text format `rslume.rftrack_utils.load_field_map()` already reads
    for a normal uploaded field map. Named after the archived element
    (`element_name`) so it's recognizable in the lattice editor
    afterward.

    `field_map_cache` ({(el_type, md5): basename}) is shared across
    every element in one import (see `build_imported_data()`) --
    several elements built from the same uploaded field-map file (e.g.
    a linac's identical accelerating cavities) are archived with one
    shared copy, not a byte-for-byte duplicate per element
    (`rslume.rftrack_archive._dedupe_field_maps()`); reusing the one lib file
    already written for that same content here, instead of writing a
    new one per element, keeps that true on import too.

    Only callable with a real `qcall`: this writes to the lib directory,
    which needs one (`sirepo.sim_data.SimDataBase.lib_file_write`) --
    `stateful_compute_import_file` (the job agent) doesn't have one,
    which is why the whole import is built server-side instead, in
    `sirepo.sim_data.rftrack.SimData.prepare_import_file_args` (see its
    own docstring).

    Returns:
        str: the plain basename to store in the model's `fieldMapFile`.

    Raises:
        sirepo.util.UserAlert: a lib file of the same name already
            exists with *different* content -- the lib directory is
            shared across every simulation this user has of this sim
            type (not per-simulation), so re-importing the very same
            archive (a normal thing to do while iterating) would
            otherwise collide with itself on every single retry.
    """
    import hashlib
    import io

    field = numpy.asarray(field)
    cache_key = (el_type, hashlib.md5(field.tobytes()).hexdigest())
    if cache_key in field_map_cache:
        return field_map_cache[cache_key]

    basename = f"{element_name}.dat"
    full_name = _SIM_DATA.lib_file_name_with_model_field(
        el_type, "fieldMapFile", basename
    )
    s = numpy.arange(len(field)) * hz
    buf = io.StringIO()
    numpy.savetxt(buf, numpy.column_stack([s, field]))
    content = buf.getvalue()
    if _SIM_DATA.lib_file_exists(full_name, qcall=qcall):
        if _SIM_DATA.lib_file_read_text(full_name, qcall=qcall) == content:
            field_map_cache[cache_key] = basename
            return basename
        raise sirepo.util.UserAlert(
            f"field map file='{basename}' already exists with different "
            f"content; rename element '{element_name}' and import again"
        )
    _SIM_DATA.lib_file_write(full_name, content, qcall=qcall)
    field_map_cache[cache_key] = basename
    return basename


def _rslume_element_to_sirepo(e, _id, qcall, field_map_cache):
    """Invert rslume.rftrack_archive._element_to_attrs()'s dict into a sirepo
    element model -- the exact reverse of _element_spec()'s analytic
    DRIFT/QUADRUPOLE/CAVITY/CORRECTOR/SCREEN/BPM construction, plus
    RF_FieldMap_1d/Static_Magnetic_FieldMap_1d (a CAVITY/SOLENOID with a
    baked field array instead of a file reference) -- `qcall` and
    `field_map_cache` are only used by those two, to write the array
    out as a (possibly shared) lib file (see `_write_field_map_lib_file`).

    Raises:
        sirepo.util.UserAlert: `e["class"]` isn't one of the element
            classes rslume.rftrack can archive yet (RF_FieldMap_2d or
            analytic Solenoid), or a field-map file of the same name
            already exists.
    """
    cls = str(e["class"])
    aperture_x = float(e["aperture_x"])
    aperture_y = float(e["aperture_y"])
    if cls == "Pillbox_Cavity":
        # Unlike every other element class, Pillbox_Cavity has no
        # universal "set_aperture() was never called" sentinel -- its
        # own un-set default is instead a function of its own geometry
        # (confirmed empirically: linear in cell_length). Detecting
        # "never explicitly set" here means asking a freshly-built,
        # aperture-untouched cavity with the same geometry what ITS
        # default is, rather than guessing a fixed constant that could
        # drift across RF_Track versions. Safe to import here: this
        # function runs inside job_cmd's stateful_compute_import_file
        # dispatch, the same job-agent process that already needs
        # RF_Track installed to run the generated parameters.py.
        import RF_Track as rft

        ref = rft.Pillbox_Cavity(
            numpy.zeros(1),
            float(e["frequency"]),
            float(e["cell_length"]),
            int(e["n_cells"]),
        )
        is_unset = (
            aperture_x == ref.get_aperture_x() and aperture_y == ref.get_aperture_y()
        )
    else:
        # RF-Track's own sentinel for "set_aperture() was never called" --
        # same convention already used for the CCDTL example this session.
        is_unset = aperture_x == -0.001 and aperture_y == -0.001
    res = PKDict(
        _id=_id,
        _super="_ELEMENT",
        name=str(e["name"]),
        setAperture="0" if is_unset else "1",
        aperture_x=0.015 if is_unset else aperture_x,
        aperture_y=0.015 if is_unset else aperture_y,
        # "x"/"y" are only present for a Volume-archived element
        # (_position_to_attrs()) -- its absolute transverse position,
        # which build_beamline()'s own v.add() takes as dx/dy directly
        # (no separate "nominal" x/y baseline to offset from). Not
        # present at all for a Lattice-archived element, which has no
        # per-element absolute position concept, so 0 is correct there.
        dx=float(e.get("x", 0.0)),
        dy=float(e.get("y", 0.0)),
        dz=0,
        # rx/ry/rz stay 0 unconditionally: a non-identity rotation makes
        # _position_to_attrs() -- and so archive() itself -- raise
        # NotImplementedError, so nothing with a real rotation ever
        # reaches this function in the first place.
        rx=0,
        ry=0,
        rz=0,
    )
    if cls == "Drift":
        res.type = "DRIFT"
        res.l = float(e["length"])
    elif cls == "Quadrupole":
        res.type = "QUADRUPOLE"
        res.l = float(e["length"])
        res.strengthType = "gradient"
        res.gradient = float(e["gradient"])
        res.k1 = 0
    elif cls == "Pillbox_Cavity":
        res.type = "CAVITY"
        res.l = float(e["n_cells"]) * float(e["cell_length"])
        res.fieldSource = "analytic"
        res.frequency = float(e["frequency"])
        # the exact inverse of _element_spec()'s gradient_v_per_m = el.gradient * 1e6
        res.gradient = float(e["coefficients"][-1][-1]) / 1e6
        res.phase = float(e["phid"])
        res.fieldMapFile = ""
        res.fieldMapFile2d = ""
        res.rescaleMode = "peak"
        res.maxField = 0
        res.scaleFactor = 1
    elif cls == "Corrector":
        res.type = "CORRECTOR"
        res.l = float(e["length"])
        # the exact inverse of _element_spec()'s
        # e = rft.Corrector(spec.l, spec.h_kick, spec.v_kick) -- so this
        # recovers whatever h_kick/v_kick produce the same Kx/Ky again,
        # not a true kick angle in mrad despite the schema's label (the
        # forward direction already passes h_kick/v_kick straight through
        # as RF-Track's Kx/Ky, which the reference manual documents as an
        # integrated strength in T.mm, not a kick angle).
        res.h_kick = float(e["kx"])
        res.v_kick = float(e["ky"])
    elif cls == "Screen":
        res.type = "SCREEN"
        # rft.Screen() takes no length -- the exact inverse of
        # _element_spec()'s own SCREEN branch, which never sets res.l
        # either; width/height aren't archivable to a sirepo field (the
        # SCREEN model has none), so they're dropped here same as the
        # forward direction already drops them building a bare Screen().
        res.l = 0
    elif cls == "Bpm":
        res.type = "BPM"
        res.l = float(e["length"])
        # resolution/resolution_t aren't archivable to a sirepo field
        # (the BPM model has none, and the forward direction's
        # rft.Bpm(spec.l) never sets them either) -- dropped, same as
        # Screen's width/height above.
    elif cls == "RF_FieldMap_1d":
        res.type = "CAVITY"
        res.fieldSource = "fieldMap"
        res.frequency = float(e["frequency"])
        res.phase = float(e["phid"])
        # get_Ez() (_serialize_rf_fieldmap_1d) is RF-Track's own complex
        # phasor representation, confirmed empirically here to always
        # have an exactly-zero imaginary part for a field built from a
        # real-valued uploaded file (_build_element()'s own
        # rft.RF_FieldMap_1d(field, ...) construction never passes a
        # complex field in the first place) -- load_field_map() expects
        # a plain two-column real-valued text file, so this keeps only
        # the real part the new lib file is written from.
        field = numpy.asarray(e["ez"]).real
        hz = float(e["hz"])
        # the exact inverse of load_field_map()'s own
        # length = s.max() - s.min() == (len(s) - 1) * step
        res.l = (len(field) - 1) * hz
        res.fieldMapFile = _write_field_map_lib_file(
            "CAVITY", res.name, field, hz, qcall, field_map_cache
        )
        res.fieldMapFile2d = ""
        # the archived array is already the exact final field (any
        # P_actual/P_map scale is already baked in) -- "factor"/1
        # applies it unchanged, the same role as Pillbox_Cavity's own
        # rescaleMode/scaleFactor defaults above, just meaning something
        # different for a field map (no further rescale) than for an
        # analytic cavity (no field amplitude to even rescale).
        res.rescaleMode = "factor"
        res.scaleFactor = 1
        res.maxField = 0
        res.gradient = 0
    elif cls == "Static_Magnetic_FieldMap_1d":
        res.type = "SOLENOID"
        res.fieldSource = "fieldMap"
        field = numpy.asarray(e["bz"])
        hz = float(e["hz"])
        res.l = (len(field) - 1) * hz
        res.fieldMapFile = _write_field_map_lib_file(
            "SOLENOID", res.name, field, hz, qcall, field_map_cache
        )
        res.rescaleMode = "factor"
        res.scaleFactor = 1
        res.maxField = 0
        res.b_field = 0
    else:
        raise sirepo.util.UserAlert(
            f"the uploaded file contains an unsupported element type={cls}"
        )
    return res


def _screen_names(data):
    util = sirepo.template.lattice.LatticeUtil(data, SCHEMA)
    beamline_id = int(
        data.models.simulation.visualizationBeamlineId or data.models.beamlines[0].id
    )
    res = []
    for item_id in util.explode_beamline(beamline_id):
        item = util.get_item(abs(item_id))
        if item.get("type") == "SCREEN":
            res.append(item.name)
    return res
