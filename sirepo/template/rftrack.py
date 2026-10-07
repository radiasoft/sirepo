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

_CLIGHT = scipy.constants.c

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

# RF_Track Volume.get_transport_table() column selector and the matching
# column order saved to _STATS_FILE. Volume uses different token names/case
# than Lattice for several quantities (e.g. %mean_Z instead of %S,
# %sigma_X/%sigma_Y instead of %sigma_x/%sigma_y, %sigma_Z and %sigma_Pz
# instead of the Lattice-only %sigma_t/%sigma_pt).
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
_STAT_TRANSPORT_FIELDS = (
    "%mean_Z %beta_x %beta_y %alpha_x %alpha_y %emitt_x %emitt_y %emitt_4d"
    " %beta_z %alpha_z %emitt_z %sigma_X %sigma_Y %sigma_Z %sigma_Pz %sigma_E"
    " %disp_x %disp_y %disp_px %disp_py %mean_X %mean_Y %mean_Px %mean_Py"
    " %mean_K %mean_E %mean_P %rmax %rmax90 %rmax99 %rmax99.9 %N"
)
# Lattice.get_transport_table() lacks %mean_Z/%sigma_X/%sigma_Y/%mean_X/
# %mean_Y (Volume-only tokens; "unknown identifier" otherwise) -- %S and
# the lowercase %mean_x/%mean_y/%sigma_x/%sigma_y are its equivalents.
# %sigma_Z (a length) has no Lattice equivalent at all; %sigma_t (a
# light-time, i.e. already a length in the same mm units once scaled) is
# the closest analog. %sigma_Pz (an absolute momentum spread) likewise has
# no equivalent -- %sigma_pt is a RELATIVE spread (dp/p), so it's
# multiplied by %mean_P (see below) to approximate the same absolute
# quantity %sigma_Pz would give, at the same %mean_Z(->%S) index (14) and
# %mean_P index (26) in this field list.
_STAT_TRANSPORT_FIELDS_LATTICE = (
    "%S %beta_x %beta_y %alpha_x %alpha_y %emitt_x %emitt_y %emitt_4d"
    " %beta_z %alpha_z %emitt_z %sigma_x %sigma_y %sigma_t %sigma_pt %sigma_E"
    " %disp_x %disp_y %disp_px %disp_py %mean_x %mean_y %mean_Px %mean_Py"
    " %mean_K %mean_E %mean_P %rmax %rmax90 %rmax99 %rmax99.9 %N"
)
_STAT_SIGMA_PT_COLUMN = 14
_STAT_MEAN_P_COLUMN = 26
# RF_Track's native units: beta/disp_x/disp_y in m already; emitt_* in
# mm.mrad; mean_Z, sigma_X/Y/Z, mean_X/Y, rmax* in mm; sigma_Pz in MeV/c;
# mean_Px/Py/mean_K/mean_E/mean_P/sigma_E in MeV or MeV/c; alpha_*, disp_p*,
# and N are dimensionless. Rescaled to base SI (m, rad, eV, eV/c) to match
# impact-t's convention; dimensionless/already-SI columns get a scale of 1.
# Ez/Bz (from Volume.get_field(), not get_transport_table()) are already in
# base SI (V/m, T).
_STAT_SCALE = [
    1e-3,  # s (mean_Z): mm -> m
    1,  # beta_x: m
    1,  # beta_y: m
    1,  # alpha_x
    1,  # alpha_y
    1e-6,  # emitt_x: mm.mrad -> m.rad
    1e-6,  # emitt_y: mm.mrad -> m.rad
    1e-6,  # emitt_4d: mm.mrad -> m.rad (sqrt(emitt_x * emitt_y)-like scale)
    1,  # beta_z: m
    1,  # alpha_z
    1e-6,  # emitt_z: mm.mrad -> m.rad
    1e-3,  # sigma_x (sigma_X): mm -> m
    1e-3,  # sigma_y (sigma_Y): mm -> m
    1e-3,  # sigma_z (sigma_Z): mm -> m
    1e6,  # sigma_Pz: MeV/c -> eV/c
    1e6,  # sigma_E: MeV -> eV
    1,  # disp_x: m
    1,  # disp_y: m
    1,  # disp_px: rad
    1,  # disp_py: rad
    1e-3,  # mean_x (mean_X): mm -> m
    1e-3,  # mean_y (mean_Y): mm -> m
    1e6,  # mean_Px: MeV/c -> eV/c
    1e6,  # mean_Py: MeV/c -> eV/c
    1e6,  # mean_K: MeV -> eV
    1e6,  # mean_E: MeV -> eV
    1e6,  # mean_P: MeV/c -> eV/c
    1e-3,  # rmax: mm -> m
    1e-3,  # rmax90: mm -> m
    1e-3,  # rmax99: mm -> m
    1e-3,  # rmax99.9: mm -> m
    1,  # N
    1,  # Ez: V/m
    1,  # Bz: T
]
# %S (Lattice's position token) is already in meters -- verified empirically
# against Volume's %mean_Z (raw millimeters) for the same physical length --
# unlike every other position/size quantity (%mean_x, %sigma_x, %sigma_t,
# rmax*, ...), which stays in the same raw millimeters in both Lattice and
# Volume. So only the first ("s") entry differs from _STAT_SCALE.
_STAT_SCALE_LATTICE = [1] + _STAT_SCALE[1:]
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

