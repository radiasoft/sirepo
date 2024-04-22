"""Shadow execution template.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo.template import template_common
from sirepo.template.template_common import ModelUnits
import sirepo.template.srw_shadow
import re
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

BEAM_STATS_FILE = "beam_stats.json"
_SHADOW_OUTPUT_FILE = "shadow-output.dat"

_CENTIMETER_FIELDS = {
    "aperture": [
        "position",
        "horizontalSize",
        "verticalSize",
        "horizontalOffset",
        "verticalOffset",
    ],
    "crl": [
        "position",
        "pilingThickness",
        "rmirr",
        "focalDistance",
        "lensThickness",
        "lensDiameter",
    ],
    "crystal": [
        "position",
        "halfWidthX1",
        "halfWidthX2",
        "halfLengthY1",
        "halfLengthY2",
        "externalOutlineMajorAxis",
        "externalOutlineMinorAxis",
        "internalOutlineMajorAxis",
        "internalOutlineMinorAxis",
        "ssour",
        "simag",
        "rmirr",
        "r_maj",
        "r_min",
        "param",
        "axmaj",
        "axmin",
        "ell_the",
        "thickness",
        "r_johansson",
        "offx",
        "offy",
        "offz",
    ],
    "electronBeam": ["sigmax", "sigmaz", "epsi_x", "epsi_z", "epsi_dx", "epsi_dz"],
    "emptyElement": ["position"],
    "geometricSource": ["wxsou", "wzsou", "sigmax", "sigmaz", "wysou", "sigmay"],
    "grating": [
        "position",
        "halfWidthX1",
        "halfWidthX2",
        "halfLengthY1",
        "halfLengthY2",
        "externalOutlineMajorAxis",
        "externalOutlineMinorAxis",
        "internalOutlineMajorAxis",
        "internalOutlineMinorAxis",
        "ssour",
        "simag",
        "rmirr",
        "r_maj",
        "r_min",
        "param",
        "axmaj",
        "axmin",
        "ell_the",
        "rulingDensityCenter",
        "holo_r1",
        "holo_r2",
        "dist_fan",
        "hunt_h",
        "hunt_l",
        "offx",
        "offy",
        "offz",
    ],
    "histogramReport": ["distanceFromSource"],
    "lens": ["position", "focal_x", "focal_z"],
    "mirror": [
        "position",
        "halfWidthX1",
        "halfWidthX2",
        "halfLengthY1",
        "halfLengthY2",
        "externalOutlineMajorAxis",
        "externalOutlineMinorAxis",
        "internalOutlineMajorAxis",
        "internalOutlineMinorAxis",
        "ssour",
        "simag",
        "rmirr",
        "r_maj",
        "r_min",
        "param",
        "axmaj",
        "axmin",
        "ell_the",
        "prereflDensity",
        "mlayerSubstrateDensity",
        "mlayerEvenSublayerDensity",
        "mlayerOddSublayerDensity",
        "offx",
        "offy",
        "offz",
    ],
    "obstacle": [
        "position",
        "horizontalSize",
        "verticalSize",
        "horizontalOffset",
        "verticalOffset",
    ],
    "plotXYReport": ["distanceFromSource"],
    "rayFilter": ["distance", "x1", "x2", "z1", "z2"],
    "watch": ["position"],
    "zonePlate": ["position", "diameter"],
}

_FIELD_ALIAS = PKDict(
    externalOutlineMajorAxis="rwidx2",
    externalOutlineMinorAxis="rlen2",
    halfLengthY1="rlen1",
    halfLengthY2="rlen2",
    halfWidthX1="rwidx1",
    halfWidthX2="rwidx2",
    horizontalOffset="cx_slit[0]",
    horizontalSize="rx_slit[0]",
    internalOutlineMajorAxis="rwidx1",
    internalOutlineMinorAxis="rlen1",
    rulingDensity="ruling",
    rulingDensityCenter="ruling",
    rulingDensityPolynomial="ruling",
    singleEnergyValue="ph1",
    verticalOffset="cz_slit[0]",
    verticalSize="rz_slit[0]",
)

_LOWERCASE_FIELDS = set(["focal_x", "focal_z"])

_WIGGLER_TRAJECTORY_FILENAME = "xshwig.sha"


def stateless_compute_harmonic_photon_energy(data, **kwargs):
    return _compute_harmonic_photon_energy(data.args)


def stateful_compute_convert_to_srw(data, **kwargs):
    return sirepo.template.srw_shadow.Convert().to_srw(data)


def get_data_file(run_dir, model, frame, options):
    if model == "beamStatisticsReport":
        return BEAM_STATS_FILE
    return _SHADOW_OUTPUT_FILE


def post_execution_processing(success_exit, is_parallel, run_dir, **kwargs):
    if success_exit or is_parallel:
        return None
    return _parse_shadow_log(run_dir)


def python_source_for_model(data, model, qcall, **kwargs):
    data.report = model
    if not model:
        beamline = data.models.beamline
        watch_id = None
        for b in beamline:
            if b.type == "watch":
                watch_id = b.id
        if watch_id:
            data.report = "{}{}".format(_SIM_DATA.WATCHPOINT_REPORT, watch_id)
        else:
            data.report = "plotXYReport"
    return """
{}

