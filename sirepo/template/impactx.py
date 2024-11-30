# -*- coding: utf-8 -*-
"""ImpactX execution template.
:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import hdf5_util
from sirepo.template import template_common
from sirepo.template.madx_converter import MadxConverter
import numpy
import pandas
import re
import sirepo.lib
import sirepo.sim_data
import sirepo.template.lattice
import sirepo.template.sdds_util

FINAL_DISTRIBUTION_OUTPUT_FILE = "diags/final_distribution.h5"
# _DEFAULT_NSLICE = 12
_DEFAULT_NSLICE = 1
_MONITOR_NAME = "monitor"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_BUNCH_REPORT_OUTPUT_FILE = f"diags/openPMD/{_MONITOR_NAME}.h5"
_STAT_REPORT_OUTPUT_FILE = "diags/reduced_beam_characteristics.0.0"
_FIELD_MAPPING = PKDict(
    l="ds",
)
_TYPE_TO_CLASS = PKDict(
    APERTURE="Aperture",
    BEAMMONITOR="BeamMonitor",
    DIPEDGE="DipEdge",
    DRIFT="Drift",
    KICKER="Kicker",
    QUAD="Quad",
    SBEND="Sbend",
    SHORTRF="ShortRF",
    SOL="Sol",
)


class LibAdapter(sirepo.lib.LibAdapterBase):
    def parse_file(self, path):
        return self._convert(
            ImpactxMadxConverter(nslice=_DEFAULT_NSLICE).from_madx_text(
                pkio.read_text(path)
            )
        )

    def write_files(self, data, source_path, dest_dir):
        pkio.write_text(
            dest_dir.join(source_path.basename),
            _generate_parameters_file(data),
        )
        if data.models.distribution.distributionType == "File":
            f = _SIM_DATA.lib_file_name_with_model_field(
                "distribution",
                "distributionFile",
                data.models.distribution.distributionFile,
            )
            # f = data.models.distribution.distributionFile
            d = dest_dir.join(f)
            pkio.mkdir_parent_only(d)
            d.mksymlinkto(source_path.dirpath().join(f), absolute=False)
        return PKDict()


class ImpactxMadxConverter(MadxConverter):
    _FIELD_MAP = [
        [
            "COLLIMATOR",
            ["APERTURE"],
        ],
        [
            "DRIFT",
            ["DRIFT", "l"],
        ],
        [
            "DIPEDGE",
            ["DIPEDGE", "tilt", "K2=fint"],
        ],
        [
            "SBEND",
            ["SBEND", "l"],
        ],
        [
            "QUADRUPOLE",
            ["QUAD", "l", "k=k1"],
        ],
        [
            "SOLENOID",
            ["SOL", "l", "ks"],
        ],
        [
            "KICKER",
            ["KICKER", "xkick=hkick", "ykick=vkick"],
        ],
        [
            "MONITOR",
            ["BEAMMONITOR"],
        ],
        [
            "RFCAVITY",
            ["SHORTRF", "V=volt", "freq", "phase=lag"],
        ],
    ]

    def __init__(self, qcall=None, nslice=1, **kwargs):
        super().__init__(
            SIM_TYPE,
            self._FIELD_MAP,
            downcase_variables=True,
            qcall=qcall,
            **kwargs,
        )
        self.nslice = nslice

    def from_madx(self, madx):
        data = self.fill_in_missing_constants(super().from_madx(madx), PKDict())
        self._remove_zero_drifts(data)
        return data

    def _fixup_element(self, element_in, element_out):
        super()._fixup_element(element_in, element_out)
        if self.from_class.sim_type() == SIM_TYPE:
            pass
        else:
            if "nslice" in SCHEMA.model[element_out.type]:
                element_out.nslice = self.nslice
            if element_in.type == "SBEND":
                if self.__val(element_in.angle) != 0:
                    element_out.rc = self.__val(element_out.l) / self.__val(
                        element_in.angle
                    )
                else:
                    element_out.rc = 0
                if element_out.rc == 0:
                    element_out.type = "DRIFT"
            elif element_in.type == "COLLIMATOR":
                m = re.search(r"^\{?\s*(.*?),\s*(.*?)\s*\}?$", element_in.aperture)
                if m:
                    element_out.xmax = self.__val(m.group(1))
                    element_out.ymax = self.__val(m.group(2))
                element_out.shape = (
                    "rectangular"
                    if element_in.apertype == "rectangle"
                    else "elliptical"
                )
            elif element_in.type == "DIPEDGE":
                if self.__val(element_in.h) != 0:
                    element_out.rc = 1.0 / self.__val(element_in.h)
                else:
                    element_out.rc = 0
                element_out.g = 2 * self.__val(element_in.hgap)
                element_out.psi = element_in.e1
                if element_out.rc == 0:
                    element_out.type = "DRIFT"
            elif element_out.type == "QUAD" and self.__val(element_out.k) == 0:
                element_out.type = "DRIFT"
            elif element_out.type == "SOL" and self.__val(element_out.ks) == 0:
                element_out.type = "DRIFT"
            elif "KICKER" in element_in.type and self.__val(element_in.l) > 0:
                # TODO(pjm): add l/2 drift around kicker in beamline
                pass
            elif element_in.type == "MONITOR" and self.__val(element_in.l) > 0:
                # TODO(pjm) add drift
                pass
            elif element_in.type == "RFCAVITY" and self.__val(element_in.freq) == 0:
                if self.__val(element_in.l) > 0:
                    element_out.l = element_in.l
                    element_out.type = "DRIFT"
            elif element_in.type == "RFCAVITY":
                element_out.phase = -(self.__val(element_out.phase) * 360 + 90)
                element_out.freq = self.__val(element_out.freq) * 1e6
                p = "electron"
                if (
                    self.beam
                    and self.beam.particle in SCHEMA.constants.particleMassAndCharge
                ):
                    p = self.beam.particle
                mc = SCHEMA.constants.particleMassAndCharge.get(p)
                element_out.V = self.__val(element_out.V) / (mc[0] * 1e3)

    def __val(self, var_value):
        return self.vars.eval_var_with_assert(var_value)


def background_percent_complete(report, run_dir, is_running):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    if not is_running:
        if run_dir.join(_STAT_REPORT_OUTPUT_FILE).exists():
            return PKDict(
                frameCount=10,
                percentComplete=100,
            )
    return PKDict(
        frameCount=0,
        percentComplete=0,
    )


def code_var(variables):
    return code_variable.CodeVar(variables, code_variable.PurePythonEval())


def generate_distribution(data, res, v):
    _generate_particles(data, res, v)
    return res + template_common.render_jinja(SIM_TYPE, v, "distribution.py")


def get_data_file(run_dir, model, frame, options):
    if "bunchReport" in model:
        return run_dir.join(_BUNCH_REPORT_OUTPUT_FILE)


def prepare_for_client(data, qcall, **kwargs):
    code_var(data.models.rpnVariables).compute_cache(data, SCHEMA)
    return data


def prepare_sequential_output_file(run_dir, data):
    report = data["report"]
    if "bunchReport" in report:
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            try:
                save_sequential_report_data(run_dir, data)
            except IOError:
                # the output file isn't readable
                pass


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def save_sequential_report_data(run_dir, data):
    report = data.models[data.report]
    res = None
    if "bunchReport" in data.report:
        res = _bunch_plot(run_dir, report)
        res.title = ""
    else:
        raise AssertionError("unknown report: {}".format(report))
    template_common.write_sequential_result(
        res,
        run_dir=run_dir,
    )


def sim_frame_statAnimation(frame_args):
    d = pandas.read_csv(
        str(frame_args.run_dir.join(_STAT_REPORT_OUTPUT_FILE)), delimiter=" "
    )
    if frame_args.x == "none":
        frame_args.x = "s"
    plots = PKDict()
    for f in ("x", "y1", "y2", "y3", "y4", "y5"):
        if frame_args[f] == "none":
            continue
        plots[f] = PKDict(
            label=frame_args[f],
            dim=f,
            points=d[frame_args[f]].tolist(),
        )
    return template_common.parameter_plot(
        x=plots.x.points,
        plots=[p for p in plots.values() if p.dim != "x"],
        model=frame_args,
        plot_fields=PKDict(
            dynamicYLabel=True,
            title="",
            y_label="",
            x_label=plots.x.label,
        ),
    )


def stateful_compute_import_file(data, **kwargs):
    res = ImpactxMadxConverter(nslice=_DEFAULT_NSLICE).from_madx_text(
        data.args.file_as_str
    )
    res.models.simulation.name = data.args.purebasename
    return PKDict(imported_data=res)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )
    if is_parallel:
        return template_common.get_exec_parameters_cmd(False)
    return None


def _bunch_plot(run_dir, model):
    _M = PKDict(
        x=["position/x", "x [m]"],
        px=["momentum/x", "Px [rad]"],
        y=["position/y", "y [m]"],
        py=["momentum/y", "Py [rad]"],
        t=["position/t", "t [m]"],
        pt=["momentum/t", "Pt (%)"],
        qm=["qm", "qm"],
    )

    def _points(file, frame_index, name):
        return numpy.array(file[f"data/2/particles/beam/{_M[name][0]}"])

    def _format_plot(h5file, field):
        field.label = _M[field.label][1]

    def _title(file, frame_index):
        return ""

    return hdf5_util.HDF5Util(str(run_dir.join(_BUNCH_REPORT_OUTPUT_FILE))).heatmap(
        PKDict(
            format_plot=_format_plot,
            frame_index=0,
            model=model,
            points=_points,
            title=_title,
        )
    )


def _element_name(el):
    return el.name.lower()


def _generate_beamlines(util):
    res = []
    for bl in util.data.models.beamlines:
        a = []
        for i in bl["items"]:
            prefix = "-" if i < 0 else ""
            e = util.id_map[abs(i)]
            if util.is_beamline(e):
                a.append(f'"{prefix}{_element_name(e)}"')
            else:
                a.append(f"el.{_element_name(e)}")
        res.append(f"{_element_name(bl)}=[{', '.join(a)}],")
    return "\n".join(res)


def _format_field_value(state, model, field, field_type):
    v = model[field]
    return [_FIELD_MAPPING.get(field, field), v, field_type]


def _generate_elements(util):
    v = util.iterate_models(
        sirepo.template.lattice.LatticeIterator(PKDict(), _format_field_value),
        "elements",
    ).result
    cv = code_var(util.data.models.rpnVariables)
    res = ""
    for mf in v:
        m, fields = mf
        if m.type == "BEAMMONITOR":
            fields.append(["name", f'"{_MONITOR_NAME}"', "String"])
            fields.append(["backend", '"h5"', "String"])
        res += f"{_element_name(m)}=elements.{_TYPE_TO_CLASS[m.type]}("
        fres = []
        for f in fields:
            if f[2] == "RPNValue":
                f[1] = cv.eval_var_with_assert(f[1])
                if f[0] == "nslice":
                    f[1] = int(f[1])
            elif f[2] in util.schema.enum:
                f[1] = f'"{f[1]}"'
            fres.append(f"{f[0]}={f[1]}")
        res += ", ".join(fres) + "),\n"
    return res


def _generate_lattice(data, res, v):
    util = sirepo.template.lattice.LatticeUtil(data, SCHEMA)
    v.latticeElements = _generate_elements(util)
    v.latticeBeamlines = _generate_beamlines(util)
    v.selectedBeamline = _element_name(util.select_beamline())


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    if "bunchReport" in data.get("report", ""):
        return generate_distribution(data, res, v)
    _generate_particles(data, res, v)
    _generate_lattice(data, res, v)
    return res + template_common.render_jinja(SIM_TYPE, v, "parameters.py")


def _generate_particles(data, res, v):
    d = data.models.distribution
    if d.distributionType == "File":
        if not d.distributionFile:
            raise AssertionError("Missing Distribution File")
        v.distributionFile = _SIM_DATA.lib_file_name_with_model_field(
            "distribution",
            "distributionFile",
            d.distributionFile,
        )
        v.isSDDS = sirepo.template.sdds_util.is_sdds_file(d.distributionFile)
    mc = SCHEMA.constants.particleMassAndCharge[d.species]
    v.speciesMassMeV = round(mc[0] * 1e3, 9)
    v.speciesCharge = mc[1]
    v.createParticles = template_common.render_jinja(SIM_TYPE, v, "particles.py")
    v.finalDistributionOutputFile = FINAL_DISTRIBUTION_OUTPUT_FILE
