"""cortex execution template.

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import asyncio
import math
import numpy
import os
import pykern.pkio
import re
import sirepo.mpi
import sirepo.quest
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.template.openmc

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_CHAIN_ENDF_FILE = "chain_endf_b8.0.xml"
_EUDEMO_H5M_FILE = "eudemo_f_1_27a.h5m"
_SLAB_CHAIN_ENDF_FILE = "chain_endfb80_sfr.xml"
_SURFACE_SOURCE_FILE = "surface_source.h5"
_TOKAMAK_INPUTS_FILE = "Tokamak_inputs.json"
_REPORT_TITLE = PKDict(
    tileAnimation=PKDict(
        dpa="DPA",
        flux="Flux",
        he="Helium",
        n_flux_spectrum="Neutron Flux",
        p_flux_spectrum="Photon Flux",
        sdr="Shutdown Dose",
    ),
    slabAnimation=PKDict(
        dpa_OB_1_b6="DPA",
        h1_OB_1_b6="Hydrogen",
        he_OB_1_b6="Helium",
        flux_total_OB_1_b6="Flux",
        heating_OB_1_b6="Heating",
        p_flux_spectrum_OB_1_b6="Photon Flux",
        n_flux_spectrum_OB_1_b6="Neutron Flux",
        activity_all_cells="Total Activity over cooling time",
        activity_cell_Armor="Activity - Armor",
        activity_cell_First_Wall="Activity - First Wall",
        activity_cell_OB_1="Activity - OB_1",
        activity_cell_OB_2="Activity - OB_2",
        activity_cell_OB_3="Activity - OB_3",
        activity_cell_OB_4="Activity - OB_4",
        activity_cell_OB_5="Activity - OB_5",
        activity_cell_OB_6="Activity - OB_6",
        activity_cell_OB_7="Activity - OB_7",
        activity_cell_OB_8="Activity - OB_8",
        activity_cell_VV="Activity - VV",
        decayheat_all_cells="Total decay heat",
        decayheat_Armor="Decay heat - Armor",
        decayheat_First_Wall="Decay heat - First Wall",
        decayheat_OB_1="Decay heat - OB1",
        decayheat_OB_2="Decay heat - OB2",
        decayheat_OB_3="Decay heat - OB3",
        decayheat_OB_4="Decay heat - OB4",
        decayheat_OB_5="Decay heat - OB5",
        decayheat_OB_6="Decay heat - OB6",
        decayheat_OB_7="Decay heat - OB7",
        decayheat_OB_8="Decay heat - OB8",
        decayheat_VV="Decay heat - VV",
        radial_activity_profiles="Radial profile of Total activity per cooling time",
        radial_decayheat_profiles="Radial profile of decay heat per cooling time",
        sdr_profile_OB_1_b6="D1S spatial profile: OB_1_b6",
    ),
)

_SIM_JINJA = PKDict(
    slabAnimation="slab",
    tileAnimation="tile",
)

_SIM_OUTPUT = PKDict(
    slabAnimation=list(_REPORT_TITLE.slabAnimation.keys()),
    tileAnimation=list(_REPORT_TITLE.tileAnimation.keys()),
)


def background_percent_complete(report, run_dir, is_running):
    o = _SIM_OUTPUT[report]
    if not is_running and run_dir.join(_json_filename(o[0])).exists():
        _save_plots_to_database(run_dir, report, o)
        return PKDict(
            frameCount=1,
            percentComplete=100,
            reports=[],
        )
    return PKDict(
        frameCount=0,
        percentComplete=0,
    )


def plotdef_to_sim_frame(plotdef):

    def _section(stat):
        if "_flux" in stat:
            return "flux"
        if "activity" in stat or "decayheat" in stat:
            return "time_dependent"
        return "steady_state"

    res = PKDict(
        title=plotdef.title,
        x_range=[plotdef.points[0][0], plotdef.points[0][-1]],
        y_label=plotdef.ylabel,
        x_label=plotdef.xlabel,
        x_points=plotdef.points[0],
        plots=[
            PKDict(
                points=plotdef.points[i],
                label=plotdef.legend[i],
            )
            for i in range(1, len(plotdef.points))
        ],
        type=plotdef.plot_type,
        meta=PKDict(
            model=plotdef.model,
            stat=plotdef.stat,
            section=_section(plotdef.stat),
        ),
    )
    res.y_range = template_common.compute_plot_color_and_range(res.plots)
    # if res.y_range[1] - res.y_range[0] < 10:
    #     res.type = "linear"
    if plotdef.stat == "flux" or plotdef.stat == "sdr":
        res.alignLegend = "right"
    if res.type == "loglog" or res.type == "semilog":
        _adjust_log_ranges(res)
    return res


def write_parameters(data, run_dir, is_parallel):
    pykern.pkio.write_text(
        "cortex_plot.py",
        template_common.render_jinja(SIM_TYPE, PKDict(), "cortex_plot.py"),
    )
    pykern.pkio.write_text(
        "cortex_materials.py",
        template_common.render_jinja(SIM_TYPE, PKDict(), "cortex_materials.py"),
    )
    v = PKDict()
    if data.report == "tileAnimation":
        v.pkupdate(
            chainPath=sirepo.template.openmc.remote_datafile_path(_CHAIN_ENDF_FILE),
        )
    elif data.report == "slabAnimation":
        v.pkupdate(
            chainPath=sirepo.template.openmc.remote_datafile_path(
                _SLAB_CHAIN_ENDF_FILE
            ),
            eudemoH5m=sirepo.template.openmc.remote_datafile_path(
                _EUDEMO_H5M_FILE, compress=False
            ),
            tokamakInputs=sirepo.template.openmc.remote_datafile_path(
                _TOKAMAK_INPUTS_FILE, compress=False
            ),
            surfaceSource=sirepo.template.openmc.remote_datafile_path(
                _SURFACE_SOURCE_FILE, compress=False
            ),
        )

    pykern.pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        template_common.render_jinja(
            SIM_TYPE,
            template_common.flatten_data(data.models, PKDict())
            .pkupdate(
                materialDefinition=_generate_material_definition(data),
                materialDirectory=sirepo.sim_run.cache_dir(
                    sirepo.template.openmc.OPENMC_CACHE_DIR
                ),
                openmcRunArgs=f"threads={sirepo.mpi.cfg().cores}",
            )
            .pkupdate(v),
            f"{_SIM_JINJA[data.report]}.py",
        ),
    )
    return None


def _adjust_log_ranges(plot):
    min_value = None
    for p in plot.plots:
        v = numpy.array(p.points)
        v[v <= 0] = 1e-24
        p.points = v.tolist()
        m = numpy.min(v[v > 1e-24])
        if min_value is None or m < min_value:
            min_value = m
    plot.y_range[0] = min_value


def _generate_material_definition(data):
    m = data.models.material
    components = ""
    for c in m.components:
        components += f"""
            PKDict(
                {c.component_type}="{c.component}",
                percent={c.percent / 100.0},
            ),"""
    return f"""
