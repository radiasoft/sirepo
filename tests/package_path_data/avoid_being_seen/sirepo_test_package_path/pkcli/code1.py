"""Wrapper to run myapp from the command line.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pksubprocess
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import sirepo_test_package_path.template.code1 as template
import sys


_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)


def run(cfg_dir):
    pksubprocess.check_call_with_signals(
        [sys.executable, template_common.PARAMETERS_PYTHON_FILE],
    )
    template_common.write_sequential_result(PKDict(
        title='A title',
        x_range=[0, 10],
        y_label='y label',
        x_label='x label',
        x_points=[0,2,4,6,8,10],
        y_range=[1, 8],
    ))
