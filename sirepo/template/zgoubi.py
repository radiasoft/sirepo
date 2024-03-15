"""zgoubi execution template.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import lattice, template_common, zgoubi_importer, zgoubi_parser
import copy
import io
import jinja2
import locale
import math
import numpy as np
import py.path
import re
import sirepo.sim_data
import zipfile

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

BUNCH_SUMMARY_FILE = "bunch.json"

WANT_BROWSER_FRAME_CACHE = True

TUNES_INPUT_FILE = "tunesFromFai.In"

_ELEMENT_NAME_MAP = PKDict(
    {
        "FFAG": "FFA",
        "FFAG-SPI": "FFA-SPI",
    }
)

_TUNES_FILE = "tunesFromFai_spctra.Out"

_ZGOUBI_COMMAND_FILE = "zgoubi.dat"

_ZGOUBI_FAI_DATA_FILE = "zgoubi.fai"

_ZGOUBI_FIT_VALUES_FILE = "zgoubi.FITVALS.out"

_ZGOUBI_PLT_DATA_FILE = "zgoubi.plt"

_ZGOUBI_LOG_FILE = "zgoubi.res"

_ZGOUBI_TWISS_FILE = "zgoubi.TWISS.out"

_INITIAL_PHASE_MAP = PKDict(
    D1="Do1",
    time="to",
)

_MAGNET_TYPE_TO_MOD = PKDict(
    cartesian=PKDict(
        {
            "2d-sf": "0",
            "2d-sf-ags": "3",
            "2d-sf-ags-p": "3.1",
            "2d-mf-f": "15.{{ fileCount }}",
            "3d-mf-2v": "0",
            "3d-mf-1v": "1",
            "3d-sf-2v": "12",
            "3d-sf-1v": "12.1",
            "3d-2f-8v": "12.2",
            "3d-mf-f": "15.{{ fileCount }}",
        }
    ),
    cylindrical=PKDict(
        {
            "2d-mf-f": "25.{{ fileCount }}",
            "3d-sf-4v": "20",
            "2d-mf-f-2v": "22.{{ fileCount }}",
            "3d-mf-f-2v": "22.{{ fileCount }}",
            "3d-sf": "24",
        }
    ),
)

_ANIMATION_FIELD_INFO = PKDict(
    Do1=["dp/p₀", 1],
    Yo=["Y₀ [m]", 0.01],
    To=["Y'₀ [rad]", 0.001],
    Zo=["Z₀ [m]", 0.01],
    Po=["Z'₀ [rad]", 0.001],
    So=["s₀ [m]", 0.01],
    to=["t₀", 1],
    D1=["dp/p", 1],
    Y=["Y [m]", 0.01],
    X=["X [m]", 0.01],
    YDY=["Y [m]", 0.01],
    T=["Y' [rad]", 0.001],
    Z=["Z [m]", 0.01],
    P=["Z' [rad]", 0.001],
    S=["s [m]", 0.01],
    time=["t [s]", 1e-6],
    RET=["RF Phase [rad]", 1],
    DPR=["dp/p", 1e6],
    ENEKI=["Kenetic Energy [eV]", 1e6],
    ENERG=["Energy [eV]", 1e6],
    IPASS=["Turn Number", 1],
    SX=["Spin X", 1],
    SY=["Spin Y", 1],
    SZ=["Spin Z", 1],
    BX=["Bx [G]", 1000],
    BY=["By [G]", 1000],
    BZ=["Bz [G]", 1000],
    EX=["Ex [V/m]", 1],
    EY=["Ey [V/m]", 1],
    EZ=["Ez [V/m]", 1],
)

# TODO(pjm): move to jinja file?
_FAKE_ELEMENT_TEMPLATES = PKDict(
    AUTOREF="""
 'AUTOREF' {{ name }}
{{ I }}
{{ XCE }} {{ YCE }} {{ ALE }}
""",
    CAVITE="""
 'CAVITE' {{ name }}
{{ IOPT }}
{% if IOPT in ('0', '1', '2', '3') -%}
{{ L }} {{ h }}
{{ V }} {{ sig_s }}
{%- elif IOPT == '7' -%}
0 {{ f_RF }}
{{ V }} {{ sig_s }}
{%- elif IOPT == '10' -%}
{{ l }} {{ f_RF }} {{ ID }}
{{ V }} {{ sig_s }} {{ IOP }}
{%- endif -%}
""",
    CHANGREF2="""
 'CHANGREF' {{ name }}
{% for transform in subElements -%}
{%- if transform['transformType'] == 'none' -%}
{%- if subElements|length == 1 -%}
 XS 0
{%- endif %}
{%- else %}
 {{- transform.transformType }} {{ transform.transformValue }}{{ ' ' -}}
{%- endif -%}
{%- endfor %}
""",
    COLLIMA="""
 'COLLIMA'
{{ IA }}
{{ IFORM }} {{ C1 }} {{ C2 }} {{ C3  }} {{ C4 }}
""",
    FFA="""
 'FFAG' {{ name }}
{{ IL }}
{{ N }} {{ AT }} {{ RM }}
{% for dipole in dipoles -%}
{{ dipole.ACN }} {{ dipole.DELTA_RM }} {{ dipole.BZ_0 }} {{ dipole.K }}
{{ dipole.G0_E }} {{ dipole.KAPPA_E }}
0 {{ dipole.CE_0 }} {{ dipole.CE_1 }} {{ dipole.CE_2 }} {{ dipole.CE_3 }} {{ dipole.CE_4 }} {{ dipole.CE_5 }} {{ dipole.SHIFT_E }}
{{ dipole.OMEGA_E }} {{ dipole.THETA_E }} {{ dipole.R1_E }} {{ dipole.U1_E }} {{ dipole.U2_E }} {{ dipole.R2_E }}
{{ dipole.G0_S }} {{ dipole.KAPPA_S }}
0 {{ dipole.CS_0 }} {{ dipole.CS_1 }} {{ dipole.CS_2 }} {{ dipole.CS_3 }} {{ dipole.CS_4 }} {{ dipole.CS_5 }} {{ dipole.SHIFT_S }}
{{ dipole.OMEGA_S }} {{ dipole.THETA_S }} {{ dipole.R1_S }} {{ dipole.U1_S }} {{ dipole.U2_S }} {{ dipole.R2_S }}
{{ dipole.G0_L }} {{ dipole.KAPPA_L }}
0 {{ dipole.CL_0 }} {{ dipole.CL_1 }} {{ dipole.CL_2 }} {{ dipole.CL_3 }} {{ dipole.CL_4 }} {{ dipole.CL_5 }} {{ dipole.SHIFT_L }}
{{ dipole.OMEGA_L }} {{ dipole.THETA_L }} {{ dipole.R1_L }} {{ dipole.U1_L }} {{ dipole.U2_L }} {{ dipole.R2_L }}
{% endfor %}
{{- KIRD }} {{ RESOL }}
{{ XPAS }}
{{ KPOS }}{{ ' ' -}}
{%- if KPOS == '1' %}
{{- DP }}
{%- else %}
{{- RE }} {{ TE }} {{ RS }} {{ TS }}
{%- endif -%}
""",
    FFA_SPI="""
 'FFAG-SPI' {{ name }}
{{ IL }}
{{ N }} {{ AT }} {{ RM }}
{% for dipole in dipoles -%}
{{ dipole.ACN }} {{ dipole.DELTA_RM }} {{ dipole.BZ_0 }} {{ dipole.K }}
{{ dipole.G0_E }} {{ dipole.KAPPA_E }}
0 {{ dipole.CE_0 }} {{ dipole.CE_1 }} {{ dipole.CE_2 }} {{ dipole.CE_3 }} {{ dipole.CE_4 }} {{ dipole.CE_5 }} {{ dipole.SHIFT_E }}
{{ dipole.OMEGA_E }} {{ dipole.XI_E }} 0 0 0 0
{{ dipole.G0_S }} {{ dipole.KAPPA_S }}
0 {{ dipole.CS_0 }} {{ dipole.CS_1 }} {{ dipole.CS_2 }} {{ dipole.CS_3 }} {{ dipole.CS_4 }} {{ dipole.CS_5 }} {{ dipole.SHIFT_S }}
{{ dipole.OMEGA_S }} {{ dipole.XI_S }} 0 0 0 0
{{ dipole.G0_L }} {{ dipole.KAPPA_L }}
0 {{ dipole.CL_0 }} {{ dipole.CL_1 }} {{ dipole.CL_2 }} {{ dipole.CL_3 }} {{ dipole.CL_4 }} {{ dipole.CL_5 }} {{ dipole.SHIFT_L }}
{{ dipole.OMEGA_L }} {{ dipole.XI_L }} 0 0 0 0
{% endfor %}
{{- KIRD }} {{ RESOL }}
{{ XPAS }}
{{ KPOS }}{{ ' ' -}}
{%- if KPOS == '1' %}
{{- DP }}
{%- else %}
{{- RE }} {{ TE }} {{ RS }} {{ TS }}
{%- endif -%}
""",
    SOLENOID="""
 'SOLENOID'
{{ IL }}
{{ l }} {{ R_0 }} {{ B_0 }} {{ MODL }}
{{ X_E }} {{ X_S }}
{{ XPAS }}
{{ KPOS }} {{ XCE }} {{ YCE }} {{ ALE }}
""",
    SPINR="""
 'SPINR' {{ name }}
{{ IOPT }}
{% if IOPT in ('0', '1') -%}
{{ phi }} {{ mu }}
{% else -%}
{{ phi }} {{ B }} {{ B_0 }} {{ C_0 }} {{ C_1 }} {{ C_2 }} {{ C_3 }}
{% endif -%}
""",
    TOSCA="""
 'TOSCA' {{ name }}
