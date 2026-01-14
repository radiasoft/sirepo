"""cortex execution template.

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import pykern.pkio
import sirepo.sim_data
import sirepo.template.openmc

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_TILE_OUTPUT = ("dpa", "flux", "he", "n_flux_spectrum", "p_flux_spectrum")


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
                )
                for idx, n in enumerate(_TILE_OUTPUT)
            ],
        )
    return PKDict(
        frameCount=0,
        percentComplete=0,
    )


def sim_frame(frame_args):
    s = frame_args.stat
    with open(str(frame_args.run_dir.join(f"{s}.png.json")), "r") as f:
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
    return PKDict(
        title="",
        x_range=[x[0], x[-1]],
        y_label=d.ylabel,
        x_label=d.xlabel,
        x_points=x,
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
    )


def write_parameters(data, run_dir, is_parallel):
    pykern.pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        template_common.render_jinja(
            SIM_TYPE,
            PKDict(
                materialDirectory=sirepo.sim_run.cache_dir(
                    sirepo.template.openmc.OPENMC_CACHE_DIR
                ),
            ),
            "tile.py",
        ),
    )
    return None
