"""canvas execution template.

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import hdf5_util
from sirepo.template import madx_parser
from sirepo.template import sdds_util
from sirepo.template import template_common
import math
import numpy
import pandas
import sirepo.sim_data
import sirepo.template.madx

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_BUNCH_REPORT_OUTPUT_FILE = "diags/openPMD/monitor.h5"


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=100,
        frameCount=0,
    )
    if is_running:
        return res
    # TODO(pjm): check enable code output files
    if run_dir.join("impactx/final_distribution.h5").exists():
        res.frameCount = 1
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


def sim_frame(frame_args):
    # TODO(pjm): implement selecting columns from frame_args
    if frame_args.simCode == "elegant":
        x = sdds_util.extract_sdds_column(
            str(frame_args.run_dir.join("elegant/run_setup.output.sdds")),
            "x",
            0,
        )["values"]
        y = sdds_util.extract_sdds_column(
            str(frame_args.run_dir.join("elegant/run_setup.output.sdds")),
            "xp",
            0,
        )["values"]
    elif frame_args.simCode == "madx":
        madx_particles = madx_parser.parse_tfs_file(
            "madx/ptc_track.file.tfs", want_page=1
        )
        x = sirepo.template.madx.to_floats(madx_particles["x"])
        y = sirepo.template.madx.to_floats(madx_particles["px"])
    elif frame_args.simCode == "impactx":
        impactx_particles = pandas.read_hdf("impactx/final_distribution.h5")
        x = list(impactx_particles["position_x"])
        y = list(impactx_particles["momentum_x"])
    else:
        raise AssertionError(f"Unknown simCode: {frame_args.simCode}")
    return template_common.heatmap(
        values=[x, y],
        model=frame_args,
        plot_fields=PKDict(
            x_label="x [m]",
            y_label="xp [rad]",
            title=frame_args.simCode,
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
                strokeWidth=10,
                opacity=0.5,
            ),
            PKDict(
                label="elegant sigma y [m]",
                points=elegant.sy,
                strokeWidth=10,
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
        bx=list(
            impactx_sigma["sig_x"].values ** 2 / impactx_sigma["emittance_x"].values
        ),
        by=list(
            impactx_sigma["sig_y"].values ** 2 / impactx_sigma["emittance_y"].values
        ),
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
                points=impactx.bx,
            ),
            PKDict(
                label="impactx beta y [m]",
                points=impactx.by,
            ),
            PKDict(
                label="madx beta x [m]",
                points=madx.bx,
                strokeWidth=15,
                opacity=0.3,
            ),
            PKDict(
                label="madx beta y [m]",
                points=madx.by,
                strokeWidth=15,
                opacity=0.3,
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
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


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


def _generate_distribution(data, res, v):
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
    return res + template_common.render_jinja(SIM_TYPE, v, "distribution.py")


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    if (
        "bunchReport" in data.get("report", "")
        or data.models.distribution.distributionType != "File"
    ):
        return _generate_distribution(data, res, v)
    return ""