import Shadow.ShadowTools
Shadow.ShadowTools.plotxy(beam, 1, 3, nbins=100, nolost=1)
    """.format(
        _generate_parameters_file(data, is_parallel=True)
    )


def remove_last_frame(run_dir):
    pass


def write_parameters(data, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(
            data,
            run_dir,
            is_parallel,
        ),
    )


def _compute_harmonic_photon_energy(data):
    from orangecontrib.shadow.util.undulator.source_undulator import SourceUndulator
    from syned.storage_ring.electron_beam import ElectronBeam
    from syned.storage_ring.magnetic_structures.undulator import Undulator

    undulator = data.undulator
    ebeam = data.undulatorBeam
    su = SourceUndulator(
        syned_electron_beam=ElectronBeam(energy_in_GeV=ebeam.energy),
        syned_undulator=Undulator(
            K_horizontal=undulator.k_horizontal,
            K_vertical=undulator.k_vertical,
            period_length=undulator.period / 1000,
            number_of_periods=int(undulator.length / (undulator.period / 1000)),
        ),
    )
    su.set_energy_monochromatic_at_resonance(int(undulator.energy_harmonic))
    return PKDict(
        photon_energy=su._EMIN,
        maxangle=su._MAXANGLE * 1e6,
    )


def _eq(item, field, *values):
    t = SCHEMA.model[item.type][field][1]
    for v, n in SCHEMA.enum[t]:
        if item[field] == v:
            return n in values
    raise AssertionError(
        "{}: value not found for model={} field={} type={}".format(
            item[field], item.type, field, t
        )
    )


def _field_value(name, field, value):
    return "\n{}.{} = {}".format(
        name,
        field if field in _LOWERCASE_FIELDS else field.upper(),
        value,
    )


def _fields(name, item, fields):
    res = ""
    for f in fields:
        field_name = _FIELD_ALIAS.get(f, f)
        res += _field_value(name, field_name, item[f])
    return res


def _generate_autotune_element(item):
    res = _item_field(item, ["f_central"])
    if item.type == "grating" or item.f_central == "0":
        res += _item_field(item, ["t_incidence", "t_reflection"])
    if item.f_central == "1":
        res += _item_field(item, ["f_phot_cent"])
        if item.f_phot_cent == "0":
            res += _item_field(item, ["phot_cent"])
        elif item.f_phot_cent == "1":
            res += _item_field(item, ["r_lambda"])
    return res


def _generate_beamline_optics(models, last_id=None, calc_beam_stats=False):
    beamline = models.beamline
    res = ""
    prev_position = source_position = 0
    last_element = False
    count = 0
    for i in range(len(beamline)):
        item = beamline[i]
        trace_method = "traceOE"
        if _is_disabled(item):
            continue
        count += 1
        source_distance = item.position - prev_position
        if calc_beam_stats and source_distance >= 1e-3:
            res += f"\n\npos = divide_drift(pos, beam, {count}, {source_distance})"
            source_distance = (
                source_distance / models.beamStatisticsReport.driftDivisions
            )
            count += models.beamStatisticsReport.driftDivisions - 1
        from_source = item.position - source_position
        image_distance = 0
        for j in range(i + 1, len(beamline)):
            next_item = beamline[j]
            if _is_disabled(next_item) or next_item.type == "emptyElement":
                continue
            image_distance = next_item.position - item.position
            break
        theta_recalc_required = (
            item.type in ("crystal", "grating")
            and item.f_default == "1"
            and item.f_central == "1"
            and item.fmirr != "5"
        )
        if item.type == "crl":
            count, res = _generate_crl(
                item, source_distance, count, res, calc_beam_stats
            )
        elif item.type == "zonePlate":
            count, res = _generate_zone_plate(
                item,
                source_distance,
                count,
                res,
                _photon_energy(models),
                calc_beam_stats,
            )
        else:
            res += "\n\noe = Shadow.OE()" + _field_value("oe", "dummy", "1.0")
            if item.type == "aperture" or item.type == "obstacle":
                res += _generate_screen(item)
            elif item.type == "crystal":
                res += _generate_element(item, from_source, image_distance)
                res += _generate_crystal(item)
            elif item.type == "emptyElement":
                res += "\n" + "oe.set_empty(ALPHA={})".format(item.alpha)
            elif item.type == "grating":
                res += _generate_element(item, from_source, image_distance)
                res += _generate_grating(item)
            elif item.type == "lens":
                trace_method = "traceIdealLensOE"
                res += _item_field(item, ["focal_x", "focal_z"])
            elif item.type == "mirror":
                res += _generate_element(item, from_source, image_distance)
                res += _generate_mirror(item)
            elif item.type == "watch":
                res += "\n" + "oe.set_empty()"
                if last_id and last_id == int(item.id):
                    last_element = True
            else:
                raise RuntimeError("unknown item type: {}".format(item))
            if theta_recalc_required:
                res += """
