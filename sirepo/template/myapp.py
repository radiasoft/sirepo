"""Myapp execution template.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern import pkconfig
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import copy
import sirepo.sim_data
import re
import sirepo.util
import time


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

INPUT_NAME = "hundli.yml"

OUTPUT_NAME = "hundli.csv"


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
        if data.report != "heightWeightReport":
            raise AssertionError(f"unknown report: {data.report}")
    v = copy.deepcopy(data.models, PKDict())
    v.input_name = INPUT_NAME
    v.output_name = OUTPUT_NAME
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )
