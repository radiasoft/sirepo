# -*- coding: utf-8 -*-
"""epicsllrf execution template.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
import filecmp
import os
import re
import shutil
import sirepo.sim_data
import subprocess

_STATUS_FILE = "status.json"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


class EpicsDisconnectError(Exception):
    pass


def background_percent_complete(report, run_dir, is_running):
    return PKDict(
        percentComplete=100,
        frameCount=0,
        alert=_parse_epics_log(run_dir),
        hasEpicsData=run_dir.join(_STATUS_FILE).exists(),
    )


def epics_field_name(model_name, field):
    return model_name.replace("_", ":") + ":" + field


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def run_epics_cmd(cmd, server_address):
    env = os.environ.copy()
    env["EPICS_PVA_AUTO_ADDR_LIST"] = "NO"
    if ":" in server_address:
        env["EPICS_PVA_ADDR_LIST"] = server_address.split(":")[0]
        env["EPICS_PVA_SERVER_PORT"] = server_address.split(":")[1]
    else:
        env["EPICS_PVA_ADDR_LIST"] = server_address
    # TODO (gurhar1133): validate cmd
    return subprocess.Popen(
        cmd,
        env=env,
        shell=True,
        stdin=subprocess.PIPE,
    ).wait()


def stateless_compute_read_epics_values(data, **kwargs):
    _PREV_EPICS_FILE = "prev-status.json"
    # TODO(pjm): hacked in animation directory
    run_dir = pkio.py_path(
        re.sub(r"/unused$", "/animation", str(simulation_db.simulation_run_dir(data)))
    )
    p = run_dir.join(_PREV_EPICS_FILE)
    e = run_dir.join(_STATUS_FILE)
    if (
        not data.get("noCache")
        and e.exists()
        and p.exists()
        and filecmp.cmp(str(e), str(p), False)
    ):
        return PKDict()
    shutil.copyfile(str(e), str(p))
    return PKDict(
        epicsData=_read_epics_data(run_dir),
    )


def stateless_compute_update_epics_value(data, **kwargs):
    for f in data.fields:
        if (
            run_epics_cmd(
                f"pvput {epics_field_name(data.model, f.field)} {f.value}",
                data.serverAddress,
            )
            != 0
        ):
            return PKDict(
                success=False,
                error=f"Unable to connect to EPICS server: {data.serverAddress}",
            )
    return PKDict(success=True)


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
            if re.search(r"[A-Za-z]{2}", v):
                v = re.sub(r"\(\d+\)", "", v)
            elif v[0] == "[":
                v = re.sub(r"\[|\]", "", v)
                v = [float(x) for x in v.split(",")]
            else:
                v = float(v)
            d[f] = v
        return d
    return PKDict()


def _parse_epics_log(run_dir):
    res = ""
    with pkio.open_text(run_dir.join(template_common.RUN_LOG)) as f:
        for line in f:
            m = re.match(
                r"sirepo.template.epicsllrf.EpicsDisconnectError:\s+(.+)", line
            )
            if m:
                return m.group(1)
    return res
