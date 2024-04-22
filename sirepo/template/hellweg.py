"""Hellweg execution template.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common, hellweg_dump_reader
import numpy
import os.path
import re
import rshellweg.solver
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

HELLWEG_DUMP_FILE = "all-data.bin"

HELLWEG_SUMMARY_FILE = "output.txt"

HELLWEG_INI_FILE = "defaults.ini"

HELLWEG_INPUT_FILE = "input.txt"

WANT_BROWSER_FRAME_CACHE = True

# lattice element is required so make it very short and wide drift
# needs to be 3 cells or else the Space Charge example doesn't produce correct results
_DEFAULT_DRIFT_ELEMENT = "DRIFT 1e-16 1e+16 3" + "\n"

_HELLWEG_PARSED_FILE = "PARSED.TXT"

_PARAMETER_SCALE = PKDict(
    rb=2.0,
    wav=1e6,
    wmax=1e6,
)


def analysis_job_compute_particle_ranges(data, run_dir, **kwargs):
    return template_common.compute_field_range(
        data,
        _compute_range_across_files,
        run_dir,
    )


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    dump_file = _dump_file(run_dir)
    if os.path.exists(dump_file):
        beam_header = hellweg_dump_reader.beam_header(dump_file)
        last_update_time = int(os.path.getmtime(dump_file))
        frame_count = beam_header.NPoints

        # TODO(pjm): work-around #1 for rshellweg bug for RF Fields
        if frame_count > 1:
            beam_info = hellweg_dump_reader.beam_info(
                _dump_file(run_dir),
                frame_count - 1,
            )
            if hellweg_dump_reader.get_parameter(beam_info, "z") == 0:
                frame_count -= 1

        return PKDict(
            lastUpdateTime=last_update_time,
            percentComplete=100,
            frameCount=frame_count,
            summaryData=_summary_text(run_dir),
        )
    return PKDict(
        percentComplete=100, frameCount=0, error=_parse_error_message(run_dir)
    )


def get_data_file(run_dir, model, frame, options):
    return HELLWEG_DUMP_FILE


def python_source_for_model(data, model, qcall, **kwargs):
    return """
{}
s = rshellweg.solver.BeamSolver("{}", "{}")
s.solve()
s.save_output("{}")
s.dump_bin("{}")
""".format(
        _generate_parameters_file(data, is_parallel=len(data.models.beamline)),
        HELLWEG_INI_FILE,
        HELLWEG_INPUT_FILE,
        HELLWEG_SUMMARY_FILE,
        HELLWEG_DUMP_FILE,
    )


def remove_last_frame(run_dir):
    pass


def sim_frame_beamAnimation(frame_args):
    data = simulation_db.read_json(
        frame_args.run_dir.join(template_common.INPUT_BASE_NAME)
    )
    model = data.models.beamAnimation
    model.update(frame_args)
    beam_info = hellweg_dump_reader.beam_info(
        _dump_file(frame_args.run_dir), frame_args.frameIndex
    )
    x, y = frame_args.reportType.split("-")
    values = [
        hellweg_dump_reader.get_points(beam_info, x, data.models.beam.particleKeyword),
        hellweg_dump_reader.get_points(beam_info, y, data.models.beam.particleKeyword),
    ]
    model["x"] = x
    model["y"] = y
    # see issue #872
    if not numpy.any(values):
        values = [[], []]
    return template_common.heatmap(
        values,
        model,
        PKDict(
            x_label=hellweg_dump_reader.get_label(x),
            y_label=hellweg_dump_reader.get_label(y),
            title=_report_title(frame_args.reportType, "BeamReportType", beam_info),
            z_label="Number of Particles",
            summaryData=_summary_text(frame_args.run_dir),
        ),
    )


def sim_frame_beamHistogramAnimation(frame_args):
    beam_info = hellweg_dump_reader.beam_info(
        _dump_file(frame_args.run_dir), frame_args.frameIndex
    )
    points = hellweg_dump_reader.get_points(
        beam_info, frame_args.reportType, frame_args.sim_in.models.beam.particleKeyword
    )
    hist, edges = numpy.histogram(
        points, template_common.histogram_bins(frame_args.histogramBins)
    )
    return PKDict(
        title=_report_title(
            frame_args.reportType, "BeamHistogramReportType", beam_info
        ),
        x_range=[edges[0], edges[-1]],
        y_label="Number of Particles",
        x_label=hellweg_dump_reader.get_label(frame_args.reportType),
        points=hist.T.tolist(),
    )


def sim_frame_parameterAnimation(frame_args):
    s = rshellweg.solver.BeamSolver(
        os.path.join(str(frame_args.run_dir), HELLWEG_INI_FILE),
        os.path.join(str(frame_args.run_dir), HELLWEG_INPUT_FILE),
    )
    s.load_bin(os.path.join(str(frame_args.run_dir), HELLWEG_DUMP_FILE))
    y1_var, y2_var = frame_args.reportType.split("-")
    x_field = "z"
    x = _scale_structure_parameters(s, x_field)
    y1 = _scale_structure_parameters(s, y1_var)
    y2 = _scale_structure_parameters(s, y2_var)
    # TODO(pjm): work-around #2 for rshellweg bug for RF Fields
    if x[-1] == 0:
        for v in (x, y1, y2):
            v.pop()
    y1_extent = [numpy.min(y1), numpy.max(y1)]
    y2_extent = [numpy.min(y2), numpy.max(y2)]
    return PKDict(
        title=_enum_text("ParameterReportType", frame_args.reportType),
        x_range=[x[0], x[-1]],
        y_label=hellweg_dump_reader.get_parameter_label(y1_var),
        x_label=hellweg_dump_reader.get_parameter_label(x_field),
        x_points=x,
        points=[
            y1,
            y2,
        ],
        y_range=[min(y1_extent[0], y2_extent[0]), max(y1_extent[1], y2_extent[1])],
        y1_title=hellweg_dump_reader.get_parameter_title(y1_var),
        y2_title=hellweg_dump_reader.get_parameter_title(y2_var),
    )


def sim_frame_particleAnimation(frame_args):
    x_field = "z0"
    particle_info = hellweg_dump_reader.particle_info(
        _dump_file(frame_args.run_dir),
        frame_args.reportType,
        int(frame_args.renderCount),
        frame_args.sim_in.models.beam.particleKeyword,
    )
    x = particle_info["z_values"]
    y = particle_info["y_values"]
    return PKDict(
        title=_enum_text("ParticleReportType", frame_args.reportType),
        x_range=[numpy.min(x), numpy.max(x)],
        y_label=hellweg_dump_reader.get_label(frame_args.reportType),
        x_label=hellweg_dump_reader.get_label(x_field),
        x_points=x,
        points=y,
        y_range=particle_info["y_range"],
    )


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


def _compute_range_across_files(run_dir, **kwargs):
    res = {}
    for v in SCHEMA.enum.BeamReportType:
        x, y = v[0].split("-")
        res[x] = []
        res[y] = []
    dump_file = _dump_file(run_dir)
    if not os.path.exists(dump_file):
        return res
    beam_header = hellweg_dump_reader.beam_header(dump_file)
    for frame in range(beam_header.NPoints):
        beam_info = hellweg_dump_reader.beam_info(dump_file, frame)
        for field in res:
            values = hellweg_dump_reader.get_points(
                beam_info,
                field,
                simulation_db.read_json(
                    run_dir.join(template_common.INPUT_BASE_NAME)
                ).models.beam.particleKeyword,
            )
            if not values:
                pass
            elif res[field]:
                res[field][0] = min(min(values), res[field][0])
                res[field][1] = max(max(values), res[field][1])
            else:
                res[field] = [min(values), max(values)]
    return res


def _dump_file(run_dir):
    return os.path.join(str(run_dir), HELLWEG_DUMP_FILE)


def _enum_text(enum_name, v):
    enum_values = SCHEMA["enum"][enum_name]
    for e in enum_values:
        if e[0] == v:
            return e[1]
    raise RuntimeError("invalid enum value: {}, {}".format(enum_values, v))


def _generate_beam(models):
    # BEAM SPH2D 0.564 -15 5 NORM2D 0.30 0.0000001 90 180
    beam_def = models.beam.beamDefinition
    if beam_def == "transverse_longitude":
        return "BEAM {} {}".format(
            _generate_transverse_dist(models), _generate_longitude_dist(models)
        )
    if beam_def == "cst_pit":
        return "BEAM CST_PIT {} {}".format(
            _SIM_DATA.lib_file_name_with_model_field(
                "beam", "cstFile", models.beam.cstFile
            ),
            "COMPRESS" if models.beam.cstCompress else "",
        )
    if beam_def == "cst_pid":
        return "BEAM CST_PID {} {}".format(
            _SIM_DATA.lib_file_name_with_model_field(
                "beam", "cstFile", models.beam.cstFile
            ),
            _generate_energy_phase_distribution(models.energyPhaseDistribution),
        )
    raise RuntimeError("invalid beam def: {}".format(beam_def))


def _generate_cell_params(el):
    # TODO(pjm): add an option field to select auto-calculate
    if el.attenuation == 0 and el.aperture == 0:
        return "{} {} {}".format(
            el.phaseAdvance, el.phaseVelocity, el.acceleratingInvariant
        )
    return "{} {} {} {} {}".format(
        el.phaseAdvance,
        el.phaseVelocity,
        el.acceleratingInvariant,
        el.attenuation,
        el.aperture,
    )


def _generate_charge(models):
    if models.beam.spaceCharge == "none":
        return ""
    return "SPCHARGE {} {}".format(
        models.beam.spaceCharge.upper(), models.beam.spaceChargeCore
    )


def _generate_particle_species(models):
    p = models.beam.particleKeyword.upper()
    if p == "IONS":
        return "PARTICLES {} {} {}".format(
            p,
            models.beam.particleParamA,
            models.beam.particleParamQ,
        )
    return "PARTICLES {}".format(p)


def _generate_current(models):
    return "CURRENT {} {}".format(models.beam.current, models.beam.numberOfParticles)


def _generate_energy_phase_distribution(dist):
    return "{} {} {}".format(
        dist.meanPhase,
        dist.phaseLength,
        dist.phaseDeviation if dist.distributionType == "gaussian" else "",
    )


def _generate_lattice(models):
    res = ""
    for el in models.beamline:
        if el.type == "powerElement":
            res += "POWER {} {} {}".format(el.inputPower, el.frequency, el.phaseShift)
        elif el.type == "cellElement":
            res += "CELL {}".format(_generate_cell_params(el))
            has_cell_or_drift = True
        elif el.type == "cellsElement":
            res += "CELLS {} {}".format(el.repeat, _generate_cell_params(el))
            has_cell_or_drift = True
        elif el.type == "driftElement":
            res += "DRIFT {} {} {}".format(el.length, el.radius, el.meshPoints)
            has_cell_or_drift = True
        elif el.type == "saveElement":
            # TODO(pjm): implement this
            pass
        else:
            raise RuntimeError("unknown element type: {}".format(el.type))
        res += "\n"
    return res


def _generate_longitude_dist(models):
    dist_type = models.beam.longitudinalDistribution
    if dist_type == "norm2d":
        dist = models.energyPhaseDistribution
        if dist.distributionType == "uniform":
            return "NORM2D {} {} {} {}".format(
                dist.meanEnergy, dist.energySpread, dist.meanPhase, dist.phaseLength
            )
        if dist.distributionType == "gaussian":
            return "NORM2D {} {} {} {} {} {}".format(
                dist.meanEnergy,
                dist.energySpread,
                dist.energyDeviation,
                dist.meanPhase,
                dist.phaseLength,
                dist.phaseDeviation,
            )
        raise RuntimeError(
            "unknown longitudinal distribution type: {}".format(
                models.longitudinalDistribution.distributionType
            )
        )
    if dist_type == "file1d":
        return "FILE1D {} {}".format(
            _SIM_DATA.lib_file_name_with_model_field(
                "beam", "longitudinalFile1d", models.beam.longitudinalFile1d
            ),
            _generate_energy_phase_distribution(models.energyPhaseDistribution),
        )
    if dist_type == "file2d":
        return "FILE2D {}".format(
            _SIM_DATA.lib_file_name_with_model_field(
                "beam", "transversalFile2d", models.beam.transversalFile2d
            )
        )

    raise RuntimeError(
        "unknown longitudinal distribution: {}".format(
            models.beam.longitudinalDistribution
        )
    )


def _generate_options(models):
    if models.simulationSettings.allowBackwardWaves == "1":
        return "OPTIONS REVERSE"
    return ""


def _generate_parameters_file(data, run_dir=None, is_parallel=False):
    template_common.validate_models(data, SCHEMA)
    v = template_common.flatten_data(data["models"], PKDict())
    v["optionsCommand"] = _generate_options(data["models"])
    v["solenoidCommand"] = _generate_solenoid(data["models"])
    v["beamCommand"] = _generate_beam(data["models"])
    v["currentCommand"] = _generate_current(data["models"])
    v["chargeCommand"] = _generate_charge(data["models"])
    v["particleSpeciesCommand"] = _generate_particle_species(data["models"])
    if is_parallel:
        v["latticeCommands"] = _generate_lattice(data["models"])
    else:
        v["latticeCommands"] = _DEFAULT_DRIFT_ELEMENT
    v.iniFile = HELLWEG_INI_FILE
    v.inputFile = HELLWEG_INPUT_FILE
    v.outputFile = HELLWEG_SUMMARY_FILE
    v.dumpFile = HELLWEG_DUMP_FILE
    return template_common.render_jinja(SIM_TYPE, v)


def _generate_solenoid(models):
    solenoid = models.solenoid
    if solenoid.sourceDefinition == "none":
        return ""
    if solenoid.sourceDefinition == "values":
        # TODO(pjm): latest version also has solenoid.fringeRegion
        return "SOLENOID {} {} {}".format(
            solenoid.fieldStrength, solenoid.length, solenoid.z0
        )
    if solenoid.sourceDefinition == "file":
        return "SOLENOID {}".format(
            _SIM_DATA.lib_file_name_with_model_field(
                "solenoid", "solenoidFile", solenoid.solenoidFile
            )
        )
    raise RuntimeError(
        "unknown solenoidDefinition: {}".format(solenoid.sourceDefinition)
    )


def _generate_transverse_dist(models):
    dist_type = models.beam.transversalDistribution
    if dist_type == "twiss4d":
        dist = models.twissDistribution
        return "TWISS4D {} {} {} {} {} {}".format(
            dist.horizontalAlpha,
            dist.horizontalBeta,
            dist.horizontalEmittance,
            dist.verticalAlpha,
            dist.verticalBeta,
            dist.verticalEmittance,
        )
    if dist_type == "sph2d":
        dist = models.sphericalDistribution
        if dist.curvature == "flat":
            dist.curvatureFactor = 0
        return "SPH2D {} {} {}".format(
            dist.radialLimit, dist.curvatureFactor, dist.thermalEmittance
        )
    if dist_type == "ell2d":
        dist = models.ellipticalDistribution
        return "ELL2D {} {} {} {}".format(
            dist.aX, dist.bY, dist.rotationAngle, dist.rmsDeviationFactor
        )
    beam = models.beam
    if dist_type == "file2d":
        return "FILE2D {}".format(
            _SIM_DATA.lib_file_name_with_model_field(
                "beam", "transversalFile2d", beam.transversalFile2d
            )
        )
    if dist_type == "file4d":
        return "FILE4D {}".format(
            _SIM_DATA.lib_file_name_with_model_field(
                "beam", "transversalFile4d", beam.transversalFile4d
            )
        )
    raise RuntimeError("unknown transverse distribution: {}".format(dist_type))


def _parse_error_message(run_dir):
    path = os.path.join(str(run_dir), _HELLWEG_PARSED_FILE)
    if not os.path.exists(path):
        return "No elements generated"
    text = pkio.read_text(str(path))
    for line in text.split("\n"):
        match = re.search(r"^ERROR:\s(.*)$", line)
        if match:
            return match.group(1)
    return "No output generated"


def _report_title(report_type, enum_name, beam_info):
    return "{}, z={:.4f} cm".format(
        _enum_text(enum_name, report_type),
        100 * hellweg_dump_reader.get_parameter(beam_info, "z"),
    )


def _scale_structure_parameters(solver, field):
    v = solver.get_structure_parameters(hellweg_dump_reader.parameter_index(field))
    if field in _PARAMETER_SCALE:
        return (_PARAMETER_SCALE[field] * numpy.array(v)).tolist()
    return v


def _summary_text(run_dir):
    return pkio.read_text(os.path.join(str(run_dir), HELLWEG_SUMMARY_FILE))
