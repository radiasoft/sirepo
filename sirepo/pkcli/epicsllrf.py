# -*- coding: utf-8 -*-
"""Wrapper to run epicsllrf from the command line.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common, epicsllrf
from sirepo import simulation_db
import subprocess


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
        "pvmonitor LLRFSim:Cav:Q LLRFSim:Cav:R LLRFSim:Cav:Vr LLRFSim:Cav:Vt LLRFSim:Cav:Z0 LLRFSim:Cav:beta LLRFSim:Cav:dw LLRFSim:Cav:phiC LLRFSim:Cav:rphase LLRFSim:Cav:tphase LLRFSim:Cav:w0 LLRFSim:Cav:wC LLRFSim:Gen:I0S LLRFSim:Gen:Ig LLRFSim:Gen:amp LLRFSim:Gen:duration LLRFSim:Gen:noise LLRFSim:Gen:phase LLRFSim:Gen:phiG LLRFSim:Gen:phiS LLRFSim:Gen:rho LLRFSim:Gen:signal_type LLRFSim:Gen:start LLRFSim:Gen:wG LLRFSim:Gen:wS LLRFSim:Sim:num_pulse LLRFSim:Sim:timestep | python parameters.py",
        shell=True,
        stdin=subprocess.PIPE,
        env=epicsllrf.epics_env(
            simulation_db.read_json(
                template_common.INPUT_BASE_NAME
            ).models.epicsServer.serverAddress
        ),
    ).wait()