# use shadow to calculate THETA from the default position
# but do not advance the original beam to the image depth
calc_beam = beam.duplicate()
calc_oe = oe.duplicate()
calc_oe.F_DEFAULT = 1
calc_oe.T_SOURCE = calc_oe.SSOUR
calc_oe.T_IMAGE = calc_oe.SIMAG
calc_beam.traceOE(calc_oe, 1)
oe.THETA = calc_oe.T_INCIDENCE * 180.0 / math.pi
"""
            res += _generate_trace(
                source_distance, trace_method, count, calc_beam_stats
            )
        if last_element:
            break
        prev_position = item.position
        if item.type != "emptyElement":
            source_position = item.position
    return res


def _generate_bending_magnet(data):
    return (
        _source_field(
            data.models.electronBeam,
            [
                "sigmax",
                "sigmaz",
                "epsi_x",
                "epsi_z",
                "bener",
                "epsi_dx",
                "epsi_dz",
                "f_pol",
            ],
        )
        + _source_field(
            data.models.sourceDivergence, ["hdiv1", "hdiv2", "vdiv1", "vdiv2"]
        )
        + _field_value("source", "f_phot", 0)
        + _field_value("source", "fsource_depth", 4)
        + _field_value("source", "f_color", 3)
        + _source_field(data.models.bendingMagnet, ["r_magnet", "ph1", "ph2", "fdistr"])
        + _field_value("source", "r_aladdin", "source.R_MAGNET * 100")
    )


def _generate_crl(item, source_distance, count, res, calc_beam_stats):
    for n in range(item.numberOfLenses):
        res += _generate_crl_lens(
            item,
            n == 0,
            n == (item.numberOfLenses - 1),
            count,
            source_distance,
            calc_beam_stats,
        )
        count += 2
    return count - 1, res


def _generate_crl_lens(item, is_first, is_last, count, source, calc_beam_stats):
    half_lens = item.lensThickness / 2.0
    source_width = item.pilingThickness / 2.0 - half_lens
    diameter = item.rmirr * 2.0

    def _half(is_obj, **values):
        is_ima = not is_obj
        values = PKDict(values)
        # "10" is "conic", but it's only valid if useCCC, which
        # are the external coefficients. The "shape" values are still
        # valid
        which = "obj" if is_obj else "ima"
        values.update(
            {
                "r_attenuation_" + which: item.attenuationCoefficient,
                "r_ind_" + which: item.refractionIndex,
            }
        )
        if _eq(item, "fmirr", "Spherical", "Paraboloid"):
            ccc = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, diameter, 0.0]
            if bool(_eq(item, "initialCurvature", "Convex")) == is_ima:
                values.f_convex = 1
            else:
                # Inverse diameter for concave surface
                ccc[8] = -ccc[8]
            if _eq(item, "useCCC", "Yes"):
                if "f_convex" in values:
                    del values["f_convex"]
            if _eq(item, "fmirr", "Paraboloid"):
                ccc[2] = 0.0
            values.ccc = "numpy.array([{}])".format(", ".join(map(str, ccc)))
        source_distance, image_distance = (
            ((source if is_first else 0.0) + source_width, half_lens)
            if is_ima
            else (half_lens, source_width)
        )
        return "\n\noe = Shadow.OE(){}".format(
            _fields("oe", values, sorted(values.keys()))
        ) + _generate_trace(
            source_distance,
            "traceOE",
            count + is_obj,
            calc_beam_stats,
            image_distance=image_distance,
        )

    common = PKDict(
        dummy=1.0,
    )
    # Same for all lenses (afaict)
    common.update(
        f_ext=1,
        f_refrac=1,
        t_incidence=0.0,
        t_reflection=180.0,
    )
    common.fmirr = item.fmirr
    if not _eq(item, "fmirr", "Plane"):
        if _eq(item, "useCCC", "Yes"):
            common.fmirr = 10
        if _eq(item, "fcyl", "Yes"):
            common.update(
                fcyl=item.fcyl,
                cil_ang=item.cil_ang,
            )
        if _eq(item, "fmirr", "Paraboloid"):
            common.param = item.rmirr
        else:
            common.rmirr = item.rmirr
    common.fhit_c = item.fhit_c
    if _eq(item, "fhit_c", "Finite"):
        lens_radius = item.lensDiameter / 2.0
        common.update(
            fshape=2,
            rlen2=lens_radius,
            rwidx2=lens_radius,
        )
    return _half(0, **common) + _half(1, **common)


def _generate_crystal(item):
    res = _field_value("oe", "f_crystal", "1")
    res += _generate_autotune_element(item)
    res += _item_field(item, ["f_refrac", "f_mosaic"])
    if item.f_mosaic == "0":
        res += _item_field(item, ["f_bragg_a", "f_johansson"])
        if item.f_bragg_a == "1":
            res += _item_field(item, ["a_bragg", "thickness"])
            if item.f_refrac == "1":
                res += _item_field(item, ["order"])
        if item.f_johansson == "1":
            res += _field_value("oe", "f_ext", "1")
            res += _item_field(item, ["r_johansson"])
    elif item.f_mosaic == "1":
        res += _item_field(item, ["spread_mos", "thickness", "mosaic_seed"])
    bragg_filename = "crystal-bragg-{}.txt".format(item.id)
    res += (
        "\n"
        + "bragg(interactive=False, DESCRIPTOR='{}', H_MILLER_INDEX={}, K_MILLER_INDEX={}, L_MILLER_INDEX={}, TEMPERATURE_FACTOR={}, E_MIN={}, E_MAX={}, E_STEP={}, SHADOW_FILE='{}')".format(
            item.braggMaterial,
            item.braggMillerH,
            item.braggMillerK,
            item.braggMillerL,
            item.braggTemperaturFactor,
            item.braggMinEnergy,
            item.braggMaxEnergy,
            item.braggEnergyStep,
            bragg_filename,
        )
    )
    res += _field_value("oe", "file_refl", "b'{}'".format(bragg_filename))
    return res


def _generate_element(item, from_source, to_focus):
    if item.f_ext == "0":
        # always override f_default - generated t_image is always 0.0
        if item.f_default == "1":
            item.ssour = from_source
            item.simag = to_focus
            item.theta = item.t_incidence
            item.f_default = "0"
    res = _item_field(item, ["fmirr", "alpha", "fhit_c"])
    if item.fmirr in ("1", "2", "3", "4", "7"):
        res += _item_field(item, ["f_ext"])
        if item.f_ext == "0":
            res += _item_field(item, ["f_default", "ssour", "simag", "theta"])
    if item.fmirr in ("1", "2", "4", "7"):
        res += _item_field(item, ["f_convex", "fcyl"])
        if item.fcyl == "1":
            res += _item_field(item, ["cil_ang"])
    if item.fmirr == "1":
        if item.f_ext == "1":
            res += _item_field(item, ["rmirr"])
    elif item.fmirr in ("2", "7"):
        if item.f_ext == "1":
            res += _item_field(item, ["axmaj", "axmin", "ell_the"])
    elif item.fmirr == "3":
        res += _item_field(item, ["f_torus"])
        if item.f_ext == "1":
            res += _item_field(item, ["r_maj", "r_min"])
    elif item.fmirr == "4":
        if item.f_ext == "0":
            res += _item_field(item, ["f_side"])
        else:
            res += _item_field(item, ["param"])
    if item.fhit_c == "1":
        res += _item_field(item, ["fshape"])
        if item.fshape == "1":
            res += _item_field(
                item, ["halfWidthX1", "halfWidthX2", "halfLengthY1", "halfLengthY2"]
            )
        else:
            res += _item_field(
                item, ["externalOutlineMajorAxis", "externalOutlineMinorAxis"]
            )
            if item.fshape == "3":
                res += _item_field(
                    item, ["internalOutlineMajorAxis", "internalOutlineMinorAxis"]
                )
    if "offx" in item:
        misalignment = ""
        for f in ("offx", "offy", "offz", "x_rot", "y_rot", "z_rot"):
            if item[f] != 0:
                misalignment += _item_field(item, [f])
        if misalignment:
            res += _field_value("oe", "f_move", "1")
            res += misalignment
    return res


def _generate_geometric_source(data):
    geo = data.models.geometricSource
    res = (
        _source_field(
            geo,
            [
                "fsour",
                "wxsou",
                "wzsou",
                "sigmax",
                "sigmaz",
                "fdistr",
                "sigdix",
                "sigdiz",
                "cone_max",
                "cone_min",
                "fsource_depth",
                "wysou",
                "sigmay",
                "f_color",
                "f_polar",
                "f_coher",
                "pol_angle",
                "pol_deg",
            ],
        )
        + _source_field(
            data.models.sourceDivergence, ["hdiv1", "hdiv2", "vdiv1", "vdiv2"]
        )
        + _field_value("source", "f_phot", 0)
    )
    if geo.f_color == "1":
        res += _source_field(geo, ["singleEnergyValue"])
    else:
        res += _source_field(geo, ["ph1", "ph2"])
    return res


def _generate_grating(item):
    res = _field_value("oe", "f_grating", "1")
    res += _generate_autotune_element(item)
    res += _item_field(item, ["f_ruling", "order"])
    if item.f_ruling in ("0", "1"):
        res += _item_field(item, ["rulingDensity"])
    elif item.f_ruling == "2":
        res += _item_field(
            item,
            [
                "holo_r1",
                "holo_r2",
                "holo_del",
                "holo_gam",
                "holo_w",
                "holo_rt1",
                "holo_rt2",
                "f_pw",
                "f_pw_c",
                "f_virtual",
            ],
        )
    elif item.f_ruling == "3":
        res += _item_field(item, ["rulingDensityCenter"])
    elif item.f_ruling == "5":
        res += _item_field(
            item,
            [
                "rulingDensityPolynomial",
                "f_rul_abs",
                "rul_a1",
                "rul_a2",
                "rul_a3",
                "rul_a4",
            ],
        )
    if item.f_central == "1":
        res += _item_field(item, ["f_mono"])
        if item.f_mono == "4":
            res += _item_field(item, ["f_hunt", "hunt_h", "hunt_l", "blaze"])
    return res


def _generate_mirror(item):
    item.t_reflection = item.t_incidence
    res = _item_field(item, ["t_incidence", "t_reflection"])

    if item.f_reflec in ("1", "2"):
        res += _item_field(item, ["f_reflec"])
        if item.f_refl == "0":
            prerefl_filename = "mirror-prerefl-{}.txt".format(item.id)
            res += (
                "\n"
                + "prerefl(interactive=False, SYMBOL='{}', DENSITY={}, FILE='{}', E_MIN={}, E_MAX={}, E_STEP={})".format(
                    item.prereflElement,
                    item.prereflDensity,
                    prerefl_filename,
                    item.reflectivityMinEnergy,
                    item.reflectivityMaxEnergy,
                    item.prereflStep,
                )
            )
            res += _field_value("oe", "file_refl", "b'{}'".format(prerefl_filename))
        elif item.f_refl == "2":
            mlayer_filename = "mirror-pre_mlayer-{}.txt".format(item.id)
            res += (
                "\n"
                + "pre_mlayer(interactive=False, FILE='{}',E_MIN={},E_MAX={},S_DENSITY={},S_MATERIAL='{}',E_DENSITY={},E_MATERIAL='{}',O_DENSITY={},O_MATERIAL='{}',N_PAIRS={},THICKNESS={},GAMMA={},ROUGHNESS_EVEN={},ROUGHNESS_ODD={})".format(
                    mlayer_filename,
                    item.reflectivityMinEnergy,
                    item.reflectivityMaxEnergy,
                    item.mlayerSubstrateDensity,
                    item.mlayerSubstrateMaterial,
                    item.mlayerEvenSublayerDensity,
                    item.mlayerEvenSublayerMaterial,
                    item.mlayerOddSublayerDensity,
                    item.mlayerOddSublayerMaterial,
                    item.mlayerBilayerNumber,
                    item.mlayerBilayerThickness,
                    item.mlayerGammaRatio,
                    item.mlayerEvenRoughness,
                    item.mlayerOddRoughness,
                )
            )
            res += _field_value("oe", "file_refl", "b'{}'".format(mlayer_filename))
            res += _item_field(item, ["f_refl", "f_thick"])
    return res


def _generate_parameters_file(data, run_dir=None, is_parallel=False):
    _validate_data(data, SCHEMA)
    _scale_units(data)
    v = template_common.flatten_data(data.models, PKDict())
    r = data.report
    report_model = data.models[r]
    beamline = data.models.beamline
    v.shadowOutputFile = _SHADOW_OUTPUT_FILE
    if _has_zone_plate(beamline):
        v.zonePlateMethods = template_common.render_jinja(SIM_TYPE, v, "zone_plate.py")

    if v.simulation_sourceType == "bendingMagnet":
        v.bendingMagnetSettings = _generate_bending_magnet(data)
    elif v.simulation_sourceType == "geometricSource":
        v.geometricSourceSettings = _generate_geometric_source(data)
    elif v.simulation_sourceType == "wiggler":
        v.wigglerSettings = _generate_wiggler(data)
        v.wigglerTrajectoryFilename = _WIGGLER_TRAJECTORY_FILENAME
        v.wigglerTrajectoryInput = ""
        if data.models.wiggler.b_from in ("1", "2"):
            v.wigglerTrajectoryInput = _SIM_DATA.shadow_wiggler_file(
                data.models.wiggler.trajFile
            )
    elif v.simulation_sourceType == "undulator":
        v.undulatorSettings = template_common.render_jinja(SIM_TYPE, v, "undulator.py")

    if r == "initialIntensityReport":
        v.distanceFromSource = (
            beamline[0].position
            if beamline
            else template_common.DEFAULT_INTENSITY_DISTANCE
        )
    elif r == "beamStatisticsReport":
        v.simulation_npoint = 10000
        v.beamlineOptics = _generate_beamline_optics(data.models, calc_beam_stats=True)
        v.beamStatsFile = BEAM_STATS_FILE
        assert v.simulation_sourceType in (
            "bendingMagnet",
            "geometricSource",
            "undulator",
        )
        if v.simulation_sourceType == "geometricSource":
            if v.geometricSource_f_color == "1":
                v.photonEnergy = v.geometricSource_singleEnergyValue
            else:
                v.photonEnergy = (v.geometricSource_ph1 + v.geometricSource_ph2) / 2
        elif v.simulation_sourceType == "undulator":
            if v.undulator_select_energy == "range":
                v.photonEnergy = (v.undulator_emin + v.undulator_emax) / 2
            else:
                v.photonEnergy = v.undulator_photon_energy
        elif v.simulation_sourceType == "bendingMagnet":
            v.photonEnergy = v.bendingMagnet_ph1
        return template_common.render_jinja(SIM_TYPE, v, "beam_statistics.py")
    elif _SIM_DATA.is_watchpoint(r):
        v.beamlineOptics = _generate_beamline_optics(
            data.models, last_id=_SIM_DATA.watchpoint_id(r)
        )
    else:
        v.distanceFromSource = report_model.distanceFromSource
    return template_common.render_jinja(SIM_TYPE, v)


def _generate_screen(item):
    return (
        "\n"
        + "oe.set_empty().set_screens()"
        + _field_value("oe", "i_slit[0]", "1")
        + _field_value("oe", "k_slit[0]", 0 if item.shape == "0" else 1)
        + _field_value("oe", "i_stop[0]", 0 if item.type == "aperture" else 1)
        + _item_field(
            item,
            ["horizontalSize", "verticalSize", "horizontalOffset", "verticalOffset"],
        )
    )


def _generate_trace(
    source_distance, trace_method, count, calc_beam_stats, image_distance=0.0
):
    res = (
        _field_value("oe", "fwrite", "3")
        + _field_value("oe", "t_image", image_distance)
        + _field_value("oe", "t_source", source_distance)
    )
    if calc_beam_stats:
        res += (
            "\nbeam01 = beam.duplicate()"
            + "\nbeam01.{}(oe, {})".format(trace_method, count)
            + "\npos = calculate_stats(pos, oe, beam01)"
        )
    else:
        res += "\nbeam.{}(oe, {})".format(trace_method, count)
    return res


def _generate_wiggler(data):
    return (
        _source_field(
            data.models.electronBeam,
            ["sigmax", "sigmaz", "epsi_x", "epsi_z", "bener", "epsi_dx", "epsi_dz"],
        )
        + _source_field(data.models.wiggler, ["ph1", "ph2"])
        + _field_value("source", "fdistr", 0)
        + _field_value("source", "fsource_depth", 0)
        + _field_value("source", "f_wiggler", 1)
        + _field_value("source", "conv_fact", 100.0)
        + _field_value("source", "hdiv1", 1.0)
        + _field_value("source", "hdiv2", 1.0)
        + _field_value("source", "vdiv1", 1.0)
        + _field_value("source", "vdiv2", 1.0)
        + _field_value("source", "f_color", 0)
        + _field_value("source", "f_phot", 0)
        + _field_value(
            "source", "file_traj", "b'{}'".format(_WIGGLER_TRAJECTORY_FILENAME)
        )
    )


def _generate_zone_plate(item, source_distance, count, res, energy, calc_beam_stats):
    # all conversions to meters should be handled by ModelUnits
    res += f"""
