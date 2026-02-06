"""cortex execution template.

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import numpy
import pykern.pkio
import re
import sirepo.sim_data
import sirepo.template.openmc

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_CHAIN_ENDF_FILE = "chain_endf_b8.0.xml"
_REPORT_TITLE = PKDict(
    dpa="DPA",
    flux="Flux",
    he="Helium",
    n_flux_spectrum="Neutron Flux",
    p_flux_spectrum="Photon Flux",
    sdr="Shutdown Dose",
)
_TILE_OUTPUT = list(_REPORT_TITLE.keys())


def _tile_filename(base):
    return f"{base}.png.json"


def background_percent_complete(report, run_dir, is_running):
    if not is_running and run_dir.join(_tile_filename(_TILE_OUTPUT[0])).exists():
        return PKDict(
            frameCount=1,
            percentComplete=0,
            reports=[
                PKDict(
                    modelName="tileAnimation",
                    modelIndex=idx,
                    stat=n,
                    frameCount=1,
                    title=_REPORT_TITLE[n],
                )
                for idx, n in enumerate(_TILE_OUTPUT)
            ],
        )
    return PKDict(
        frameCount=0,
        percentComplete=0,
    )


def sim_frame(frame_args):
    def _label(value):
        return re.sub(r"\$\^2\$", "²", value)

    s = frame_args.stat
    with open(str(frame_args.run_dir.join(_tile_filename(s))), "r") as f:
        d = pykern.pkjson.load_any(f)

    # TODO(pjm): assert x points match across plots
    x = d.plots[0].x
    plots = []
    for p in d.plots:
        plots.append(
            PKDict(
                points=p.y,
                label=p.label or d.ylabel,
            )
        )
    res = PKDict(
        title="",
        x_range=[x[0], x[-1]],
        y_label=_label(d.ylabel),
        x_label=_label(d.xlabel),
        x_points=x,
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
        type=d.type or "linear",
    )
    if res.y_range[1] - res.y_range[0] < 10:
        res.type = "linear"
    if s == "flux" or s == "sdr":
        res.alignLegend = "right"
    if d.type == "loglog" or d.type == "semilog":
        _adjust_log_ranges(res)
    return res


def _adjust_log_ranges(plot):
    min_value = None
    for p in plot.plots:
        v = numpy.array(p.points)
        v[v <= 0] = 1
        p.points = v.tolist()
        m = numpy.min(v[v > 1])
        if min_value is None or m < min_value:
            min_value = m
    plot.y_range[0] = min_value


def write_parameters(data, run_dir, is_parallel):
    pykern.pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        template_common.render_jinja(
            SIM_TYPE,
            template_common.flatten_data(data.models, PKDict()).pkupdate(
                materialComponents=data.models.material.components,
                materialDirectory=sirepo.sim_run.cache_dir(
                    sirepo.template.openmc.OPENMC_CACHE_DIR
                ),
                chainPath=sirepo.template.openmc.remote_datafile_path(_CHAIN_ENDF_FILE),
            ),
            "tile.py",
        ),
    )
    return None
