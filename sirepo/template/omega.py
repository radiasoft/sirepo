# -*- coding: utf-8 -*-
"""omega execution template.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import re
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_MAX_SIMS = 4
_MAX_PHASE_PLOTS = 4
_PHASE_PLOTS = PKDict(
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
        }
    )
)
_PLOT_Y_LABEL = PKDict(
    opal=PKDict(
        {
            "x-px": "px [β_x γ]",
            "y-py": "py [β_y γ]",
            "z-pz": "pz [β γ]",
        }
    )
)
_BEAM_PARAMETERS = PKDict(
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
    meanx="run_setup.centroid.sdds",
    meany="run_setup.centroid.sdds",
)


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            frameCount=0,
            percentComplete=0,
        )
    return PKDict(
        percentComplete=100,
        reports=_completed_reports(run_dir),
    )


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data, None)


def _phase_plot_args(sim_type, frame_args):
    m = re.search(r"Phase(\d+)", frame_args.frameReport)
    if not m:
        raise AssertionError(f"unparse-able model name: {frame_args.frameReport}")
    xy = _PHASE_PLOTS[sim_type][int(m.group(1)) - 1]
    frame_args.x = xy[0]
    frame_args.y = xy[1]


def sim_frame(frame_args):
    sim_type, run_dir = _sim_type_and_run_dir_from_report_name(
        frame_args.sim_in.models,
        frame_args.frameReport,
    )
    if "Phase" in frame_args.frameReport:
        return _plot_phase(sim_type, run_dir, frame_args)
    if "Beam" in frame_args.frameReport:
        return _plot_beam(sim_type, run_dir, frame_args)
    raise AssertionError(
        "unhandled sim frame report: {}".format(frame_args.frameReport)
    )


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data, run_dir),
    )


def _completed_reports(run_dir):
    res = []
    for idx in range(_MAX_SIMS):
        if run_dir.join(f"run{idx + 1}").exists():
            res.append(
                PKDict(
                    modelName=f"sim{idx + 1}BeamAnimation",
                    frameCount=1,
                )
            )
            res += [
                PKDict(
                    modelName=f"sim{idx + 1}Phase{phase + 1}Animation",
                    frameCount=1,
                )
                for phase in range(_MAX_PHASE_PLOTS)
            ]

    return res


def _extract_elegant_beam_plot(run_dir, frame_args):
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
        frame_args[f] = _BEAM_PARAMETERS.elegant[frame_args[f]]
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
            str(frame_args.run_dir.join(f"{run_dir}/{fn}")),
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


def _generate_parameters_file(data, run_dir=None):
    dm = data.models
    res, v = template_common.generate_parameters_file(data)
    sim_list = []
    for idx in range(_MAX_SIMS):
        f = f"simType_{idx + 1}"
        f2 = f"simId_{idx + 1}"
        if dm.simWorkflow.get(f) and dm.simWorkflow.get(f2):
            sim_list.append(
                PKDict(
                    sim_type=dm.simWorkflow[f],
                    sim_id=dm.simWorkflow[f2],
                )
            )
        else:
            break
    if not sim_list:
        raise AssertionError("No simulations selected")
    v.simList = sim_list
    return res + template_common.render_jinja(SIM_TYPE, v)


def _plot_phase(sim_type, run_dir, frame_args):
    _phase_plot_args(sim_type, frame_args)

    if sim_type == "opal":
        import sirepo.template.opal

        r = sirepo.template.opal.bunch_plot(
            frame_args,
            frame_args.run_dir.join(run_dir),
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
            str(frame_args.run_dir.join(f"{run_dir}/run_setup.output.sdds")),
            frame_args,
        )
    raise AssertionError("unhandled sim_type for sim_frame(): {}".format(sim_type))


def _plot_beam(sim_type, run_dir, frame_args):
    if sim_type == "opal":
        import sirepo.template.opal

        frame_args.x = "s"
        frame_args.y1 = "rms x"
        frame_args.y2 = "rms y"
        frame_args.y3 = "rms s"
        frame_args.run_dir = frame_args.run_dir.join(run_dir)
        return sirepo.template.opal.sim_frame_plot2Animation(frame_args)
    if sim_type == "elegant":
        return _extract_elegant_beam_plot(run_dir, frame_args)
    raise AssertionError("unhandled sim_type for sim_frame(): {}".format(sim_type))


def _sim_type_and_run_dir_from_report_name(models, report):
    m = re.match(r"sim(\d+).*?Animation", report)
    assert m
    idx = int(m.group(1))
    return (
        models.simWorkflow[f"simType_{idx}"],
        f"run{idx}",
    )
