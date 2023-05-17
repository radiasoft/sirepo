# -*- coding: utf-8 -*-
"""Wrapper to run epicsllrf from the command line.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common, epicsllrf
from sirepo import simulation_db
import sirepo.sim_data
import subprocess


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

def run(cfg_dir):
    plots = [
        PKDict(
            points=[0, 0],
            label="",
        ),
    ]
    # write out a dummy plot, real plot data is returned from template.epicsllrf.background_percent_complete
    template_common.write_sequential_result(
        PKDict(
            title="",
            x_range=[0, 1],
            y_label="",
            x_label="",
            x_points=[0, 1],
            plots=plots,
            y_range=template_common.compute_plot_color_and_range(plots),
        ),
    )


def run_background(cfg_dir):
    subprocess.Popen(
        f"pvmonitor {_epics_fields()} | python parameters.py",
        shell=True,
        stdin=subprocess.PIPE,
        env=epicsllrf.epics_env(
            simulation_db.read_json(
                template_common.INPUT_BASE_NAME
            ).models.epicsServer.serverAddress
        ),
    ).wait()

def _epics_fields():
    r = []
    for model in SCHEMA.model:
        if SCHEMA.constants.epicsModelPrefix in model:
            for k in SCHEMA.model[model]:
                r.append(model.replace("_", ":") + ":" + k)
    pkdp("\n\n\nr={}", "\n ".join(r))
    return " ".join(r)