# RF_Track Bunch*.get_phase_space() column selector and the matching column
# order saved to the particle files. RF_Track's own native units are mm,
# mrad, and MeV/c; the values are rescaled to base SI units (m, rad, eV/c,
# eV, s) at save time to match impact-t's unit convention. %Z (uppercase) is
# the one token that behaves identically across Bunch6d and Bunch6dT, tracked
# or freshly-generated, initial or screen-captured: lowercase %z is defined
# only for Bunch6d and is always exactly 0 there (not the same quantity).
_PHASE_SPACE_COLUMNS = ["x", "xp", "y", "yp", "z", "t", "Px", "Py", "Pz", "P", "E", "K"]
_PHASE_SPACE_FIELDS = "%x %xp %y %yp %Z %dt %Px %Py %Pz %P %E %K"
# Bunch6dT (used for the "cathode" distribution) uses different token names
# for the same quantities: uppercase %X/%Y for position (lowercase %x/%y
# are not defined), and %t0 rather than %dt for the per-particle time. The
# resulting columns line up with _PHASE_SPACE_COLUMNS/_PHASE_SPACE_SCALE
# above; only the RF_Track-side token string differs.
_PHASE_SPACE_FIELDS_CATHODE = "%X %xp %Y %yp %Z %t0 %Px %Py %Pz %P %E %K"
# Volume.get_bunch_at_screens() always returns Bunch6d-typed bunches (even
# when the tracked bunch was a Bunch6dT), so %t0 is not defined there; only
# %dt works, same as the non-cathode case.
_PHASE_SPACE_FIELDS_CATHODE_SCREEN = "%X %xp %Y %yp %Z %dt %Px %Py %Pz %P %E %K"
# %dt for a raw-matrix-constructed Bunch6d (not one built by its own
# generator, e.g. Bunch6d_QR) is relative to whichever particle happens to
# be first in the array, not the mean -- verified empirically. From File's
# already-accelerated case (Bunch6d, not Bunch6dT) is built from a raw
# matrix, so it uses %t (absolute) instead to avoid that arbitrary offset.
_PHASE_SPACE_FIELDS_FROM_FILE = "%x %xp %y %yp %Z %t %Px %Py %Pz %P %E %K"

# RF_Track Bunch6dT_Generator.species values, keyed by our BeamParticle enum
_CATHODE_SPECIES = PKDict(
    electron="electrons",
    positron="positrons",
    proton="protons",
)
_PHASE_SPACE_SCALE = [
    1e-3,  # x: mm -> m
    1e-3,  # xp: mrad -> rad
    1e-3,  # y: mm -> m
    1e-3,  # yp: mrad -> rad
    1e-3,  # z: mm -> m
    1e-3 / _CLIGHT,  # t: mm/c -> s
    1e6,  # Px: MeV/c -> eV/c
    1e6,  # Py: MeV/c -> eV/c
    1e6,  # Pz: MeV/c -> eV/c
    1e6,  # P: MeV/c -> eV/c
    1e6,  # E: MeV -> eV
    1e6,  # K: MeV -> eV
]
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


