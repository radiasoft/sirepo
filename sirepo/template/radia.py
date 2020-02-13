# -*- coding: utf-8 -*-
u"""Myapp execution template.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkcollections import PKDict
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
from sirepo.template import radia_tk
import copy
import sirepo.sim_data
import re
import sirepo.util


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

GEOM_PYTHON_FILE = 'geom.py'

geom_mgr = radia_tk.RadiaGeomMgr()


def extract_report_data(run_dir, sim_in):
    if 'geometry' in sim_in.report:
        simulation_db.write_result(pkio.read_text('geometry.json'), run_dir=run_dir)
        return
    simulation_db.write_result(PKDict(), run_dir=run_dir)

def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    #v = copy.deepcopy(data['models'], pkcollections.Dict())
    # add parameters
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        GEOM_PYTHON_FILE,
    )
