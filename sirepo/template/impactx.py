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
import numpy
import pandas
import sirepo.sim_data
import sirepo.template.lattice


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_BUNCH_REPORT_OUTPUT_FILE = "diags/openPMD/monitor.h5"
_STAT_REPORT_OUTPUT_FILE = "diags/reduced_beam_characteristics.0.0"


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
        x=["position/x", "m"],
        px=["momentum/x", ""],
        y=["position/y", "m"],
        py=["momentum/y", ""],
        t=["position/t", "m"],
        pt=["momentum/t", ""],
        qm=["qm", ""],
    )

    def _points(file, frame_index, name):
        return numpy.array(file[f"data/2/particles/beam/{_M[name][0]}"])

    def _format_plot(h5file, field):
        u = _M[field.label][1]
        if u:
            field.label = f"{field.label} [{u}]"

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


def _generate_elements(util):
    return """m1=elements.BeamMonitor("monitor", backend="h5"),
dr1=elements.Drift(ds=5.0058489435, nslice=25),
dr2=elements.Drift(ds=0.5, nslice=25),
sbend1=elements.Sbend(ds=0.500194828041958, rc=-10.3462283686195526, nslice=25),
sbend2=elements.Sbend(ds=0.500194828041958, rc=10.3462283686195526, nslice=25),
dipedge1=elements.DipEdge(psi=-0.048345620280243, rc=-10.3462283686195526, g=0.0, K2=0.0),
dipedge2=elements.DipEdge(psi=0.048345620280243, rc=10.3462283686195526, g=0.0, K2=0.0),"""


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
    v.kineticEnergyMeV = round(
        template_common.ParticleEnergy.compute_energy(
            SIM_TYPE,
            d.species,
            PKDict(
                energy=d.energy,
            ),
        )["kinetic_energy"]
        * 1e3,
        9,
    )
    mc = SCHEMA.constants.particleMassAndCharge[d.species]
    v.speciesMassMeV = round(mc[0] * 1e3, 9)
    v.speciesCharge = mc[1]
    v.createParticles = template_common.render_jinja(SIM_TYPE, v, "particles.py")
