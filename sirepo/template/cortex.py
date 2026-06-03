"""cortex execution template.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import csv
import io
import math
import numpy
import os
import pykern.pkcompat
import pykern.pkio
import pykern.pkjson
import re
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.template.openmc

CORTEX_RUN_LOG = "cortex.log"
STATEPOINTS = ["neutronics", "depletion"]
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
        activity_cell_First_wall="Activity - First Wall",
        activity_cell_Breeder_layer_1="Activity - Breeder layer 1",
        activity_cell_Breeder_layer_2="Activity - Breeder layer 2",
        activity_cell_Breeder_layer_3="Activity - Breeder layer 3",
        activity_cell_Breeder_layer_4="Activity - Breeder layer 4",
        activity_cell_Breeder_layer_5="Activity - Breeder layer 5",
        activity_cell_Breeder_layer_6="Activity - Breeder layer 6",
        activity_cell_Breeder_layer_7="Activity - Breeder layer 7",
        activity_cell_Breeder_layer_8="Activity - Breeder layer 8",
        activity_cell_Breeder_layer_9="Activity - Breeder layer 9",
        activity_cell_VV="Activity - VV",
        decayheat_all_cells="Total decay heat",
        decayheat_Armor="Decay heat - Armor",
        decayheat_First_wall="Decay heat - First Wall",
        decayheat_Breeder_layer_1="Decay heat - Breeder layer 1",
        decayheat_Breeder_layer_2="Decay heat - Breeder layer 2",
        decayheat_Breeder_layer_3="Decay heat - Breeder layer 3",
        decayheat_Breeder_layer_4="Decay heat - Breeder layer 4",
        decayheat_Breeder_layer_5="Decay heat - Breeder layer 5",
        decayheat_Breeder_layer_6="Decay heat - Breeder layer 6",
        decayheat_Breeder_layer_7="Decay heat - Breeder layer 7",
        decayheat_Breeder_layer_8="Decay heat - Breeder layer 8",
        decayheat_Breeder_layer_9="Decay heat - Breeder layer 9",
        decayheat_VV="Decay heat - VV",
        radial_activity_profiles="Radial profile of Total activity per cooling time",
        radial_decayheat_profiles="Radial profile of decay heat per cooling time",
    ),
)

_SIM_JINJA = PKDict(
    slabAnimation="slab",
    tileAnimation="tile",
)

SIM_VERSION = PKDict(
    hcllSlabAnimation="1.01",
    hcpbSlabAnimation="1.01",
    tileAnimation="1.05",
    wcllSlabAnimation="1.01",
)

_SIM_OUTPUT = PKDict(
    slabAnimation=list(_REPORT_TITLE.slabAnimation.keys()),
    tileAnimation=list(_REPORT_TITLE.tileAnimation.keys()),
)

_SAVE_SIM_RESULTS = PKDict(
    # TODO(pjm): choosing WCLL as the standard
    wcllSlabAnimation=PKDict(
        dpa_OB_1_b6=[[1, 45, "DPA at 45cm"]],
        h1_OB_1_b6=[[1, 45, "H at 45cm"]],
        he_OB_1_b6=[[1, 45, "He at 45cm"]],
        activity_all_cells=[
            [1, 100, "Armor activity at 100 years"],
            [2, 100, "First wall activity at 100 years"],
        ],
    ),
)

_SIM_TIME = PKDict(
    tileAnimation=104,
    # TODO(pjm): measure this
    slabAnimation=679,
)
_LOG_TIME = PKDict(
    tileAnimation=[
        [v[0], v[1] / _SIM_TIME.tileAnimation]
        for v in (
            ["setting OPENMC_CROSS_SECTIONS", 10],
            ["Creating state point", 20],
            ["Performing D1S run", 30],
            ["Performing R2S Activation run", 40],
            ["Creating state point statepoint", 50],
            ["Simulating batch 25", 60],
            ["Simulating batch 25", 70],
            ["Creating state point", 80],
            ["OpenMP Threads", 90],
            ["Simulating batch 1", 100],
        )
    ],
    # TODO(pjm): measure this
    slabAnimation=[
        [v[0], v[1] / _SIM_TIME.slabAnimation]
        for v in (
            ["Reading model XML file", 50],
            ["Simulating batch 2", 75],
            ["Simulating batch 3", 93],
            ["Simulating batch 4", 111],
            ["Simulating batch 5", 128],
            ["Simulating batch 6", 147],
            ["Simulating batch 7", 165],
            ["Simulating batch 8", 182],
            ["Simulating batch 9", 200],
            ["Simulating batch 10", 217],
            ["Performing D1S run", 244],
            ["Simulating batch 1", 252],
            ["Simulating batch 2", 274],
            ["Simulating batch 3", 297],
            ["Simulating batch 4", 319],
            ["Simulating batch 5", 342],
            ["Simulating batch 6", 364],
            ["Simulating batch 7", 387],
            ["Simulating batch 8", 410],
            ["Simulating batch 9", 432],
            ["Simulating batch 10", 454],
            ["Creating state point", 476],
            ["Simulating batch 1", 488],
            ["Simulating batch 2", 503],
            ["Simulating batch 3", 520],
            ["Simulating batch 4", 535],
            ["Simulating batch 5", 551],
            ["Simulating batch 6", 566],
            ["Simulating batch 7", 582],
            ["Simulating batch 8", 597],
            ["Simulating batch 9", 613],
            ["Simulating batch 10", 629],
            ["Creating state point", 644],
        )
    ],
)


def background_percent_complete(report, run_dir, is_running):

    def _percent_complete():
        r = 0
        i = 0
        log_time = _LOG_TIME[_report_type(report)]
        n = run_dir.join(CORTEX_RUN_LOG)
        if n.exists():
            with pykern.pkio.open_text(n) as f:
                for line in f:
                    if log_time[i][0] in line:
                        r = log_time[i][1]
                        i += 1
                        if i >= len(log_time):
                            break
        return r * 100

    o = _SIM_OUTPUT[_report_type(report)]
    if not is_running and run_dir.join(_json_filename(o[0])).exists():
        _save_summary_to_database(run_dir, report, o)
        return PKDict(
            frameCount=1,
            percentComplete=100,
            reports=[],
        )
    return PKDict(
        frameCount=0,
        percentComplete=_percent_complete(),
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
    elif "SlabAnimation" in data.report:
        t = re.search(r"(\w+)SlabAnimation", data.report).group(1).upper()
        for n in (
            f"EUDEMO_{t}_inputs.json",
            f"{t}_surface_source.h5",
            f"{t}_armor_current_neutron.json",
        ):
            sirepo.template.openmc.remote_datafile_path(n, compress=False)
        v.pkupdate(
            chainPath=sirepo.template.openmc.remote_datafile_path(
                _SLAB_CHAIN_ENDF_FILE
            ),
            dagmcPath=sirepo.template.openmc.remote_datafile_path(
                f"eudemo_{t.lower()}.h5m", compress=False
            ).dirname,
            surfaceSource=sirepo.template.openmc.remote_datafile_path(
                _SURFACE_SOURCE_FILE, compress=False
            ),
            slabType=t,
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
            )
            .pkupdate(v),
            f"{_SIM_JINJA[_report_type(data.report)]}.py",
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


def _csv_from_plot(plot):
    v = io.StringIO()
    w = csv.writer(v)
    w.writerow([plot.xlabel] + plot.legend[1:])
    for i in range(len(plot.points[0])):
        w.writerow([plot.points[j][i] for j in range(len(plot.points))])
    return v.getvalue()


def _generate_material_definition(data):
    m = data.models.material
    components = ""
    for c in m.components:
        components += f"""
            PKDict(
                {c.component_type}="{c.component}",
                percent={c.percent / 100.0},
            ),"""
    material_directory = sirepo.sim_run.cache_dir(
        sirepo.template.openmc.OPENMC_CACHE_DIR
    )
    return f"""
