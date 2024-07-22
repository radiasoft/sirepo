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
from sirepo.template import template_common
import math
import numpy
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
DISTRIBUTION_PYTHON_FILE = "distribution.py"


def code_var(variables):
    return code_variable.CodeVar(
        variables,
        code_variable.PurePythonEval(
            PKDict(
                pi=math.pi,
            )
        ),
    )


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


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(DISTRIBUTION_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _bunch_plot(run_dir, model):
    _M = PKDict(
        x="position/x",
        px="momentum/x",
        y="position/y",
        py="momentum/y",
        t="position/t",
        pt="momentum/t",
        qm="qm",
    )

    def _points(file, frame_index, name):
        return numpy.array(file[f"data/2/particles/beam/{_M[name]}"])

    def _format_plot(h5file, field):
        return field

    def _title(file, frame_index):
        return ""

    fn = "diags/openPMD/monitor.h5"
    return hdf5_util.HDF5Util(str(run_dir.join(fn))).heatmap(
        PKDict(
            format_plot=_format_plot,
            frame_index=0,
            model=model,
            points=_points,
            title=_title,
        )
    )


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    return res + template_common.render_jinja(SIM_TYPE, v, DISTRIBUTION_PYTHON_FILE)
