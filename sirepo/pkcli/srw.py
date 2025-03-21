"""Wrapper to run SRW from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo.job
import sirepo.template


def python_to_json(run_dir=".", in_py="in.py", out_json="out.json"):
    """Run importer in run_dir trying to import py_file

    Args:
        run_dir (str): clean directory except for in_py
        in_py (str): name of the python file in run_dir
        out_json (str): valid json matching SRW schema
    """
    from sirepo.template import srw_importer

    with pkio.save_chdir(run_dir):
        out = srw_importer.python_to_json(in_py)
        with open(out_json, "w") as f:
            f.write(out)
    return "Created: {}".format(out_json)


def run(cfg_dir):
    """Run srw in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run srw in
    """
    srw = sirepo.template.import_module("srw")
    sim_in = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    r = template_common.exec_parameters()
    m = sim_in.report
    if m == "backgroundImport":
        # special case for importing python code
        template_common.write_sequential_result(
            PKDict({srw.PARSED_DATA_ATTR: r.parsed_data})
        )
    else:
        template_common.write_sequential_result(
            srw.extract_report_data(sim_in),
        )