zp = zone_plate_simulator(
    {item.zone_plate_type},
    {item.width_coating},
    {item.height},
    {item.diameter * 1e-2},
    {item.b_min},
    '{item.zone_plate_material}',
    '{item.template_material}',
    {energy} * 1e-3,
    {item.n_points},
)
"""

    # circular aperture
    res += "\noe = Shadow.OE()" + _field_value("oe", "dummy", "1.0")
    res += _generate_screen(
        PKDict(
            type="aperture",
            shape="1",
            horizontalSize=item.diameter,
            horizontalOffset=0,
            verticalSize=item.diameter,
            verticalOffset=0,
        )
    ) + _generate_trace(source_distance, "traceOE", count, calc_beam_stats)

    # lens
    count += 1
    res += "\n\noe = Shadow.OE()" + _field_value("oe", "dummy", "1.0")
    res += _item_field(
        PKDict(
            focal_x="zp.focal_distance * 1e2",
            focal_z="zp.focal_distance * 1e2",
        ),
        ["focal_x", "focal_z"],
    ) + _generate_trace(0, "traceIdealLensOE", count, calc_beam_stats)

    if not calc_beam_stats:
        # do not trace through zone plate for stats - not enough particles
        count += 1
        res += f"\n\ntrace_through_zone_plate(beam, zp, {item.last_index})\n"

    return count, res


def _init_model_units():
    def _scale(v, factor, is_native):
        scale = 0.1**factor
        return v * scale if is_native else v / scale

    def _mm2_to_cm2(v, is_native):
        return _scale(v, 2, is_native)

    def _mm3_to_cm3(v, is_native):
        return _scale(v, 3, is_native)

    def _mm4_to_cm4(v, is_native):
        return _scale(v, 4, is_native)

    def _mm5_to_cm5(v, is_native):
        return _scale(v, 5, is_native)

    res = ModelUnits(
        PKDict(
            {
                x: PKDict({y: "cm_to_m" for y in _CENTIMETER_FIELDS[x]})
                for x in _CENTIMETER_FIELDS.keys()
            }
        )
    )
    res.unit_def.grating.pkupdate(
        PKDict(
            {
                "rul_a1": _mm2_to_cm2,
                "rul_a2": _mm3_to_cm3,
                "rul_a3": _mm4_to_cm4,
                "rul_a4": _mm5_to_cm5,
                "rulingDensity": "mm_to_cm",
                "rulingDensityCenter": "mm_to_cm",
                "rulingDensityPolynomial": "mm_to_cm",
            }
        )
    )
    return res


def _has_zone_plate(beamline):
    for item in beamline:
        if item.type == "zonePlate":
            return True
    return False


def _is_disabled(item):
    return "isDisabled" in item and item.isDisabled


def _item_field(item, fields):
    return _fields("oe", item, fields)


def _parse_shadow_log(run_dir, log_filename="run.log"):
    if template_common.LogParser(
        run_dir,
        log_filename=log_filename,
        error_patterns=(r".*(invalid chemical formula)",),
        default_msg="",
    ).parse_for_errors():
        return "A mirror contains an invalid reflectivity material"
    return template_common.LogParser(
        run_dir,
        log_filename=log_filename,
        error_patterns=(r"ValueError: (.*)?",),
    ).parse_for_errors()


def _photon_energy(models):
    source_type = models.simulation.sourceType
    if source_type == "undulator":
        if models.undulator.select_energy == "range":
            return (models.undulator.emin + models.undulator.emax) / 2
        return models.undulator.photon_energy
    if source_type == "geometricSource":
        if models.geometricSource.f_color == "1":
            return models.geometricSource.singleEnergyValue
    return (models[source_type].ph1 + models[source_type].ph2) / 2


def _scale_units(data):
    for name in _MODEL_UNITS.unit_def:
        if name in data.models:
            _MODEL_UNITS.scale_to_native(name, data.models[name])
    for item in data.models.beamline:
        if item.type in _MODEL_UNITS.unit_def:
            _MODEL_UNITS.scale_to_native(item.type, item)


def _source_field(model, fields):
    return _fields("source", model, fields)


def _validate_data(data, schema):
    template_common.validate_models(data, schema)
    if data.models.simulation.sourceType == "undulator":
        und = data.models.undulator
        if und.select_energy == "single":
            und.emin = und.photon_energy
            und.emax = und.photon_energy
        if und.emin == und.emax:
            und.ng_e = 1


_MODEL_UNITS = _init_model_units()
