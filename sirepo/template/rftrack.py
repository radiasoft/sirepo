"""RF-Track execution template.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import numpy
import pykern.pkio
import scipy.constants
import sirepo.mpi
import sirepo.sim_data
import sirepo.template.lattice


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


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    r = _output_info(_read_data(run_dir), run_dir)
    return PKDict(
        percentComplete=100,
        frameCount=1 if len(r) else 0,
        reports=r,
    )


def get_data_file(run_dir, model, frame, options):
    if "bunchReport" in model:
        return _INITIAL_PARTICLES_FILE
    if frame < 0:
        return template_common.text_data_file(template_common.RUN_LOG, run_dir)
    return _file_name_for_element_animation(
        run_dir,
        model,
        simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME)),
    )


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


def write_parameters(data, run_dir, is_parallel):
    pykern.pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _axis_label(name):
    return _AXIS_LABELS[name]


def _element_code(el, index):
    """Build the Python source lines that construct one RF_Track element.

    Returns a PKDict with:
        var: the local variable name the element is bound to
        lines: list of top-level python statements; the first line always
            assigns `var`
        is_cavity: whether this is an RF element (participates in autophase)
        x, y, z, roll, pitch, yaw: already-converted values (meters,
            radians) for the Volume.add() call. x/y are always the
            element's misalignment offset (dx/dy) since the nominal
            transverse position is always 0; z is the beamline's absolute
            elemedge position for this element plus its dz misalignment.
    """
    var = f"_e{index}"
    lines = []
    is_cavity = False
    phase = None

    if el.type == "DRIFT":
        lines.append(f"{var} = rft.Drift({el.l})")
    elif el.type == "QUADRUPOLE":
        if el.get("strengthType") == "k1":
            lines.append(f"{var} = rft.Quadrupole({el.l}, {el.k1})")
        else:
            lines.append(f'{var} = rft.Quadrupole({el.l}, float("nan"), 0.0)')
            lines.append(f"{var}.set_gradient({el.gradient})")
    elif el.type == "RBEND":
        lines.append(f"{var} = rft.RBend({el.l}, {el.angle}, Pc / charge)")
    elif el.type == "SOLENOID":
        if el.get("fieldSource") == "fieldMap":
            lines += _field_map_load_lines(var, el, is_cavity=False)
        else:
            r = el.aperture_x or el.aperture_y or 0.05
            lines.append(f"{var} = rft.Solenoid({el.l}, {el.b_field}, {r})")
    elif el.type == "CORRECTOR":
        lines.append(f"{var} = rft.Corrector({el.l}, {el.h_kick}, {el.v_kick})")
    elif el.type == "CAVITY":
        is_cavity = True
        phase = float(el.phase)
        if el.get("fieldSource") == "fieldMap":
            lines += _field_map_load_lines(var, el, is_cavity=True)
        else:
            lines.append(f"_l_cell = {_CLIGHT} / (2.0 * {el.frequency})")
            lines.append(f"_n_cells = max(1, round({el.l} / _l_cell))")
            lines.append("_a = numpy.zeros(1)")
            lines.append(f"_a[-1] = {el.gradient} * 1e6")
            lines.append(
                f"{var} = rft.Pillbox_Cavity(_a, {el.frequency}, _l_cell, _n_cells)"
            )
        lines.append(f"{var}.set_phid({phase})")
    elif el.type == "SCREEN":
        lines.append(f"{var} = rft.Screen()")
    else:
        raise AssertionError(f"unsupported element type={el.type}")

    lines.append(f'{var}.set_name("{el.name}")')
    lines.append(f'{var}.set_aperture({el.aperture_x}, {el.aperture_y}, "circular")')
    return PKDict(
        var=var,
        lines=lines,
        is_cavity=is_cavity,
        # Volume.add()'s x/y/z/roll/pitch/yaw args are in meters/radians;
        # our schema misalignment fields are in mm/mrad. The nominal
        # transverse position is always 0 (only misalignment moves x/y);
        # z is the beamline's absolute elemedge position for this element
        # plus its own dz misalignment.
        x=el.dx / 1000.0,
        y=el.dy / 1000.0,
        z=el.elemedge + el.dz / 1000.0,
        roll=el.rz / 1000.0,
        pitch=el.rx / 1000.0,
        yaw=el.ry / 1000.0,
    )


def _field_map_load_lines(var, el, is_cavity):
    lib_name = _SIM_DATA.lib_file_name_with_model_field(
        el.type, "fieldMapFile", el.fieldMapFile
    )
    lines = [
        f'_T = numpy.loadtxt("{lib_name}")',
        "_S = _T[:, 0]",
        "_dS = (_S.max() - _S.min()) / (len(_S) - 1)",
        "_L = _S.max() - _S.min()",
        "_field = _T[:, 1]",
    ]
    if el.get("rescaleMode") == "factor":
        lines.append(f"_field = _field * {el.scaleFactor}")
    else:
        target = el.maxField * 1e6 if is_cavity else el.maxField
        lines.append(f"_field = _field / numpy.max(numpy.abs(_field)) * {target}")
    if is_cavity:
        lines.append(f"{var} = rft.RF_FieldMap_1d(_field, _dS, _L, {el.frequency}, +1)")
    else:
        lines.append(f"{var} = rft.Static_Magnetic_FieldMap_1d(_field, _dS)")
    return lines


def _file_name_for_element_animation(run_dir, report, data):
    for info in _output_info(data, run_dir):
        if info.modelKey == report:
            return info.filename
    raise AssertionError(f"no output for frame={report}")


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
    v.beam = dm.beam
    v.particleMassAndCharge = _PARTICLE_MASS_AND_CHARGE.get(dm.beam.particle)
    v.spaceCharge = dm.simulationSettings.spaceCharge
    v.scGridNx = dm.simulationSettings.scGridNx
    v.scGridNy = dm.simulationSettings.scGridNy
    v.scGridNz = dm.simulationSettings.scGridNz
    v.scDtMm = dm.simulationSettings.scDtMm
    v.scSmooth = dm.simulationSettings.scSmooth
    v.scMirror = dm.simulationSettings.scMirror
    v.autophase = dm.simulationSettings.autophase == "1"
    v.numThreads = sirepo.mpi.cfg().cores
    v.isCathode = dm.beam.distributionType == "cathode"
    v.cathodeSpecies = _CATHODE_SPECIES.get(dm.beam.particle, "electrons")
    v.phaseSpaceFields = (
        _PHASE_SPACE_FIELDS_CATHODE if v.isCathode else _PHASE_SPACE_FIELDS
    )
    v.screenPhaseSpaceFields = (
        _PHASE_SPACE_FIELDS_CATHODE_SCREEN if v.isCathode else _PHASE_SPACE_FIELDS
    )
    v.phaseSpaceScale = _PHASE_SPACE_SCALE
    v.statTransportFields = _STAT_TRANSPORT_FIELDS
    v.statScale = _STAT_SCALE
    v.isBunchReport = "bunchReport" in data.get("report", "")
    if not v.isBunchReport:
        elements = _generate_lattice(util, util.select_beamline().id, [])
        if dm.simulationSettings.autoTrackingRange == "1":
            # Volume.set_s0()/set_s1() gate which portion of every element's
            # field is active during tracking (not merely where particles
            # are reported), so an element positioned to start before the
            # beam origin -- e.g. a solenoid whose field map's own s=0
            # reference sits upstream of the cathode -- needs the range
            # widened to its full extent or that leading portion is
            # silently excluded from the field the beam feels.
            v.volumeS0 = min((e.elemedge for e in elements), default=0.0)
            v.volumeS1 = max((e.elemedge + e.l for e in elements), default=1.0)
        else:
            v.volumeS0 = dm.simulationSettings.trackingS0
            v.volumeS1 = dm.simulationSettings.trackingS1
        v.elements = [_element_code(e, i) for i, e in enumerate(elements)]
        v.hasCavity = any(e.is_cavity for e in v.elements)
    return res + template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )


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