# this import add openmc.Materials.download_cross_section_data()
import openmc_data_downloader
from pykern.pkcollections import PKDict
# import generated modules from work directory
import sys
sys.path.append('.')
# replaces matplotlib with stub which saves plot data
from cortex_plot import plt
import cortex_materials as materials


def material_from_definition(definition):
    m = openmc.Material()
    for c in definition.components:
        if "element" in c:
            m.add_element(c.element, c.percent, definition.percent_type)
        elif "nuclide" in c:
            m.add_nuclide(c.nuclide, c.percent, definition.percent_type)
        else:
            raise AssertionError(f"unhandled material component {{c}}")
    m.set_density("g/cc", definition.density_gcc)
    return m


t = material_from_definition(
    PKDict(
        density_gcc={m.density},
        percent_type="{m.percent_type}",
        components=[{components}
        ],
    )
)"""


def _json_filename(stat):
    return f"{stat}.png.json"


def _material_id_from_run_dir(run_dir):
    return int(
        sirepo.simulation_db.read_json(
            run_dir.join(template_common.INPUT_BASE_NAME)
        ).models.material.material_id
    )


def _plot_from_file(run_dir, material_id, report, stat):
    def _label(value):
        return re.sub(r"\$\^2\$", "²", value)

    def _process_points(plot, dim):
        # convert NaN to 0
        for i in range(len(plot[dim])):
            if math.isnan(plot[dim][i]):
                plot[dim][i] = 0
        if plot.get("_type", "") != "step":
            return plot[dim]
        r = []
        for i in range(len(plot.x) - 1):
            if dim == "x":
                r.append(plot.x[i])
                r.append(plot.x[i + 1])
            else:
                r.append(plot.y[i])
                r.append(plot.y[i])
        return r

    with open(str(run_dir.join(_json_filename(stat))), "r") as f:
        d = pykern.pkjson.load_any(f)

    # TODO(pjm): assert x points match across plots
    points = [_process_points(d.plots[0], "x")]
    legend = [""]
    for p in d.plots:
        points.append(_process_points(p, "y"))
        legend.append(p.label or d.ylabel)
    return PKDict(
        material_id=material_id,
        title="",
        xlabel=_label(d.xlabel),
        ylabel=_label(d.ylabel),
        plot_type=d.type or "linear",
        model=report,
        stat=stat,
        legend=legend,
        points=points,
    )


def _save_plots_to_database(run_dir, report, stats):

    async def call_db(material_id, plot):
        with sirepo.quest.start(in_pkcli=True) as qcall:
            with qcall.auth.logged_in_user_set(
                os.environ["SIREPO_AUTH_LOGGED_IN_USER"]
            ):
                r = await qcall.call_api(
                    "cortexDb",
                    body=PKDict(
                        op_name="insert_plot",
                        op_args=PKDict(
                            plot=plot,
                        ),
                    ),
                )

    m = _material_id_from_run_dir(run_dir)
    for s in stats:
        p = _plot_from_file(run_dir, m, report, s)
        asyncio.run(call_db(m, p))
