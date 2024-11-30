"""canvas execution template.

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from rsbeams.rsstats import kinematic
from sirepo.template import code_variable
from sirepo.template import madx_parser
from sirepo.template import sdds_util
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
from sirepo.template.madx_converter import MadxConverter
import h5py
import impactx
import math
import numpy
import pandas
import pmd_beamphysics.readers
import pykern.pkio
import pykern.pksubprocess
import re
import scipy.constants
import sirepo.sim_data
import sirepo.template.impactx
import sirepo.template.madx
import tempfile

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
INPUT_IMPACTX_BEAM_FILE = "beam.h5"
_PHASE_SPACE_LABEL = PKDict(
    x="x [m]",
    px="Px [rad]",
    y="y [m]",
    py="Py [rad]",
    t="t [m]",
    pt="Pt (%)",
)
_MADX_TRACK_OUTPUT_FILE = "madx/ptc_track.file.tfs"


class CanvasMadxConverter(MadxConverter):
    _FIELD_MAP = [
        [
            "COLLIMATOR",
            ["APERTURE", "l"],
        ],
        [
            "DRIFT",
            ["DRIFT", "l"],
        ],
        [
            "QUADRUPOLE",
            ["QUADRUPOLE", "l", "k1", "k1s"],
        ],
        ["RFCAVITY", ["RFCAVITY", "l", "volt", "freq", "phase=lag"]],
        [
            "SBEND",
            ["SBEND", "l", "angle", "fint", "fintx", "e1", "e2"],
        ],
        [
            "DIPEDGE",
            ["SBEND"],
        ],
        [
            "SEXTUPOLE",
            ["SEXTUPOLE", "l", "k2", "k2s"],
        ],
    ]

    def __init__(self, qcall=None, **kwargs):
        super().__init__(
            SIM_TYPE,
            self._FIELD_MAP,
            downcase_variables=True,
            qcall=qcall,
            **kwargs,
        )
        self.dipedges = PKDict()

    def from_madx(self, madx):
        data = self.fill_in_missing_constants(super().from_madx(madx), PKDict())
        self._remove_zero_drifts(data)
        self.__merge_dipedges(data)
        return data

    def _fixup_element(self, element_in, element_out):
        super()._fixup_element(element_in, element_out)
        if self.from_class.sim_type() == SIM_TYPE:
            pass
        else:
            if element_in.type == "COLLIMATOR":
                element_out.shape = (
                    "rectangular"
                    if element_in.apertype == "rectangle"
                    else "elliptical"
                )
                m = re.search(r"^\{?\s*(.*?),\s*(.*?)\s*\}?$", element_in.aperture)
                if m:
                    element_out.xmax = float(m.group(1))
                    element_out.ymax = float(m.group(2))
            if element_in.type == "DIPEDGE":
                self.dipedges[element_out._id] = element_in
            elif element_in.type == "SBEND":
                element_out.gap = self.__val(element_in.hgap) * 2
                if element_out.fintx == -1:
                    element_out.fintx = element_out.fint
            elif element_in.type == "RFCAVITY":
                element_out.volt = self.__val(element_out.volt) * 1e6
                element_out.phase = self.__val(element_out.phase) * -180

    def __merge_dipedges(self, data):
        # dipedge in: {'e1': 0.048345620280243, 'fint': 0.0, 'h': 0.096653578905433, 'hgap': 0.0, }
        # bend angle, gap, fint, fintx, e1, e2
        bends = PKDict()
        el = []
        for e in data.models.elements:
            if e._id in self.dipedges:
                continue
            if e.type == "SBEND":
                bends[e._id] = e
            el.append(e)
        data.models.elements = el
        for b in data.models.beamlines:
            bl = []
            dip = None
            bend = None
            for i in b["items"]:
                if i in self.dipedges:
                    if bend:
                        # trailing dipedge
                        bend.fintx = self.dipedges[i].fint
                        bend.e2 = self.dipedges[i].e1
                        bend.gap = 2 * self.__val(self.dipedges[i].hgap)
                        bend = None
                    else:
                        dip = self.dipedges[i]
                    continue
                if i in bends:
                    bend = bends[i]
                    if dip:
                        # leading dipedge
                        bend.fint = dip.fint
                        bend.e1 = dip.e1
                        bend.gap = 2 * self.__val(dip.hgap)
                        dip = None
                bl.append(i)
            b["items"] = bl

    def __val(self, var_value):
        return self.vars.eval_var_with_assert(var_value)


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=100,
        frameCount=0,
    )
    if is_running:
        return res
    # TODO(pjm): check enable code output files
    if run_dir.join(
        f"impactx/{ sirepo.template.impactx.FINAL_DISTRIBUTION_OUTPUT_FILE }"
    ).exists():
        res.frameCount = 1
        res.bunchAnimationFrameCount = len(_madx_track_info())

    return res


def code_var(variables):
    return code_variable.CodeVar(
        variables,
        code_variable.PurePythonEval(
            PKDict(
                pi=math.pi,
            )
        ),
    )


def get_data_file(run_dir, model, frame, options):
    if "bunchReport" in model:
        return sirepo.template.impactx.get_data_file(run_dir, model, frame, options)


def prepare_for_client(data, qcall, **kwargs):
    code_var(data.models.rpnVariables).compute_cache(data, SCHEMA)
    return data


def prepare_sequential_output_file(run_dir, data):
    return sirepo.template.impactx.prepare_sequential_output_file(run_dir, data)


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def save_sequential_report_data(run_dir, data):
    return sirepo.template.impactx.save_sequential_report_data(run_dir, data)


def _elegant_filename_for_frame(sim_in, frame_index):
    if frame_index == 0:
        return f"{INPUT_IMPACTX_BEAM_FILE}.sdds"
    c = 0
    names = PKDict()
    util = LatticeUtil(sim_in, SIM_TYPE)
    for bid in util.explode_beamline(util.select_beamline().id):
        e = util.get_item(bid)
        if e.type == "MONITOR":
            n = names.get(e.name, 0) + 1
            names[e.name] = n
            c += 1
            if c == frame_index:
                return f"{e.name}.filename-{n:03}.sdds"
    return "end.filename-001.sdds"


def sim_frame(frame_args):

    def _flip_sign(values):
        return (-numpy.array(values)).tolist()

    title = ""
    if frame_args.simCode == "elegant":
        _ELEGANT_FIELD_MAP = PKDict(
            px="xp",
            py="yp",
            pt="p",
        )

        def _to_elegant(field):
            fn = str(
                frame_args.run_dir.join(
                    "elegant/{}".format(
                        _elegant_filename_for_frame(
                            frame_args.sim_in, frame_args.frameIndex
                        )
                    )
                )
            )
            s = sdds_util.read_sdds_parameter(fn, "s")
            if s is None:
                s = 0
            v = sdds_util.extract_sdds_column(
                fn,
                _ELEGANT_FIELD_MAP.get(field, field),
                0,
            )["values"]
            if field == "t":
                v = -numpy.array(v) * scipy.constants.c
                if s is not None:
                    v -= v.mean()
            elif field == "pt":
                v = _elegant_p_to_pt(frame_args.run_dir, v)
            return v, s

        x, s = _to_elegant(frame_args.x)
        y, s = _to_elegant(frame_args.y)
        title = "{:.4g} m".format(s)
    elif frame_args.simCode == "madx":

        def _to_madx(particles, field):
            v = sirepo.template.madx.to_floats(particles[field])
            if field in ("t", "pt"):
                v = _flip_sign(v)
            return v

        i = _madx_track_info()[frame_args.frameIndex]
        title = "{} {:.4g} m".format(i.name, float(i.s))
        p = madx_parser.parse_tfs_file(
            _MADX_TRACK_OUTPUT_FILE,
            want_page=frame_args.frameIndex,
        )
        x = _to_madx(p, frame_args.x)
        y = _to_madx(p, frame_args.y)
    elif frame_args.simCode == "impactx":
        _IMPACTX_FIELD_MAP = PKDict(
            x="position/x",
            px="momentum/x",
            y="position/y",
            py="momentum/y",
            t="position/t",
            pt="momentum/t",
        )
        if frame_args.frameIndex == 0:
            filename = INPUT_IMPACTX_BEAM_FILE
            fi = 0
        else:
            filename = "impactx/diags/openPMD/monitor.h5"
            fi = frame_args.frameIndex - 1
        with h5py.File(filename, "r") as f:
            pp = pmd_beamphysics.readers.particle_paths(f)
            pm = PKDict()
            for p in pp:
                idx = int(re.search(r"/data/(\d+)/", p)[1])
                pm[idx] = p
            v = sorted(pm.keys())
            d = f[pm[v[fi]]]["beam"]
            x = list(d[_IMPACTX_FIELD_MAP[frame_args.x]])
            y = list(d[_IMPACTX_FIELD_MAP[frame_args.y]])
            # TODO(pjm): share title format across codes
            title = "{:.4g} m".format(d.attrs["s_ref"])
    else:
        raise AssertionError(f"Unknown simCode: {frame_args.simCode}")
    return template_common.heatmap(
        values=[x, y],
        model=frame_args,
        plot_fields=PKDict(
            x_label=_PHASE_SPACE_LABEL[frame_args.x],
            y_label=_PHASE_SPACE_LABEL[frame_args.y],
            title=f"{frame_args.simCode} {title}",
        ),
    )


def sim_frame_sigmaAnimation(frame_args):
    elegant = PKDict(
        s=sdds_util.extract_sdds_column(
            str(frame_args.run_dir.join("elegant/run_setup.sigma.sdds")),
            "s",
            0,
        )["values"],
        sx=sdds_util.extract_sdds_column(
            str(frame_args.run_dir.join("elegant/run_setup.sigma.sdds")),
            "Sx",
            0,
        )["values"],
        sy=sdds_util.extract_sdds_column(
            str(frame_args.run_dir.join("elegant/run_setup.sigma.sdds")),
            "Sy",
            0,
        )["values"],
    )
    impactx_sigma = pandas.read_csv(
        "impactx/diags/reduced_beam_characteristics.0.0", delimiter=" "
    )
    impactx = PKDict(
        s=list(impactx_sigma["s"].values),
        sx=list(impactx_sigma["sig_x"].values),
        sy=list(impactx_sigma["sig_y"].values),
    )

    # TODO(pjm): group both codes by "s" and interpolate values if necessary

    _trim_duplicate_positions(elegant, "s", "sx", "sy")
    _trim_duplicate_positions(impactx, "s", "sx", "sy")

    return template_common.parameter_plot(
        x=elegant.s,
        plots=[
            PKDict(
                label="elegant sigma x [m]",
                points=elegant.sx,
                strokeWidth=7,
                opacity=0.5,
            ),
            PKDict(
                label="elegant sigma y [m]",
                points=elegant.sy,
                strokeWidth=7,
                opacity=0.5,
            ),
            PKDict(label="impactx sigma x [m]", points=impactx.sx),
            PKDict(
                label="impactx sigma y [m]",
                points=impactx.sy,
            ),
        ],
        model=frame_args,
        plot_fields=PKDict(
            title="",
            y_label="",
            x_label="s [m]",
            dynamicYLabel=True,
        ),
    )


def stateless_compute_code_versions(data, **kwargs):
    def _run_code(name, regexp):
        t = tempfile.NamedTemporaryFile()
        pykern.pksubprocess.check_call_with_signals([name], output=t.name)
        m = re.match(regexp, pykern.pkio.read_text(t.name), re.MULTILINE | re.DOTALL)
        if not m:
            raise AssertionError(f"Unable to parse version for code: {name}")
        return m.group(1)

    return PKDict(
        elegant="elegant ("
        + _run_code("elegant", r".*?This is elegant ([\d\.]{4,}),")
        + ")",
        madx="MAD-X (" + _run_code("madx", r".*?MAD-X\s([\d\.]{4,})\s") + ")",
        impactx=f"ImpactX ({ impactx.__version__ })",
    )


def stateful_compute_import_file(data, **kwargs):
    res = CanvasMadxConverter().from_madx_text(data.args.file_as_str)
    res.models.simulation.name = data.args.purebasename
    return PKDict(imported_data=res)


def sim_frame_twissAnimation(frame_args):
    # TODO(pjm): refactor this
    elegant = PKDict(
        s=sdds_util.extract_sdds_column(
            str(frame_args.run_dir.join("elegant/run_setup.sigma.sdds")),
            "s",
            0,
        )["values"],
        bx=sdds_util.extract_sdds_column(
            str(frame_args.run_dir.join("elegant/run_setup.sigma.sdds")),
            "betaxBeam",
            0,
        )["values"],
        by=sdds_util.extract_sdds_column(
            str(frame_args.run_dir.join("elegant/run_setup.sigma.sdds")),
            "betayBeam",
            0,
        )["values"],
    )
    impactx_sigma = pandas.read_csv(
        "impactx/diags/reduced_beam_characteristics.0.0", delimiter=" "
    )
    impactx = PKDict(
        s=list(impactx_sigma["s"].values),
        bx=list(impactx_sigma["beta_x"].values),
        by=list(impactx_sigma["beta_y"].values),
    )
    madx_twiss = madx_parser.parse_tfs_file("madx/twiss.file.tfs")
    madx = PKDict(
        s=sirepo.template.madx.to_floats(madx_twiss["s"]),
        bx=sirepo.template.madx.to_floats(madx_twiss["betx"]),
        by=sirepo.template.madx.to_floats(madx_twiss["bety"]),
    )

    _trim_duplicate_positions(elegant, "s", "bx", "by")
    _trim_duplicate_positions(impactx, "s", "bx", "by")
    _trim_duplicate_positions(madx, "s", "bx", "by")

    # TODO(pjm): group/verify both codes by "s" and interpolate values if necessary

    return template_common.parameter_plot(
        x=elegant.s,
        plots=[
            PKDict(
                label="elegant beta x [m]",
                points=elegant.bx,
                strokeWidth=7,
                opacity=0.5,
            ),
            PKDict(
                label="elegant beta y [m]",
                points=elegant.by,
                strokeWidth=7,
                opacity=0.5,
            ),
            PKDict(
                label="impactx beta x [m]",
                strokeWidth=3,
                opacity=0.7,
                points=impactx.bx,
            ),
            PKDict(
                label="impactx beta y [m]",
                strokeWidth=3,
                opacity=0.7,
                points=impactx.by,
            ),
            PKDict(
                label="madx beta x [m]",
                points=madx.bx,
                dashes="5 3",
            ),
            PKDict(
                label="madx beta y [m]",
                points=madx.by,
                dashes="5 3",
            ),
        ],
        model=frame_args,
        plot_fields=PKDict(
            title="",
            y_label="",
            x_label="s [m]",
            dynamicYLabel=True,
        ),
    )


def write_parameters(data, run_dir, is_parallel):
    pykern.pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _elegant_p_to_pt(run_dir, values):
    # read species mass from impactx input file
    with h5py.File(run_dir.join(INPUT_IMPACTX_BEAM_FILE), "r") as f:
        pp = pmd_beamphysics.readers.particle_paths(f)
        d = f[pp[-1]]
        if "beam" in d:
            d = d["beam"]
        mass = d.attrs["mass_ref"]
    ref = kinematic.Converter(
        mass=mass,
        mass_unit="SI",
        betagamma=sdds_util.read_sdds_parameter(
            "elegant/run_setup.output.sdds", "pCentral"
        ),
    )()
    return (
        kinematic.Converter(
            mass=mass,
            mass_unit="SI",
            betagamma=numpy.array(values),
        )(
            silent=True
        )["gamma"]
        - ref["gamma"]
    ) / ref["betagamma"]


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    if (
        "bunchReport" in data.get("report", "")
        or data.models.distribution.distributionType != "File"
        or (
            data.models.distribution.distributionType == "File"
            and sdds_util.is_sdds_file(data.models.distribution.distributionFile)
        )
    ):
        return sirepo.template.impactx.generate_distribution(data, res, v)
    return ""


def _madx_track_info():
    return madx_parser.parse_tfs_page_info(_MADX_TRACK_OUTPUT_FILE)


def _trim_duplicate_positions(v, s, k1, k2):
    s2 = []
    last_pos = None
    for idx in reversed(range(len(v[s]))):
        pos = v[s][idx]
        if last_pos is not None and last_pos == pos:
            del v[k1][idx]
            del v[k2][idx]
        else:
            s2.insert(0, pos)
        last_pos = pos
    v[s] = s2
