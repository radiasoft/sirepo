"""JSPEC execution template.

:copyright: Copyright (c) 2017-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcollections
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common, sdds_util
import glob
import math
import numpy as np
import os.path
import py.path
import re
import sdds
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

JSPEC_INPUT_FILENAME = "jspec.in"

JSPEC_LOG_FILE = "jspec.log"

JSPEC_TWISS_FILENAME = "jspec.tfs"

WANT_BROWSER_FRAME_CACHE = True

_BEAM_EVOLUTION_OUTPUT_FILENAME = "JSPEC.SDDS"

_FORCE_TABLE_FILENAME = "force_table.txt"

_ION_FILE_PREFIX = "ions"

_FIELD_MAP = PKDict(
    emitx="emit_x",
    emity="emit_y",
    dpp="dp/p",
    sigmas="sigma_s",
    rxibs="rx_ibs",
    ryibs="ry_ibs",
    rsibs="rs_ibs",
    rxecool="rx_ecool",
    ryecool="ry_ecool",
    rsecool="rs_ecool",
    fx="f_x",
    flong="f_long",
    Vlong="V_long",
    Vtrans="V_trans",
    edensity="e_density",
)

# TODO(pjm): get this from the enum?
_FIELD_LABEL = PKDict(
    f_x="Transverse Force",
    f_long="Longitudinal Force",
    V_long="Longitudinal Velocity",
    V_trans="Transverse Velocity",
    e_density="Electron Density",
)

_OPTIONAL_MADX_TWISS_COLUMNS = ["NAME", "TYPE", "COUNT", "DY", "DPY"]

_SPECIES_MASS_AND_CHARGE = PKDict(
    ALUMINUM=(25126.4878, 13),
    COPPER=(58603.6989, 29),
    DEUTERON=(1875.612928, 1),
    GOLD=(183432.7312, 79),
    HELIUM=(3755.675436, 2),
    LEAD=(193687.0203, 82),
    PROTON=(938.2720882, 1),
    RUTHENIUM=(94900.76612, 44),
    URANIUM=(221695.7759, 92),
    ZIRCONIUM=(83725.21758, 40),
)

_X_FIELD = "t"


def analysis_job_compute_particle_ranges(data, run_dir, **kwargs):
    return template_common.compute_field_range(
        data,
        _compute_range_across_files,
        run_dir,
    )


def background_percent_complete(report, run_dir, is_running):
    res = _v2_report_status(run_dir, is_running)

    # convert v2 format to original format for old client
    t = None
    for r in res.reports:
        if r.modelName == "particleAnimation":
            res.hasParticles = True
            res.frameCount = r.frameCount
        elif r.modelName == "beamEvolutionAnimation":
            t = r.lastUpdateTime
        elif r.modelName == "coolingRatesAnimation":
            res.hasRates = True
        elif r.modelName == "forceTableAnimation":
            res.hasForceTable = True
    if "frameCount" not in res and t:
        res.frameCount = t

    return res


def get_rates(run_dir):
    f = pkio.py_path(run_dir).join(JSPEC_LOG_FILE)
    assert f.exists(), "non-existent log file {}".format(f)
    o = PKDict(
        # TODO(pjm): x_range is needed for sirepo-plotting.js, need a better valid-data check
        x_range=[],
        rate=[],
        headings=[
            "Horizontal",
            "Vertical",
            "Longitudinal",
        ],
    )
    for l in pkio.read_text(f).split("\n"):
        m = re.match(r"^(.*? rate.*?)\:\s+(\S+)\s+(\S+)\s+(\S+)", l)
        if m:
            r = [m.group(1), [m.group(i) for i in range(2, 5)]]
            r[0] = re.sub(r"\(", "[", r[0])
            r[0] = re.sub(r"\)", "]", r[0])
            o.rate.append(r)
    return o


def get_data_file(run_dir, model, frame, options):
    if model in ("beamEvolutionAnimation", "coolingRatesAnimation"):
        return _BEAM_EVOLUTION_OUTPUT_FILENAME
    elif model == "forceTableAnimation":
        return _FORCE_TABLE_FILENAME
    return _ion_files(run_dir)[frame]


def post_execution_processing(success_exit, is_parallel, run_dir, **kwargs):
    if not success_exit or not is_parallel:
        return None
    return _get_time_step_warning(run_dir)


def python_source_for_model(data, model, qcall, **kwargs):
    ring = data.models.ring
    elegant_twiss_file = None
    if ring.latticeSource == "elegant":
        elegant_twiss_file = _SIM_DATA.lib_file_name_with_model_field(
            "ring", "elegantTwiss", ring.elegantTwiss
        )
    elif ring.latticeSource == "elegant-sirepo":
        elegant_twiss_file = _SIM_DATA.JSPEC_ELEGANT_TWISS_FILENAME
    convert_twiss_to_tfs = ""
    if elegant_twiss_file:
        convert_twiss_to_tfs = """