0 {{ IL }}
{{ BNORM }} {{ XN }} {{ YN }} {{ ZN }}
{{ name }} HEADER_{{ headerLineCount -}}
{%- if flipX == '1' %} FLIP {% endif -%}
{%- if zeroBXY == '1' %} ZroBXY {% endif -%}
{%- if normalizeHelix == '1' %} RHIC_helix {% endif %}
{{ IX }} {{ IY }} {{ IZ }} {{ MOD -}}
{%- if hasFields %} {{ field1 }} {{ field2 }} {{ field3 }} {{ field4 }}{% endif %}
{%- for fileName in fileNames %}
{{ fileName -}}
{% endfor %}
{{ ID }} {{ A }} {{ B }} {{ C }} {{ Ap }} {{ Bp }} {{ Cp }} {{ App }} {{ Bpp }} {{ Cpp }}
{{ IORDRE }}
{{ XPAS }}
{% if meshType == 'cartesian' -%}
{{ KPOS }} {{ XCE }} {{ YCE }} {{ ALE }}
{%- else -%}
{{ KPOS }}
{{ RE }} {{ TE }} {{ RS }} {{ TS }}
{% endif -%}
""",
)

_PYZGOUBI_FIELD_MAP = PKDict(
    l="XL",
    plt="label2",
)

_REPORT_ENUM_INFO = PKDict(
    twissReport="TwissParameter",
    twissReport2="TwissParameter",
    opticsReport="OpticsParameter",
)

_TWISS_SUMMARY_LABELS = PKDict(
    LENGTH="Beamline length [m]",
    ORBIT5="Orbit5 [m]",
    ALFA="Momentum compaction factor",
    GAMMATR="Transition energy gamma",
    DELTAP="Energy difference",
    ENERGY="Particle energy [GeV]",
    GAMMA="Particle gamma",
    Q1="Horizontal tune (fractional)",
    DQ1="Horizontal chromaticity",
    BETXMIN="Horizontal minimum beta [m]",
    BETXMAX="Horizontal maximum beta [m]",
    DXMIN="Horizontal minimum dispersion [m]",
    DXMAX="Horizontal maximum dispersion [m]",
    DXRMS="Horizontal RMS dispersion [m]",
    XCOMIN="Horizontal closed orbit minimum deviation [m]",
    XCOMAX="Horizontal closed orbit maximum deviation [m]",
    XCORMS="Horizontal closed orbit RMS deviation [m]",
    Q2="Vertical tune (fractional)",
    DQ2="Vertical chromaticity",
    BETYMIN="Vertical minimum beta [m]",
    BETYMAX="Vertical maximum beta [m]",
    DYMIN="Vertical minimum dispersion [m]",
    DYMAX="Vertical maximum dispersion [m]",
    DYRMS="Vertical RMS dispersion [m]",
    YCOMIN="Vertical closed orbit minimum deviation [m]",
    YCOMAX="Vertical closed orbit maximum deviation [m]",
    YCORMS="Vertical closed orbit RMS deviation [m]",
)


class _ZgoubiLogParser(template_common.LogParser):
    def __init__(self, run_dir, **kwargs):
        super().__init__(run_dir, **kwargs)
        self.elements_by_num = PKDict()

    def _parse_log_line(self, line):
        match = re.search(r"^ (\'\w+\'.*?)\s+(\d+)$", line)
        if match:
            self.element_by_num[match.group(2)] = match.group(1)
            return
        if re.search("all particles lost", line):
            return line
        if re.search("charge found null", line):
            return line
        match = re.search(r"Enjob occured at element # (\d+)", line)
        if match:
            res = "{}\n".format(line)
            num = match.group(1)
            if num in element_by_num:
                res = "  element # {}: {}\n".format(num, self.element_by_num[num])
            return res
        return None


def analysis_job_compute_particle_ranges(data, run_dir, **kwargs):
    return template_common.compute_field_range(
        data,
        _compute_range_across_frames,
        run_dir,
    )


def background_percent_complete(report, run_dir, is_running):
    error = ""
    if not is_running:
        show_tunes_report = False
        show_spin_3d = False
        in_file = run_dir.join("{}.json".format(template_common.INPUT_BASE_NAME))
        if in_file.exists():
            data = simulation_db.read_json(
                run_dir.join(template_common.INPUT_BASE_NAME)
            )
            show_tunes_report = (
                _particle_count(data) <= SCHEMA.constants.maxFilterPlotParticles
                and data.models.simulationSettings.npass >= 10
            )
            show_spin_3d = data.models.SPNTRK.KSO == "1"
        count = read_frame_count(run_dir)
        if count:
            plt_file = run_dir.join(_ZGOUBI_PLT_DATA_FILE)
            return PKDict(
                hasPlotFile=plt_file.exists(),
                percentComplete=100,
                frameCount=count,
                showTunesReport=show_tunes_report,
                showSpin3d=show_spin_3d,
            )
        else:
            error = _parse_zgoubi_log(run_dir)
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    if error:
        res.error = error
    return res


def column_data(col, col_names, rows):
    idx = col_names.index(col)
    assert idx >= 0, "invalid col: {}".format(col)
    res = []
    for row in rows:
        res.append(float(row[idx]))
    return res


def extract_first_twiss_row(run_dir):
    col_names, rows = _read_data_file(py.path.local(run_dir).join(_ZGOUBI_TWISS_FILE))
    return col_names, rows[0]


def extract_tunes_report(run_dir, data):
    report = data.models.tunesReport
    assert (
        report.turnStart < data.models.simulationSettings.npass
    ), "Turn Start is greater than Number of Turns"
    col_names, rows = _read_data_file(
        py.path.local(run_dir).join(_TUNES_FILE), mode="header"
    )
    # actual columns appear at end of each data line, not in file header
    col_names = [
        "qx",
        "amp_x",
        "qy",
        "amp_y",
        "ql",
        "amp_l",
        "kpa",
        "kpb",
        "kt",
        "nspec",
    ]
    plots = []
    x = []

    if report.particleSelector == "all":
        axis = report.plotAxis
        title = template_common.enum_text(SCHEMA, "TunesAxis", axis)
        x_idx = col_names.index("q{}".format(axis))
        y_idx = col_names.index("amp_{}".format(axis))
        p_idx = col_names.index("nspec")
        current_p = -1
        for row in rows:
            p = row[p_idx]
            if current_p != p:
                current_p = p
                plots.append(
                    PKDict(
                        points=[],
                        label="Particle {}".format(current_p),
                    )
                )
                x = []
            x.append(float(row[x_idx]))
            plots[-1].points.append(float(row[y_idx]))
    else:
        title = "Tunes, Particle {}".format(report.particleSelector)
        for axis in ("x", "y"):
            x_idx = col_names.index("q{}".format(axis))
            y_idx = col_names.index("amp_{}".format(axis))
            points = []
            for row in rows:
                if axis == "x":
                    x.append(float(row[x_idx]))
                points.append(float(row[y_idx]))
            plots.append(
                PKDict(
                    label=template_common.enum_text(SCHEMA, "TunesAxis", axis),
                    points=points,
                )
            )
    for plot in plots:
        plot.label += ", {}".format(_peak_x(x, plot.points))
    if report.plotScale == "linear":
        # normalize each plot to 1.0 and show amplitude in label
        for plot in plots:
            maxp = max(plot.points)
            if maxp != 0:
                plot.points = (np.array(plot.points) / maxp).tolist()
            plot.label += ", amplitude: {}".format(_format_exp(maxp))

    return template_common.parameter_plot(
        x,
        plots,
        {},
        PKDict(
            title=title,
            y_label="",
            x_label="",
        ),
        plot_colors=[
            "#1f77b4",
            "#ff7f0e",
            "#2ca02c",
            "#d62728",
            "#9467bd",
            "#8c564b",
            "#e377c2",
            "#7f7f7f",
            "#bcbd22",
            "#17becf",
        ],
    )


def get_data_file(run_dir, model, frame, options):
    if options.suffix == _ZGOUBI_COMMAND_FILE:
        return TUNES_INPUT_FILE if model == "tunesReport" else _ZGOUBI_COMMAND_FILE
    elif model == "elementStepAnimation":
        return _ZGOUBI_PLT_DATA_FILE
    elif model == "opticsReport" or "twissReport" in model:
        return _ZGOUBI_TWISS_FILE
    return _ZGOUBI_FAI_DATA_FILE


def post_execution_processing(success_exit, is_parallel, run_dir, **kwargs):
    if success_exit:
        return None
    if not is_parallel:
        return _parse_zgoubi_log(run_dir)
    return None


def prepare_sequential_output_file(run_dir, data):
    report = data.report
    if "bunchReport" in report or "twissReport" in report or "opticsReport" in report:
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            save_sequential_report_data(data, run_dir)


def python_source_for_model(data, qcall, model=None, **kwargs):
    return _generate_parameters_file(data)


def read_frame_count(run_dir):
    data_file = run_dir.join(_ZGOUBI_FAI_DATA_FILE)
    if data_file.exists():
        col_names, rows = _read_data_file(data_file)
        ipasses = _ipasses_for_data(col_names, rows)
        return len(ipasses) + 1
    return 0


def remove_last_frame(run_dir):
    pass


def save_sequential_report_data(data, run_dir):
    report_name = data.report
    if "twissReport" in report_name or "opticsReport" in report_name:
        enum_name = _REPORT_ENUM_INFO[report_name]
        report = data.models[report_name]
        plots = []
        col_names, rows = _read_data_file(
            py.path.local(run_dir).join(_ZGOUBI_TWISS_FILE)
        )
        error = ""
        for f in ("y1", "y2", "y3"):
            if report[f] == "none":
                continue
            points = column_data(report[f], col_names, rows)
            if any(map(lambda x: math.isnan(x), points)):
                error = "Twiss data could not be computed for {}".format(
                    template_common.enum_text(SCHEMA, enum_name, report[f]),
                )
                break
            plots.append(
                PKDict(
                    points=points,
                    label=template_common.enum_text(SCHEMA, enum_name, report[f]),
                )
            )
        if error:
            res = PKDict(
                error=error,
            )
        else:
            # TODO(pjm): use template_common
            x = column_data("sums", col_names, rows)
            res = PKDict(
                title="",
                x_range=[min(x), max(x)],
                y_label="",
                x_label="s [m]",
                x_points=x,
                plots=plots,
                y_range=template_common.compute_plot_color_and_range(plots),
                summaryData=_read_twiss_header(run_dir),
            )
    elif report_name == "twissSummaryReport":
        res = PKDict(
            # TODO(pjm): x_range requied by sirepo-plotting.js
            x_range=[],
            summaryData=_read_twiss_header(run_dir),
        )
    elif "bunchReport" in report_name:
        report = data.models[report_name]
        col_names, rows = _read_data_file(
            py.path.local(run_dir).join(_ZGOUBI_FAI_DATA_FILE)
        )
        res = _extract_heatmap_data(report, col_names, rows, "")
        summary_file = py.path.local(run_dir).join(BUNCH_SUMMARY_FILE)
        if summary_file.exists():
            res.summaryData = PKDict(bunch=simulation_db.read_json(summary_file))
    else:
        raise AssertionError("unknown report: {}".format(report_name))
    template_common.write_sequential_result(res, run_dir=run_dir)


def sim_frame(frame_args):
    r = frame_args.frameReport
    if "bunchAnimation" in r or r in ("energyAnimation", "elementStepAnimation"):
        return _extract_animation(frame_args)
    if r == "particleAnimation":
        return _extract_spin_3d(frame_args)
    return None


def stateful_compute_import_file(data, **kwargs):
    return PKDict(
        imported_data=zgoubi_importer.import_file(data.args.file_as_str),
    )


def stateful_compute_tosca_info(data, **kwargs):
    return zgoubi_importer.tosca_info(data.args.tosca)


def write_parameters(
    data, run_dir, is_parallel, python_file=template_common.PARAMETERS_PYTHON_FILE
):
    pkio.write_text(
        run_dir.join(python_file),
        _generate_parameters_file(data),
    )
    # unzip the required magnet files
    for el in data.models.elements:
        if el.type != "TOSCA":
            continue
        filename = str(
            run_dir.join(
                _SIM_DATA.lib_file_name_with_model_field(
                    "TOSCA", "magnetFile", el.magnetFile
                )
            )
        )
        if zgoubi_importer.is_zip_file(filename):
            with zipfile.ZipFile(filename, "r") as z:
                for info in z.infolist():
                    if info.filename in el.fileNames:
                        z.extract(info, str(run_dir))


def _compute_range_across_frames(run_dir, **kwargs):
    res = PKDict()
    for v in SCHEMA.enum.PhaseSpaceCoordinate:
        res[v[0]] = []
    for v in SCHEMA.enum.EnergyPlotVariable:
        res[v[0]] = []
    col_names, rows = _read_data_file(run_dir.join(_ZGOUBI_FAI_DATA_FILE))
    for field in res:
        values = column_data(field, col_names, rows)
        initial_field = _initial_phase_field(field)
        if initial_field in col_names:
            values += column_data(initial_field, col_names, rows)
        if res[field]:
            res[field][0] = min(min(values), res[field][0])
            res[field][1] = max(max(values), res[field][1])
        else:
            res[field] = [min(values), max(values)]
    for field in list(res.keys()):
        factor = _ANIMATION_FIELD_INFO[field][1]
        res[field][0] *= factor
        res[field][1] *= factor
        res[_initial_phase_field(field)] = res[field]
    return res


def _2d_range(rows):
    # returns min, max from a set of 2d data
    # the rows may have an uneven shape, this works when np.amin(), np.amax() doesn't
    vmax = vmin = rows[0][0]
    for row in rows:
        for v in row:
            if v > vmax:
                vmax = v
            elif v < vmin:
                vmin = v
    return [vmin, vmax]


def _extract_animation(frame_args):
    r = frame_args.frameReport
    frame_index = frame_args.frameIndex
    is_frame_0 = False
    # fieldRange is store on the bunchAnimation
    model = frame_args.sim_in.models.bunchAnimation
    if r in ("energyAnimation", "elementStepAnimation"):
        model.update(frame_args.sim_in.models.energyAnimation)
        frame_index += 1
    else:
        # bunchAnimations
        # remap frame 0 to use initial "o" values from frame 1
        if frame_index == 0:
            is_frame_0 = True
            for f in ("x", "y"):
                frame_args[f] = _initial_phase_field(frame_args[f])
            frame_index = 1
    model.update(frame_args)
    if r == "elementStepAnimation":
        col_names, all_rows = _read_data_file(
            frame_args.run_dir.join(_ZGOUBI_PLT_DATA_FILE)
        )
    else:
        col_names, all_rows = _read_data_file(
            frame_args.run_dir.join(_ZGOUBI_FAI_DATA_FILE)
        )
    ipasses = _ipasses_for_data(col_names, all_rows)
    ipass = int(ipasses[frame_index - 1])
    rows = []
    ipass_index = int(col_names.index("IPASS"))
    it_index = int(col_names.index("IT"))
    kex_index = int(col_names.index("KEX"))
    it_filter = None
    if _particle_count(frame_args.sim_in) <= SCHEMA.constants.maxFilterPlotParticles:
        if frame_args.particleSelector != "all":
            it_filter = frame_args.particleSelector

    count = 0
    el_names = []
    for row in all_rows:
        if not is_frame_0:
            if row[kex_index] != "1":
                # particle isn't active
                continue
        if str(frame_args.showAllFrames) == "1":
            if it_filter and row[it_index] != it_filter:
                continue
            rows.append(row)
        elif int(row[ipass_index]) == ipass:
            rows.append(row)
    if str(frame_args.showAllFrames) == "1":
        title = "All Frames"
        if it_filter:
            title += ", Particle {}".format(it_filter)
        if model.plotRangeType == "fit":
            # unset 'fit' plot - all frames are shown
            model.plotRangeType = "none"
    else:
        title = "Initial Distribution" if is_frame_0 else "Pass {}".format(ipass)
    if frame_args.get("plotType") == "particle":
        return _extract_particle_data(model, col_names, rows, title)
    return _extract_heatmap_data(model, col_names, rows, title)


def _extract_heatmap_data(report, col_names, rows, title):
    x_info = _ANIMATION_FIELD_INFO[report.x]
    y_info = _ANIMATION_FIELD_INFO[report.y]
    x = np.array(column_data(report.x, col_names, rows)) * x_info[1]
    y = np.array(column_data(report.y, col_names, rows)) * y_info[1]
    return template_common.heatmap(
        [x, y],
        report,
        PKDict(
            x_label=x_info[0],
            y_label=y_info[0],
            title=title,
            z_label="Number of Particles",
        ),
    )


def _extract_particle_data(report, col_names, rows, title):
    x_info = _ANIMATION_FIELD_INFO[report.x]
    y_info = _ANIMATION_FIELD_INFO[report.y]
    x = np.array(column_data(report.x, col_names, rows)) * x_info[1]
    y = np.array(column_data(report.y, col_names, rows)) * y_info[1]
    it = column_data("IT", col_names, rows)
    x_points = []
    points = []
    if "ENEKI" in col_names:
        # zgoubi.fai
        points_by_num = {}
        for idx in range(len(x)):
            num = it[idx]
            if num not in points_by_num:
                points_by_num[num] = [[], []]
            points_by_num[num][0].append(x[idx])
            points_by_num[num][1].append(y[idx])
        for num in points_by_num:
            x_points.append(points_by_num[num][0])
            points.append(points_by_num[num][1])
    else:
        # zgoubi.plt
        kley_index = col_names.index("KLEY")
        label_index = col_names.index("LABEL1")
        ipass_index = col_names.index("IPASS")
        names = []
        current_it = None
        current_ipass = None
        for idx in range(len(x)):
            ipass = rows[idx][ipass_index]
            if current_it != it[idx] or current_ipass != ipass:
                el_type = re.sub(r"\'", "", rows[idx][kley_index])
                name = (
                    _ELEMENT_NAME_MAP.get(el_type, el_type)
                    + " "
                    + rows[idx][label_index]
                )
                if name not in names:
                    names.append(name)
                current_it = it[idx]
                current_ipass = ipass
                x_points.append([])
                points.append([])
            x_points[-1].append(x[idx])
            points[-1].append(y[idx])
        title += " " + ", ".join(names)
    return PKDict(
        title=title,
        y_label=y_info[0],
        x_label=x_info[0],
        x_range=_2d_range(x_points),
        y_range=_2d_range(points),
        x_points=x_points,
        points=points,
    )


def _extract_spin_3d(frame_args):
    col_names, all_rows = _read_data_file(
        frame_args.run_dir.join(_ZGOUBI_FAI_DATA_FILE)
    )
    x_idx = col_names.index("SX")
    y_idx = col_names.index("SY")
    z_idx = col_names.index("SZ")
    points = []
    it_idx = int(col_names.index("IT"))
    it_filter = None
    if frame_args.particleSelector != "all":
        it_filter = frame_args.particleSelector
    for row in all_rows:
        if it_filter and it_filter != row[it_idx]:
            continue
        points.append(row[x_idx])
        points.append(row[y_idx])
        points.append(row[z_idx])
    return PKDict(
        title="Particle {}".format(it_filter) if it_filter else "All Particles",
        points=points,
    )


def _format_exp(v):
    res = "{:.4e}".format(v)
    res = re.sub(r"e\+00$", "", res)
    return res


def _generate_beamline(data, beamline_map, element_map, beamline_id):
    res = ""
    for item_id in beamline_map[beamline_id]["items"]:
        if item_id in beamline_map:
            res += _generate_beamline(data, beamline_map, element_map, item_id)
            continue
        el = element_map[item_id]
        if el.type == "TOSCA":
            _prepare_tosca_element(el)
        if el.type == "SEXTUPOL":
            res += _generate_pyzgoubi_element(el, "QUADRUPO")
        elif el.type == "SCALING":
            # TODO(pjm): convert to fake element jinja template
            form = 'line.add(core.FAKE_ELEM(""" \'SCALING\'\n{} {}\n{}"""))\n'
            max_family = SCHEMA.constants.maxScalingFamily
            count = 0
            scale_values = ""
            for idx in range(1, max_family + 1):
                # NAMEF1, SCL1, LBL1
                if el.get("NAMEF{}".format(idx), "none") != "none":
                    count += 1
                    scale_values += "{} {}\n-1\n{}\n1\n".format(
                        el["NAMEF{}".format(idx)],
                        el.get("LBL{}".format(idx), ""),
                        el["SCL{}".format(idx)],
                    )
            if el.IOPT == "1" and count > 0:
                res += form.format(el.IOPT, count, scale_values)
        elif el.type in _FAKE_ELEMENT_TEMPLATES:
            res += 'line.add(core.FAKE_ELEM("""{}\n"""))\n'.format(
                jinja2.Template(_FAKE_ELEMENT_TEMPLATES[el.type]).render(el)
            )
        else:
            res += _generate_pyzgoubi_element(el)
    return res