# this import add openmc.Materials.download_cross_section_data()
import openmc_data_downloader
from pykern.pkcollections import PKDict
import openmc.deplete.pool
import pykern.pkrunpy
import shutil

# RS: disable multiprocessing, there is no way to set process count
openmc.deplete.pool.USE_MULTIPROCESSING = False
# replaces matplotlib with stub which saves plot data
plt = pykern.pkrunpy.run_path_as_module("cortex_plot.py").pyplot
materials = pykern.pkrunpy.run_path_as_module("cortex_materials.py")


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

sp_count = 0
sp_names = {STATEPOINTS}

def rsdownload(materials):
    materials.download_cross_section_data(
        libraries=["ENDFB-8.0-NNDC", "ENDFB-7.1-NNDC", "FENDL-3.1d", "TENDL-2019"],
        destination="{ material_directory }",
    )

def rsrun(statepoint):
    global sp_count
    if sp_count < len(sp_names):
        shutil.copy(statepoint, f"{{sp_names[sp_count]}}.hdf5")
    sp_count += 1
    return statepoint


t = material_from_definition(
    PKDict(
        density_gcc={m.density},
        percent_type="{m.percent_type}",
        components=[{components}
        ],
    )
)"""


def _json_filename(stat):
    return f"{_png_filename(stat)}.json"


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
        title=_REPORT_TITLE[_report_type(report)][stat],
        xlabel=_label(d.xlabel),
        ylabel=_label(d.ylabel),
        plot_type=d.type or "linear",
        model=report,
        stat=stat,
        legend=legend,
        points=points,
    )


def _png_filename(stat):
    return f"{stat}.png"


def _report_type(report):
    return re.sub(r"(\w+S)(labAnimation)", r"s\2", report)


def _save_summary_to_database(run_dir, report, stats):
    m = _material_id_from_run_dir(run_dir)
    summary = PKDict(
        material_id=m,
        model=report,
        version=SIM_VERSION[report],
        completed=pykern.pkcompat.utcnow(),
        plots=[],
        values=PKDict(),
    )
    for s in stats:
        p = _plot_from_file(run_dir, m, report, s)
        p.csv = _csv_from_plot(p)
        summary.plots.append(p)
        if report in _SAVE_SIM_RESULTS and s in _SAVE_SIM_RESULTS[report]:
            for d in _SAVE_SIM_RESULTS[report][s]:
                idx, pos, label = d
                for i in range(len(p.points[0])):
                    if pos < p.points[0][i]:
                        summary["values"][label] = p.points[idx][i]
                        break
        _SIM_DATA.lib_file_write(
            _SIM_DATA.lib_file_from_parts(report, m, s, "png"),
            run_dir.join(_png_filename(s)),
        )
    for s in STATEPOINTS:
        _SIM_DATA.lib_file_write(
            _SIM_DATA.lib_file_from_parts(report, m, s, "hdf5"),
            run_dir.join(f"{s}.hdf5"),
        )
    _SIM_DATA.lib_file_write(
        _SIM_DATA.summary_file_from_parts(report, m),
        pykern.pkjson.dump_str(summary),
    )