from pykern import pkconfig
pkconfig.append_load_path('sirepo')
from sirepo.template import sdds_util
sdds_util.twiss_to_madx('{}', '{}')
        """.format(
            elegant_twiss_file, JSPEC_TWISS_FILENAME
        )
    return """
{}

with open('{}', 'w') as f:
    f.write(jspec_file)
{}
import os
os.system('jspec {}')
    """.format(
        _generate_parameters_file(data),
        JSPEC_INPUT_FILENAME,
        convert_twiss_to_tfs,
        JSPEC_INPUT_FILENAME,
    )


def remove_last_frame(run_dir):
    pass


def sim_frame_beamEvolutionAnimation(frame_args):
    return _sdds_report(
        frame_args,
        str(frame_args.run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME)),
        _X_FIELD,
    )


sim_frame_coolingRatesAnimation = sim_frame_beamEvolutionAnimation


def sim_frame_forceTableAnimation(frame_args):
    return _sdds_report(
        frame_args,
        str(frame_args.run_dir.join(_FORCE_TABLE_FILENAME)),
        frame_args.x,
    )


def sim_frame_particleAnimation(frame_args):
    def _format_plot(field, sdds_units):
        field.label = _field_label(field.label, sdds_units)

    def _title(frame_args):
        settings = frame_args.sim_in.models.simulationSettings
        time = (
            settings.time
            / settings.step_number
            * settings.save_particle_interval
            * frame_args.frameIndex
        )
        if time > settings.time:
            time = settings.time
        return "Ions at time {:.2f} [s]".format(time)

    return sdds_util.SDDSUtil(
        _ion_files(frame_args.run_dir)[frame_args.frameIndex]
    ).heatmap(
        plot_attrs=PKDict(
            format_col_name=_map_field_name,
            title=_title(frame_args),
            model=template_common.model_from_frame_args(frame_args),
            format_plot=_format_plot,
        )
    )


def stateful_compute_get_elegant_sim_list(data, **kwargs):
    tp = _SIM_DATA.jspec_elegant_twiss_path()
    res = []
    for f in pkio.sorted_glob(
        _SIM_DATA.jspec_elegant_dir().join("*", tp),
    ):
        assert str(f).endswith(tp)
        i = simulation_db.sid_from_compute_file(f)
        try:
            name = simulation_db.read_json(
                simulation_db.sim_data_file("elegant", i),
            ).models.simulation.name
            res.append(PKDict(simulationId=i, name=name))
        except IOError:
            # ignore errors reading corrupted elegant sim files
            pass
    return {
        "simList": res,
    }


def validate_file(file_type, path):
    if file_type == "ring-elegantTwiss":
        return None
    assert file_type == "ring-lattice"
    for line in pkio.read_text(str(path)).split("\n"):
        # mad-x twiss column header starts with '*'
        match = re.search(r"^\*\s+(.*?)\s*$", line)
        if match:
            columns = re.split(r"\s+", match.group(1))
            is_ok = True
            for col in sdds_util.MADX_TWISS_COLUMS:
                if col in _OPTIONAL_MADX_TWISS_COLUMNS:
                    continue
                if col not in columns:
                    is_ok = False
                    break
            if is_ok:
                return None
    return "TFS file must contain columns: {}".format(
        ", ".join(sdds_util.MADX_TWISS_COLUMS)
    )


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _compute_range_across_files(run_dir, **kwargs):
    res = PKDict(
        {
            _X_FIELD: [],
        }
    )
    for v in SCHEMA.enum.BeamColumn:
        res[_map_field_name(v[0])] = []
    for v in SCHEMA.enum.CoolingRatesColumn:
        res[_map_field_name(v[0])] = []
    sdds_util.process_sdds_page(
        str(run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME)), 0, _compute_sdds_range, res
    )
    if run_dir.join(_FORCE_TABLE_FILENAME).exists():
        res2 = PKDict()
        for v in SCHEMA.enum.ForceTableColumn:
            res2[_map_field_name(v[0])] = []
            sdds_util.process_sdds_page(
                str(run_dir.join(_FORCE_TABLE_FILENAME)), 0, _compute_sdds_range, res2
            )
        res.update(res2)
    # TODO(pjm): particleAnimation dp/p collides with beamEvolutionAnimation dp/p
    ion_files = _ion_files(run_dir)
    if ion_files:
        res2 = PKDict()
        for v in SCHEMA.enum.ParticleColumn:
            res2[_map_field_name(v[0])] = []
        for filename in ion_files:
            sdds_util.process_sdds_page(filename, 0, _compute_sdds_range, res2)
        res.update(res2)
    # reverse field mapping back to enum values
    for k in _FIELD_MAP:
        v = _FIELD_MAP[k]
        if v in res:
            res[k] = res[v]
            del res[v]
    return res


def _compute_sdds_range(res, sdds_index=0):
    column_names = sdds.sddsdata.GetColumnNames(sdds_index)
    for field in res:
        values = sdds.sddsdata.GetColumn(sdds_index, column_names.index(field))
        if res[field]:
            res[field][0] = _safe_sdds_value(min(min(values), res[field][0]))
            res[field][1] = _safe_sdds_value(max(max(values), res[field][1]))
        else:
            res[field] = [_safe_sdds_value(min(values)), _safe_sdds_value(max(values))]


def _field_description(field, data):
    if not re.search(r"rx|ry|rs", field):
        return ""
    settings = data.models.simulationSettings
    ibs = settings.ibs == "1"
    e_cool = settings.e_cool == "1"
    dir = _field_direction(field)
    if "ibs" in field:
        return " - {} IBS rate".format(dir)
    if "ecool" in field:
        return " - {} electron cooling rate".format(dir)
    if ibs and e_cool:
        return " - combined electron cooling and IBS heating rate ({})".format(dir)
    if e_cool:
        return " - {} electron cooling rate".format(dir)
    if ibs:
        return " - {} IBS rate".format(dir)
    return ""


def _field_direction(field):
    if "rx" in field:
        return "horizontal"
    if "ry" in field:
        return "vertical"
    if "rs" in field:
        return "longitudinal"
    assert False, "invalid direction field: {}".format(field)


def _field_label(field, units):
    field = _FIELD_LABEL.get(field, field)
    if units == "NULL":
        return field
    return "{} [{}]".format(field, units)


def _generate_parameters_file(data):
    report = data.report if "report" in data else None
    _set_mass_and_charge(data.models.ionBeam)
    template_common.validate_models(data, simulation_db.get_schema(SIM_TYPE))
    v = template_common.flatten_data(data.models, PKDict())
    v.beamEvolutionOutputFilename = _BEAM_EVOLUTION_OUTPUT_FILENAME
    v.runSimulation = report is None or report == "animation"
    v.runRateCalculation = report is None or report == "rateCalculationReport"
    if data.models.ring.latticeSource == "madx":
        v.latticeFilename = _SIM_DATA.lib_file_name_with_model_field(
            "ring", "lattice", v.ring_lattice
        )
    else:
        v.latticeFilename = JSPEC_TWISS_FILENAME
    if v.ionBeam_beam_type == "continuous":
        v.ionBeam_rms_bunch_length = 0
    v.simulationSettings_ibs = "on" if v.simulationSettings_ibs == "1" else "off"
    v.simulationSettings_e_cool = "on" if v.simulationSettings_e_cool == "1" else "off"
    return template_common.render_jinja(SIM_TYPE, v)


def _get_time_step_warning(run_dir):
    def _get_rate(rates, i, j):
        return abs(float(rates[i][1][j]))

    def _get_max_rate(rates):
        m = _get_rate(rates, 0, 0)
        for i in range(2):
            t = rates[i][0]
            assert (
                "IBS rate" in t or "Electron cooling rate" in t
            ), "unknown rates={}".format(rates)
            for j in range(3):
                m = max(m, _get_rate(rates, i, j))
        return m

    m = _get_max_rate(get_rates(run_dir).rate)
    w = None
    r = 0.05 / m
    s = simulation_db.read_json(
        run_dir.join(template_common.INPUT_BASE_NAME),
    ).models.simulationSettings.time_step
    if s < 0.25 * r:
        w = (
            "The time step is too small. This can lead to long run times.\n"
            "Please consider increasing the total time and/or decreasing\n"
            "the number of steps."
        )
    elif s > 4 * r:
        w = (
            "The time step is too large. This can lead to innacurate results.\n"
            "Please consider decreasing the total time and/or increasing\n"
            "the number of steps."
        )
    return w


def _ion_files(run_dir):
    # sort files by file number suffix
    res = []
    for f in glob.glob(str(run_dir.join("{}*".format(_ION_FILE_PREFIX)))):
        m = re.match(r"^.*?(\d+)\.txt$", f)
        if m:
            res.append([f, int(m.group(1))])
    return [v[0] for v in sorted(res, key=lambda v: v[1])]


def _map_field_name(f):
    return _FIELD_MAP.get(f, f)


def _safe_sdds_value(v):
    if isinstance(v, float) and (math.isinf(v) or math.isnan(v)):
        return 0
    return v


def _sdds_report(frame_args, filename, x_field):
    def _force_scale_and_label_prefix(plot):
        label_prefix = ""
        # TODO(pjm): the forceScale feature makes the code unmanageable
        #  it might be simpler if this was done on the client
        if (
            "forceScale" in frame_args
            and plot.col_name in ("f_x", "f_long")
            and frame_args.forceScale == "negative"
        ):
            plot.points = [-v for v in plot.points]
            label_prefix = "-"
            if "fieldRange" in frame_args:
                r = frame_args.fieldRange[plot.label]
                frame_args.fieldRange[plot.label] = [-r[1], -r[0]]
        return label_prefix

    def _format_plot(plot, sdds_units):
        if x_field == plot.col_name:
            plot.label = _field_label(plot.col_name, sdds_units)
        else:
            plot.label = "{}{}{}".format(
                _force_scale_and_label_prefix(plot),
                _field_label(plot.col_name, sdds_units),
                _field_description(plot.col_name, frame_args.sim_in),
            )

    if "fieldRange" in frame_args.sim_in.models.particleAnimation:
        frame_args.fieldRange = frame_args.sim_in.models.particleAnimation.fieldRange
    frame_args.x = x_field

    return sdds_util.SDDSUtil(filename).lineplot(
        PKDict(
            format_col_name=_map_field_name,
            model=template_common.model_from_frame_args(frame_args),
            format_plot=_format_plot,
        )
    )


def _set_mass_and_charge(ion_beam):
    if ion_beam.particle != "OTHER":
        ion_beam.mass, ion_beam.charge_number = _SPECIES_MASS_AND_CHARGE[
            ion_beam.particle
        ]


def _v2_add_report_mtime(reports, model_name, path):
    if path.exists():
        reports.append(
            PKDict(
                modelName=model_name,
                lastUpdateTime=int(float(os.path.getmtime(str(path)))),
            )
        )


def _v2_percent_complete(settings, evolution_file):
    if not evolution_file.exists():
        return 0
    try:
        col = sdds_util.extract_sdds_column(str(evolution_file), "t", 0)
        if "values" in col:
            t_max = max(col["values"])
            if t_max and settings.time > 0:
                return 100.0 * t_max / settings.time
    except Exception:
        # TODO(pjm): sdds read may have failed, use a better exception subclass
        pass
    return 0


def _v2_report_status(run_dir, is_running):
    # forceTableAnimation
    #   _FORCE_TABLE_FILENAME exists
    #   lastUpdateTime: _FORCE_TABLE_FILENAME.lastModified
    # beamEvolutionAnimation:
    #   _BEAM_EVOLUTION_OUTPUT_FILENAME exists
    #   lastUpdateTime: _BEAM_EVOLUTION_OUTPUT_FILENAME.lastModified
    # coolingRatesAnimation
    #   _BEAM_EVOLUTION_OUTPUT_FILENAME exists
    #     and  settings.ibs == "1" or settings.e_cool == "1"
    #   lastUpdateTime: _BEAM_EVOLUTION_OUTPUT_FILENAME.lastModified
    # particleAnimation
    #   settings.model == "particle" and settings.save_particle_interval > 0:
    #   frameCount: len(_ion_files()) - is_running ? 1 : 0
    settings = simulation_db.read_json(
        run_dir.join(template_common.INPUT_BASE_NAME)
    ).models.simulationSettings
    res = PKDict(
        percentComplete=_v2_percent_complete(
            settings, run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME)
        ),
        reports=[],
    )
    if res.percentComplete:
        _v2_add_report_mtime(
            res.reports, "forceTableAnimation", run_dir.join(_FORCE_TABLE_FILENAME)
        )
        _v2_add_report_mtime(
            res.reports,
            "beamEvolutionAnimation",
            run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME),
        )
        if settings.ibs == "1" or settings.e_cool == "1":
            _v2_add_report_mtime(
                res.reports,
                "coolingRatesAnimation",
                run_dir.join(_BEAM_EVOLUTION_OUTPUT_FILENAME),
            )
        count = len(_ion_files(run_dir))
        if count > 0 and is_running:
            count -= 1
        if count:
            res.reports.append(PKDict(modelName="particleAnimation", frameCount=count))
    return res