def _generate_beamline_elements(report, data):
    res = ""
    beamline_map = PKDict()
    for bl in data.models.beamlines:
        beamline_map[bl.id] = bl
    element_map = PKDict()
    for el in copy.deepcopy(data.models.elements):
        element_map[el._id] = zgoubi_importer.MODEL_UNITS.scale_to_native(el.type, el)
        # TODO(pjm): special case for FFA dipole array
        if "dipoles" in el:
            for dipole in el.dipoles:
                zgoubi_importer.MODEL_UNITS.scale_to_native(dipole.type, dipole)
    beamline_id = lattice.LatticeUtil(data, SCHEMA).select_beamline().id
    return _generate_beamline(data, beamline_map, element_map, beamline_id)


def _generate_pyzgoubi_element(el, schema_type=None):
    res = 'line.add(core.{}("{}"'.format(el.type, el.name)
    for f in sorted(SCHEMA.model[schema_type or el.type].keys()):
        # TODO(pjm): need ignore list
        if f == "name" or f == "order" or f == "format":
            continue
        res += ", {}={}".format(_PYZGOUBI_FIELD_MAP.get(f, f), el[f])
    res += "))\n"
    return res


def _generate_parameters_file(data):
    bunch = data.models.bunch
    zgoubi_importer.MODEL_UNITS.scale_to_native("bunch", bunch)
    for f in ("FNAME", "FNAME2", "FNAME3"):
        if bunch[f]:
            bunch[f] = _SIM_DATA.lib_file_name_with_model_field("bunch", f, bunch[f])
    res, v = template_common.generate_parameters_file(data)
    report = data.report if "report" in data else ""
    if report == "tunesReport":
        return template_common.render_jinja(SIM_TYPE, v, TUNES_INPUT_FILE)
    v.zgoubiCommandFile = _ZGOUBI_COMMAND_FILE
    v.particleDef = _generate_particle(data.models.particle)
    v.beamlineElements = _generate_beamline_elements(report, data)
    v.bunchCoordinates = bunch.coordinates
    res += template_common.render_jinja(SIM_TYPE, v, "base.py")
    if (
        "twissReport" in report
        or "opticsReport" in report
        or report == "twissSummaryReport"
    ):
        v.fitYRange = [-10, 10]
        if v.bunch_method == "OBJET2.1":
            y = v.bunchCoordinates[0].Y
            if y != 0:
                # within 20% on either side of particle 0
                v.fitYRange = [
                    min(v.fitYRange[0], y * 80),
                    max(v.fitYRange[1], y * 120),
                ]
        return res + template_common.render_jinja(SIM_TYPE, v, "twiss.py")
    v.outputFile = _ZGOUBI_FAI_DATA_FILE
    res += template_common.render_jinja(SIM_TYPE, v, "bunch.py")
    if "bunchReport" in report:
        return res + template_common.render_jinja(SIM_TYPE, v, "bunch-report.py")
    return res + template_common.render_jinja(SIM_TYPE, v)