def stateful_compute_import_file(data, **kwargs):
    """Import a self-contained RF-Track Python script.

    The exact inverse of `_generate_parameters_file()`: runs the script
    under `rftrack_import_recorder` (in a subprocess, via
    `rftrack_import_runner`, since it's arbitrary code) and maps whatever
    it recorded back onto a fresh simulation (`rftrack_import_mapper`).
    See rftrack-import-plan.md for the design and its current limits.
    """
    if data.args.ext_lower != ".py":
        raise IOError(f"invalid file={data.args.basename} extension, expecting .py")
    from sirepo.template import rftrack_import_mapper
    from sirepo.template import rftrack_import_runner

    r = rftrack_import_runner.run(data.args.file_as_str)
    elements, element_position, warnings = rftrack_import_mapper.map_elements(r.calls)
    # a field-map file already in this sim type's lib store (e.g. a
    # previous import or sim already uploaded it) is never "missing" to
    # the generic lattice import dialog's upload prompt -- it only
    # prompts for a file not already in the lib list, so without this,
    # `l` would stay fabricated/zeroed forever for that case, unlike a
    # genuinely new file (see validate_file(), which handles that one
    # once the user actually uploads it)
    lib_files = _lib_file_data(elements, qcall=None)
    if lib_files:
        r = rftrack_import_runner.run(data.args.file_as_str, data_files=lib_files)
        elements, element_position, warnings = rftrack_import_mapper.map_elements(
            r.calls
        )
    res = simulation_db.default_data(SIM_TYPE)
    res.models.simulation.name = data.args.purebasename
    res.models.simulation.elementPosition = element_position
    item_ids = []
    positions = []
    for spec in elements:
        el = _SIM_DATA.model_defaults(spec.type)
        el.update(spec)
        el._id = len(res.models.elements) + 1
        positions.append(PKDict(elemedge=el.pkdel("elemedge")))
        res.models.elements.append(el)
        item_ids.append(el._id)
    beamline_id = len(res.models.elements) + 1
    res.models.beamlines = [
        PKDict(id=beamline_id, name="Beamline1", items=item_ids, positions=positions)
    ]
    # sirepo-lattice.js's loadTree() groups the elements list into type
    # categories by looking only at *consecutive* elements (a new
    # category starts whenever the type differs from the previous
    # element's) -- it assumes same-typed elements are already
    # contiguous, not merely present, so the physical/beamline order
    # built above (where types are naturally interleaved, e.g. two
    # different cavities with a solenoid between them) produces more
    # than one same-named category and an Angular ngRepeat dupes error.
    # sort_elements_and_beamlines() is what every other lattice-code
    # importer already calls for this same reason; items/positions
    # above reference elements by _id, so this doesn't affect them.
    sirepo.template.lattice.LatticeUtil(res, SCHEMA).sort_elements_and_beamlines()
    res.models.simulation.activeBeamlineId = beamline_id
    res.models.simulation.visualizationBeamlineId = beamline_id
    beam = rftrack_import_mapper.map_bunch(r.calls)
    if beam:
        res.models.beam.update(beam)
        res.models.beam.distributionType = "cathode"
    else:
        warnings.append(
            "no recognized bunch (only Cathode Emission is mapped so far);"
            " check the Beam tab"
        )
    if r.get("pc_mev") is not None:
        # unobservable any other way for a Cathode bunch (see
        # rftrack_import_driver._resolve_pc_mev()) -- recovered directly
        # from the script's own globals only when it's one Sirepo itself
        # generated; otherwise stays the schema default, same as before
        res.models.beam.pc = r.pc_mev
    settings = rftrack_import_mapper.map_settings(r.calls)
    if settings:
        res.models.simulationSettings.update(settings)
    if r.get("partial_error"):
        # track()/btrack()/autophase() are no-ops now, not an abort (see
        # rftrack_import_recorder._NOOP_METHODS), specifically so a
        # script keeps running past them -- the lattice/bunch/settings
        # above already reflect everything up to wherever it then
        # actually stopped, so this is a caveat on the result, not a
        # reason to discard it
        warnings.append(
            f"script did not finish running ({r.partial_error}); import"
            " reflects whatever it built before that point"
        )
    if warnings:
        res.importWarnings = warnings
    # not a bare `return res`: sirepo.server's api_importFile unwraps
    # this call's result as resp.content_as_object().imported_data --
    # without that key, it never finds one, treats that as a hard
    # failure, and short-circuits past the save that normally assigns
    # models.simulation.simulationId, which is what broke the browser's
    # own post-import redirect (it had no simulationId to redirect to)
    return PKDict(imported_data=res)


