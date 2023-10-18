# -*- coding: utf-8 -*-
"""omega execution template.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import h5py
import pmd_beamphysics
import re
import sirepo.sim_data


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_PHASE_PLOT_COUNT = 4
_PHASE_PLOTS = PKDict(
    genesis=[
        ["x", "pxmc"],
        ["y", "pymc"],
        ["x", "y"],
        ["psi", "gamma"],
    ],
    opal=[
        ["x", "px"],
        ["y", "py"],
        ["x", "y"],
        ["z", "pz"],
    ],
    elegant=[
        ["x", "xp"],
        ["y", "yp"],
        ["x", "y"],
        ["t", "p"],
    ],
)
_PLOT_TITLE = PKDict(
    opal=PKDict(
        {
            "x-px": "Horizontal",
            "y-py": "Vertical",
            "x-y": "Cross-section",
            "z-pz": "Longitudinal",
        },
    ),
    genesis=PKDict(
        {
            "x-pxmc": "Horizontal",
            "y-pymc": "Vertical",
            "x-y": "Cross-section",
            "psi-gamma": "PSI/Gamma",
        },
    ),
)
_PLOT_Y_LABEL = PKDict(
    opal=PKDict(
        {
            # TODO(pjm): should format px and βx with subscripts
            "x-px": "px (βx γ)",
            "y-py": "py (βy γ)",
            "z-pz": "pz (β γ)",
        }
    )
)
_BEAM_PARAMETERS = PKDict(
    genesis=PKDict(
        rmsx="xrms",
        rmsy="yrms",
        rmss="none",
        rmspx="none",
        rmspy="none",
        meanx="none",
        meany="none",
        none="none",
    ),
    opal=PKDict(
        rmsx="rms x",
        rmsy="rms y",
        rmss="rms s",
        rmspx="rms px",
        rmspy="rms py",
        meanx="mean x",
        meany="mean y",
        none="none",
    ),
    elegant=PKDict(
        rmsx="Sx",
        rmsy="Sy",
        rmss="Ss",
        rmspx="Sxp",
        rmspy="Syp",
        meanx="Cx",
        meany="Cy",
        none="none",
    ),
)
_ELEGANT_BEAM_PARAMETER_FILE_DEFAULT = "run_setup.sigma.sdds"
_ELEGANT_BEAM_PARAMETER_FILE = PKDict(
    Cx="run_setup.centroid.sdds",
    Cy="run_setup.centroid.sdds",
)
_SUCCESS_OUTPUT_FILE = PKDict(
    elegant="run_setup.output.sdds",
    opal="opal.h5",
    genesis="genesis.out.par",
)


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            frameCount=0,
            percentComplete=0,
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
        outputInfo=_output_info(run_dir),
    )


def get_data_file(run_dir, model, frame, options):
    i = int(re.search(r"Animation(\d+)\-", model).groups(1)[0])
    sim_type, sim_id = _sim_info(
        simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME)).models,
        i - 1,
    )
    particle_file = pkio.py_path(f"run{i}").join(_SUCCESS_OUTPUT_FILE[sim_type])
    if options.suffix is None:
        return particle_file
    assert options.suffix == "openpmd", f"unknown data type={options.suffix} requested"
    n = f"{sim_type}_openpmd.h5"
    d = None
    if sim_type == "elegant":
        from pmd_beamphysics import ParticleGroup
        import pmd_beamphysics.interfaces.elegant

        p = ParticleGroup(
            data=pmd_beamphysics.interfaces.elegant.elegant_to_data(particle_file),
        ).write(n)
    elif sim_type == "opal":
        from pmd_beamphysics import ParticleGroup
        import pmd_beamphysics.interfaces.opal
        import sirepo.template.opal
        import pykern.pkio

        step = sirepo.template.opal.read_frame_count(pykern.pkio.py_path("."))
        #        assert step > 0
        #        step -= 1

        with h5py.File(particle_file, "r") as f:
            p = ParticleGroup(
                data=pmd_beamphysics.interfaces.opal.opal_to_data(f[f"/Step#{step}"]),
            )
            p.write(n)
    elif sim_type == "genesis":
        from pmd_beamphysics import ParticleGroup
        import pmd_beamphysics.interfaces.genesis
        import numpy
        import sirepo.simulation_db
        import sirepo.template.template_common

        dm = sirepo.simulation_db.read_json(
            sirepo.template.template_common.INPUT_BASE_NAME
        ).models
        v = numpy.fromfile(
            particle_file.dirpath().join(particle_file.purebasename + ".dpa"),
            dtype=numpy.float64,
        )
        v = v.reshape(
            int(len(v) / 6 / dm.electronBeam.npart),
            6,
            dm.electronBeam.npart,
        )

        p = ParticleGroup(
            data=pmd_beamphysics.interfaces.genesis.genesis2_dpa_to_data(
                v,
                xlamds=dm.radiation.xlamds,
                current=numpy.array([dm.electronBeam.curpeak]),
            )
        )
        p.write(n)
    else:
        raise AssertionError(f"unsupported sim_type={sim_type}")

    # with h5py.File(n, "w") as h:
    #     pmd_beamphysics.writers.write_pmd_bunch(
    #         h,
    #         d,
    #     )
    return n


def post_execution_processing(success_exit, run_dir, **kwargs):
    if not success_exit:
        # first check for assertion errors in main log file
        # AssertionError: The referenced ELEGANT simulation no longer exists
        with pkio.open_text(run_dir.join(template_common.RUN_LOG)) as f:
            for line in f:
                m = re.search(r"^AssertionError: (.*)", line)
                if m:
                    return m.group(1)
    dm = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME)).models
    for idx in reversed(range(len(dm.simWorkflow.coupledSims))):
        sim_type, sim_id = _sim_info(dm, idx)
        if not sim_type or not sim_id:
            continue
        sim_dir = _sim_dir(run_dir, idx + 1)
        sim_template = sirepo.template.import_module(sim_type)
        res = f"{sim_type.upper()} failed\n"
        if success_exit:
            # no error
            return
        if sim_type and sim_id:
            if sim_dir.exists():
                if sim_type == "opal":
                    return res + sim_template.parse_opal_log(sim_dir)
                if sim_type == "elegant":
                    return res + sim_template.parse_elegant_log(sim_dir)
                if sim_type == "genesis":
                    # genesis gets error from main run.log
                    return res + sim_template.parse_genesis_error(run_dir)
                return res

    return "An unknown error occurred"


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def sim_frame(frame_args):
    sim_type = frame_args.sim_in.models.simWorkflow.coupledSims[
        int(frame_args.simCount) - 1
    ].simulationType
    frame_args.run_dir = _sim_dir(frame_args.run_dir, frame_args.simCount)
    frame_args.sim_in = simulation_db.read_json(
        frame_args.run_dir.join(template_common.INPUT_BASE_NAME)
    )
    if "Phase" in frame_args.frameReport:
        return _plot_phase(sim_type, frame_args)
    if "Beam" in frame_args.frameReport:
        return _plot_beam(sim_type, frame_args)
    if "Field" in frame_args.frameReport:
        return _plot_field_dist(sim_type, frame_args)
    raise AssertionError(
        "unhandled sim frame report: {}".format(frame_args.frameReport)
    )


def stateful_compute_get_elegant_sim_list(**kwargs):
    return _sim_list("elegant")


def stateful_compute_get_genesis_sim_list(**kwargs):
    return _sim_list("genesis")


def stateful_compute_get_opal_sim_list(**kwargs):
    return _sim_list("opal")


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _extract_elegant_beam_plot(frame_args):
    # this is tricky because the data could come from 2 different elegant output files
    import sirepo.template.elegant

    files = PKDict()
    frame_args.x = "s"
    for f in ("y1", "y2", "y3"):
        if frame_args[f] == "none":
            continue
        fn = _ELEGANT_BEAM_PARAMETER_FILE.get(
            frame_args[f], _ELEGANT_BEAM_PARAMETER_FILE_DEFAULT
        )
        if fn in files:
            files[fn].append(frame_args[f])
        else:
            files[fn] = [frame_args[f]]

    res = None
    for fn in files:
        for i in (1, 2, 3):
            if i <= len(files[fn]):
                frame_args[f"y{i}"] = files[fn][i - 1]
            else:
                frame_args[f"y{i}"] = "none"
        r = sirepo.template.elegant.extract_report_data(
            str(frame_args.run_dir.join(fn)),
            frame_args,
        )
        if res:
            for p in r.plots:
                # TODO(pjm): reaches inside template_common to get colors
                p.color = template_common._PLOT_LINE_COLOR[len(res.plots)]
                res.plots.append(p)
        else:
            res = r
    return res


def _generate_parameters_file(data):
    dm = data.models
    res, v = template_common.generate_parameters_file(data)
    sim_list = []
    for idx in range(len(dm.simWorkflow.coupledSims)):
        sim_type, sim_id = _sim_info(dm, idx)
        if sim_type and sim_id:
            sim_list.append(
                PKDict(
                    sim_type=sim_type,
                    sim_id=sim_id,
                )
            )
        else:
            break
    if not sim_list:
        raise AssertionError("No simulations selected")
    v.simList = sim_list
    return res + template_common.render_jinja(SIM_TYPE, v)


def _output_info(run_dir):
    def _has_file(sim_dir):
        for f in _SUCCESS_OUTPUT_FILE:
            s = sim_dir.join(_SUCCESS_OUTPUT_FILE[f])
            if s.exists() and s.size() > 0:
                return True
        return False

    def _report_info(sim_count, model_name, report_count):
        return PKDict(
            simCount=sim_count,
            modelName=model_name,
            reportCount=report_count,
            modelKey=f"{model_name}{sim_count}-{report_count}",
        )

    res = []
    idx = 0
    sim_dir = _sim_dir(run_dir, idx + 1)
    while sim_dir.exists() and _has_file(sim_dir):
        r = []
        res.append(r)
        r.append(
            [
                _report_info(idx + 1, "simBeamAnimation", 1),
            ]
        )
        r.append(
            [
                _report_info(idx + 1, "simPhaseSpaceAnimation", phase + 1)
                for phase in range(_PHASE_PLOT_COUNT)
            ]
        )
        if _is_genesis(run_dir, idx):
            r.append(
                [
                    _report_info(idx + 1, "simFieldDistributionAnimation", 1),
                ]
            )
        idx += 1
        sim_dir = _sim_dir(run_dir, idx + 1)

    return res


def _is_genesis(run_dir, index):
    t, i = _sim_info(
        simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME)).models,
        index,
    )
    return t == "genesis"


def _phase_plot_args(sim_type, frame_args):
    xy = _PHASE_PLOTS[sim_type][int(frame_args.reportCount) - 1]
    del frame_args["y1"]
    frame_args.x = xy[0]
    frame_args.y = xy[1]


def _plot_beam(sim_type, frame_args):
    for f in ("y1", "y2", "y3"):
        frame_args[f] = _BEAM_PARAMETERS[sim_type][frame_args[f]]
    if sim_type == "opal":
        import sirepo.template.opal

        frame_args.x = "s"
        return sirepo.template.opal.sim_frame_plot2Animation(frame_args)
    if sim_type == "elegant":
        return _extract_elegant_beam_plot(frame_args)
    if sim_type == "genesis":
        import sirepo.template.genesis

        frame_args.sim_in = simulation_db.read_json(
            frame_args.run_dir.join(template_common.INPUT_BASE_NAME)
        )
        return sirepo.template.genesis.sim_frame_parameterAnimation(frame_args)

    raise AssertionError("unhandled sim_type for sim_frame(): {}".format(sim_type))


def _plot_field_dist(sim_type, frame_args):
    import sirepo.template.genesis

    frame_args.frameIndex = 1
    return sirepo.template.genesis.sim_frame_fieldDistributionAnimation(frame_args)


def _plot_phase(sim_type, frame_args):
    _phase_plot_args(sim_type, frame_args)

    if sim_type == "opal":
        import sirepo.template.opal

        r = sirepo.template.opal.bunch_plot(
            frame_args,
            frame_args.run_dir,
            frame_args.frameIndex,
        )
        return r.pkupdate(
            title=_PLOT_TITLE[sim_type][frame_args.x + "-" + frame_args.y],
            y_label=_PLOT_Y_LABEL[sim_type].get(
                frame_args.x + "-" + frame_args.y, r.y_label
            ),
        )
    if sim_type == "elegant":
        import sirepo.template.elegant

        return sirepo.template.elegant.extract_report_data(
            str(frame_args.run_dir.join(_SUCCESS_OUTPUT_FILE[sim_type])),
            frame_args,
        )
    if sim_type == "genesis":
        import sirepo.template.genesis

        frame_args.frameIndex = 1
        return sirepo.template.genesis.sim_frame_particleAnimation(frame_args).pkupdate(
            title=_PLOT_TITLE[sim_type][frame_args.x + "-" + frame_args.y],
        )
    raise AssertionError("unhandled sim_type for sim_frame(): {}".format(sim_type))


def _sim_dir(run_dir, sim_count):
    return run_dir.join(f"run{sim_count}")


def _sim_info(dm, idx):
    s = dm.simWorkflow.coupledSims
    if len(s) > idx:
        return s[idx].simulationType, s[idx].simulationId
    return None, None


def _sim_list(sim_type):
    return PKDict(
        simList=sorted(
            simulation_db.iterate_simulation_datafiles(
                sim_type,
                simulation_db.process_simulation_list,
            ),
            key=lambda row: row["name"],
        )
    )