def _generate_particle(particle):
    if particle.particleType == "Other":
        return "{} {} {} {} 0".format(particle.M, particle.Q, particle.G, particle.Tau)
    return particle.particleType


def _initial_phase_field(field):
    return _INITIAL_PHASE_MAP.get(field, "{}o".format(field))


def _ipasses_for_data(col_names, rows):
    res = []
    ipass_index = col_names.index("IPASS")
    for row in rows:
        ipass = row[ipass_index]
        if ipass not in res:
            res.append(ipass)
    return res


def _parse_zgoubi_log(run_dir, log_filename="run.log"):
    if (
        res := _ZgoubiLogParser(
            run_dir,
            log_filename=_ZGOUBI_LOG_FILE,
            default_msg="",
        ).parse_for_errors()
    ) != "":
        return res
    return template_common.LogParser(
        run_dir,
        log_filename=log_filename,
        error_patterns=(r"Fortran runtime error: (.*)",),
        default_msg="",
    ).parse_for_errors()


def _particle_count(data):
    bunch = data.models.bunch
    if bunch.method == "MCOBJET3":
        return bunch.particleCount
    return bunch.particleCount2


def _peak_x(x_points, y_points):
    x = x_points[0]
    max_y = y_points[0]
    for i in range(len(x_points)):
        if y_points[i] > max_y:
            max_y = y_points[i]
            x = x_points[i]
    return "{:.6f}".format(x)


