# -*- coding: utf-8 -*-
"""Wrapper to run accel from the command line.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common, accel
from sirepo import simulation_db
import subprocess


def run(cfg_dir):
    plots = [
        PKDict(
            points=[0, 0],
            label="",
        ),
    ]
    # write out a dummy plot, real plot data is returned from template.accel.background_percent_complete
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
        "camonitor MTEST:Run MTEST:MaxPoints MTEST:UpdateTime MTEST:TimePerDivision MTEST:TriggerDelay MTEST:VoltOffset MTEST:NoiseAmplitude MTEST:Waveform MTEST:TimeBase MTEST:MinValue MTEST:MaxValue MTEST:MeanValue | python parameters.py",
        shell=True,
        stdin=subprocess.PIPE,
        env=accel.epics_env(simulation_db.read_json(template_common.INPUT_BASE_NAME).models.epicsServer.serverAddress),
    ).wait()
