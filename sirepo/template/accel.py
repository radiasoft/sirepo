# -*- coding: utf-8 -*-
"""accel execution template.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import re
import sirepo.sim_data
import sirepo.util

_STATUS_FILE = "status.json"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def background_percent_complete(report, run_dir, is_running):
    return PKDict(
        percentComplete=100,
        frameCount=0,
        epicsData=_read_epics_data(run_dir),
    )


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    v.statusFile = _STATUS_FILE
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )


def _read_epics_data(run_dir):
    s = run_dir.join(_STATUS_FILE)
    if s.exists():
        d = simulation_db.json_load(s)
        for f in d:
            v = d[f][0]
            if re.search(r"[A-Za-z]", v):
                pass
            elif " " in v:
                v = [float(x) for x in v.split(" ")]
            else:
                v = float(v)
            d[f] = v
        pkdp("\n\n\nd={}", d)
        if _disconected(d):
            raise sirepo.util.UserAlert("Disconnected from Process Variables")
        return d
    return PKDict()


def _disconected(process_variables):
    for k in process_variables:
        if type(process_variables[k]) == float:
            continue
        if "disconnected" in process_variables[k]:
            return True
    return False
