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


def sim_frame(frame_args):
    sim_type, run_dir = _sim_type_and_run_dir_from_report_name(
        frame_args.sim_in.models,
        frame_args.frameReport,
    )
    if sim_type == "opal":
        import sirepo.template.opal

        frame_args.x = "x"
        frame_args.y = "px"
        return sirepo.template.opal._bunch_plot(
            frame_args,
            frame_args.run_dir.join(run_dir),
            frame_args.frameIndex,
        )
    if sim_type == "elegant":
        import sirepo.template.elegant

        frame_args.x = "x"
        frame_args.y1 = "xp"
        return sirepo.template.elegant._extract_report_data(
            str(frame_args.run_dir.join(f"{run_dir}/run_setup.output.sdds")),
            frame_args,
        )
    raise AssertionError("unhandled sim_type for sim_frame(): {}".format(sim_type))


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
                    modelName=f"sim{idx + 1}Animation",
                    frameCount=1,
                ),
            )
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


def _sim_type_and_run_dir_from_report_name(models, report):
    m = re.match(r"sim(\d+)Animation", report)
    assert m
    idx = int(m.group(1))
    return (
        models.simWorkflow[f"simType_{idx}"],
        f"run{idx}",
    )