def _prepare_tosca_element(el):
    el.MOD = _MAGNET_TYPE_TO_MOD[el.meshType][el.magnetType]
    if "{{ fileCount }}" in el.MOD:
        el.MOD = el.MOD.replace("{{ fileCount }}", str(el.fileCount))
        el.hasFields = True
    file_count = zgoubi_parser.tosca_file_count(el)
    el.fileNames = el.fileNames[:file_count]

    filename = _SIM_DATA.lib_file_name_with_model_field(
        "TOSCA", "magnetFile", el.magnetFile
    )
    if file_count == 1 and not zgoubi_importer.is_zip_file(filename):
        el.fileNames[0] = _SIM_DATA.lib_file_name_with_model_field(
            "TOSCA", "magnetFile", el.fileNames[0]
        )


def _read_data_file(path, mode="title"):
    # mode: title -> header -> data
    col_names = []
    rows = []
    with pkio.open_text(str(path)) as f:
        for line in f:
            if mode == "title":
                if not re.search(r"^\@", line):
                    mode = "header"
                continue
            # work-around odd header/value "! optimp.f" int twiss output
            line = re.sub(r"\!\s", "", line)
            # remove space from quoted values
            line = re.sub(r"'(\S*)\s*'", r"'\1'", line)
            if mode == "header":
                # header row starts with '# <letter>'
                if re.search(r"^\s*#\s+[a-zA-Z]", line):
                    col_names = re.split(r"\s+", line)
                    col_names = [re.sub(r"\W|_", "", x) for x in col_names[1:]]
                    mode = "data"
            elif mode == "data":
                if re.search(r"^\s*#", line):
                    continue
                row = re.split(r"\s+", re.sub(r"^\s+", "", line))
                rows.append(row)
    return col_names, rows


def _read_twiss_header(run_dir):
    path = py.path.local(run_dir).join(_ZGOUBI_TWISS_FILE)
    res = []
    for line in pkio.read_text(path).split("\n"):
        for var in line.split("@ "):
            values = var.split()
            if values and values[0] in _TWISS_SUMMARY_LABELS:
                v = values[2]
                if re.search(r"[a-z]{2}", v, re.IGNORECASE):
                    pass
                else:
                    v = float(v)
                res.append([values[0], _TWISS_SUMMARY_LABELS[values[0]], v])
    # get FIT2 results for Y and Y' from zgoubi.FITVALS.out
    path = py.path.local(run_dir).join(_ZGOUBI_FIT_VALUES_FILE)
    col_names = None
    rows = []
    for line in pkio.read_text(path).split("\n"):
        if not col_names and re.search(r"\bLMNT\b", line):
            col_names = line.split()
        elif col_names:
            rows.append(line.split())
    idx = col_names.index("FINAL")
    res.append(["FIT2 FINAL Y", "Closed Orbit Y [m]", float(rows[0][idx]) / 1e2])
    res.append(["FIT2 FINAL Y'", "Closed Orbit Y' [rad]", float(rows[1][idx]) / 1e3])
    return res
