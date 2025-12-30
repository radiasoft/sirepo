"""Myapp execution template.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo.template import template_common
import copy
import csv
import re
import sirepo.sim_data
import sirepo.util
import time


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

INPUT_NAME = "hundli.yml"

OUTPUT_NAME = "hundli.csv"


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=0,
        frameCount=0,
        reports=[],
    )
    if run_dir.join(OUTPUT_NAME).exists() and not is_running:
        res.pkupdate(
            frameCount=1,
            reports=[
                PKDict(
                    modelName="activityAnimation",
                    frameCount=1,
                ),
            ],
        )
    return res


def report_from_csv(title, fields):

    def _csv_to_cols():
        with open(OUTPUT_NAME, "r") as f:
            rows = csv.reader(f)
            headers = next(rows)
            cols = [[] for _ in headers]
            for row in rows:
                for i, c in enumerate(row):
                    cols[i].append(float(c))
        return PKDict((k.lower(), cols[i]) for i, k in enumerate(headers))

    def _label(field):
        return SCHEMA.model.dog[field][0]

    def _plot(field, cols):
        return {
            "name": field,
            "label": _label(field),
            "points": cols[field],
        }

    cols = _csv_to_cols()
    x_points = cols["year"]
    plots = [_plot(f, cols) for f in fields]
    return PKDict(
        title=title,
        x_range=[x_points[0], x_points[-1]],
        y_label=_label(fields[0]) if len(fields) == 1 else "",
        x_label="Age (years)",
        x_points=x_points,
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
    )


def sim_frame_activityAnimation(frame_args):
    return report_from_csv(
        "Dog Activity Over Time",
        ("activity",),
    )


def stateless_compute_global_resources(data, **kwargs):
    import sirepo.global_resources

    return sirepo.global_resources.for_simulation(
        data.simulationType, data.simulationId
    )


def stateful_compute_sim_data(data, **kwargs):
    assert pkconfig.channel_in_internal_test()
    m = data.args.test_method
    if m.startswith("[a-z]"):
        raise AssertionError(f"invalid method={m}")
    return getattr(sim_data, m)(**data.args.test_kwargs)


def get_data_file(run_dir, model, frame, options):
    if options.suffix == "sr_long_analysis":
        # Not asyncio.sleep: not in coroutine (job_cmd)
        time.sleep(100)
    return OUTPUT_NAME


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    m = re.search("^user_alert=(.*)", data.models.dog.breed)
    if m:
        raise sirepo.util.UserAlert(m.group(1), "log msg should not be sent")
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    if "report" in data:
        if data.report not in ("activityAnimation", "heightWeightReport"):
            raise AssertionError(f"unknown report: {data.report}")
    v = copy.deepcopy(data.models, PKDict())
    v.input_name = INPUT_NAME
    v.output_name = OUTPUT_NAME
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )
