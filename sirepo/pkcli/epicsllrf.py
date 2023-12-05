# -*- coding: utf-8 -*-
"""Wrapper to run epicsllrf from the command line.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common, epicsllrf
from sirepo import simulation_db


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
    dm = simulation_db.read_json(template_common.INPUT_BASE_NAME).models
    s = dm.epicsServer.serverAddress
    f = _epics_fields(dm)
    if epicsllrf.run_epics_cmd(f"pvget {f[0]}", s) != 0:
        raise epicsllrf.EpicsDisconnectError(
            "Unable to connect to EPICS server: {}".format(s)
        )
    epicsllrf.run_epics_cmd(f"pvmonitor {' '.join(f)} | python parameters.py", s)


def _epics_fields(models):
    r = []
    p = models.epicsConfig.epicsModelPrefix
    for m in models:
        if p in m:
            for k in models[m]:
                r.append(epicsllrf.epics_field_name(p, m, k))
    return r