def validate_file(file_type, path, sim_id, qcall):
    """Recompute `l` for every element referencing a field-map file that
    was just uploaded because stateful_compute_import_file() found it
    missing at import time (see `_lib_file_data()` for the other case --
    the file already being in the lib store, which never reaches here
    at all since the generic lattice import dialog only uploads a file
    it doesn't already have).

    `l` is the one field-map value genuinely derivable from the file's
    own content; `rescaleMode`/`scaleFactor`/`maxField` are not, and
    stay at the import's placeholder defaults regardless (see
    rftrack-import-plan.md).
    """
    m = re.match(r"^(CAVITY|SOLENOID)-fieldMapFile$", file_type)
    if not m:
        return None
    try:
        s = numpy.loadtxt(str(path))[:, 0]
        length = s.max() - s.min()
    except Exception:
        return (
            f"{path.basename} is not a valid field map file"
            " (expecting two numeric columns: s [m], field)"
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
        if el.get("type") == m.group(1) and el.get("fieldMapFile") == path.basename:
            el.l = length
            changed = True
    if changed:
        simulation_db.save_simulation_json(
            data, fixup=False, qcall=qcall, modified=True
        )
    return None


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
    _build_element()/_load_field_map() need for that kind, and the
    aperture/misalignment fields every kind has.

    Returns (spec, is_cavity).
    """
    res = PKDict(
        name=el.name,
        elemedge=el.elemedge,
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
        else:
            res.kind = "cavity_analytic"
            res.l = el.l
            res.frequency_hz = el.frequency
            res.gradient_v_per_m = el.gradient * 1e6
        res.phase_deg = float(el.phase)
    elif el.type == "SCREEN":
        res.kind = "screen"
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


def _lib_file_data(elements, qcall):
    """Field-map elements (from `rftrack_import_mapper.map_elements()`)
    whose referenced file is already in this sim type's lib store,
    read now (lib-prefixed basename -> content) so a second import pass
    can resolve `l` from the real file -- not `rescaleMode`/
    `scaleFactor`/`maxField`, which are never recoverable from the
    file's own content regardless (see rftrack-import-plan.md).
    """
    res = PKDict()
    for el in elements:
        if el.get("fieldSource") != "fieldMap" or not el.get("fieldMapFile"):
            continue
        n = _SIM_DATA.lib_file_name_with_model_field(
            el.type, "fieldMapFile", el.fieldMapFile
        )
        if n in res:
            continue
        try:
            if not _SIM_DATA.lib_file_exists(n, qcall=qcall):
                continue
            res[n] = pykern.pkio.read_text(_SIM_DATA.lib_file_abspath(n, qcall=qcall))
        except Exception as e:
            # best-effort: a field-map file genuinely missing from the
            # lib store is the normal, common case here, not an error --
            # and any other failure (e.g. no uid/qcall context to resolve
            # a lib directory against, outside the real agent-side
            # import flow) must not crash the whole import over this
            # one optional enhancement
            pkdlog("lib_file_data name={} error={}", n, e)
    return res


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
    # tracked output downstream, where Pz dominates -- matching how
    # zone_2.ipynb loads zone_1's own saved output), that approximation is
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
    if v.isBunch6dT:
        v.phaseSpaceFields = _PHASE_SPACE_FIELDS_CATHODE
        v.screenPhaseSpaceFields = _PHASE_SPACE_FIELDS_CATHODE_SCREEN
    elif v.isFromFile:
        v.phaseSpaceFields = _PHASE_SPACE_FIELDS_FROM_FILE
        v.screenPhaseSpaceFields = _PHASE_SPACE_FIELDS_FROM_FILE
    else:
        v.phaseSpaceFields = _PHASE_SPACE_FIELDS
        v.screenPhaseSpaceFields = _PHASE_SPACE_FIELDS
    v.phaseSpaceScale = _PHASE_SPACE_SCALE
    v.isBunchReport = "bunchReport" in data.get("report", "")

    # A From File bunch's Z is rebased to (Z - mean(Z)) + from_file_z_offset;
    # 0.0 is the only sensible choice when previewing the bunch alone (no
    # volume exists yet to place it relative to), or when the destination
    # is a Lattice (which has no absolute position -- it always begins at
    # its own local s=0, so there's no elemedge value to rebase onto).
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
            from_file_z_offset = volume_s0
        else:
            volume_s0 = dm.simulationSettings.trackingS0
            volume_s1 = dm.simulationSettings.trackingS1
            from_file_z_offset = volume_s0

        specs = []
        for e in elements:
            s, is_cavity = _element_spec(e)
            specs.append(s)
            v.hasCavity = v.hasCavity or is_cavity
        v.elementsCode = _format_value(specs, 0)
        v.statTransportFields = (
            _STAT_TRANSPORT_FIELDS_LATTICE if v.isLattice else _STAT_TRANSPORT_FIELDS
        )
        v.statSigmaPtColumn = _STAT_SIGMA_PT_COLUMN
        v.statMeanPColumn = _STAT_MEAN_P_COLUMN
        v.statScale = _STAT_SCALE_LATTICE if v.isLattice else _STAT_SCALE
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
    if simulation_settings.spaceCharge == "pic":
        return PKDict(
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
