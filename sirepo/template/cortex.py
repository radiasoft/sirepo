"""cortex execution template.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import component_def
import csv
import io
import material_def
import math
import numpy
import os
import pykern.pkcompat
import pykern.pkio
import pykern.pkjson
import re
import sirepo.mpi
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.template.openmc
import tea_api

CORTEX_RUN_LOG = "cortex.log"
STATEPOINTS = ["neutronics", "depletion"]
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_CHAIN_ENDF_FILE = "chain_endf_b8.0.xml"
_EUDEMO_H5M_FILE = "eudemo_f_1_27a.h5m"
_SLAB_CHAIN_ENDF_FILE = "chain_endfb80_sfr.xml"
_TOKAMAK_INPUTS_FILE = "Tokamak_inputs.json"
_REPORT_TITLE = PKDict(
    slabAnimation=PKDict(
        dpa_OB_1_b6="DPA",
        h1_OB_1_b6="Hydrogen",
        he_OB_1_b6="Helium",
        flux_total_OB_1_b6="Flux",
        heating_OB_1_b6="Heating",
        p_flux_spectrum_OB_1_b6="Photon Flux",
        n_flux_spectrum_OB_1_b6="Neutron Flux",
        sdr_layer_00_Armor_OB_1_b6="Armor SDR",
        sdr_layer_01_First_Wall_OB_1_b6="First wall SDR",
        sdr_layer_12_VV_OB_1_b6="Vacuum Vessel SDR",
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
        activity_cell_VV="Activity - Vacuum Vessel",
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
        decayheat_VV="Decay heat - Vacuum Vessel",
        radial_activity_profiles="Radial profile of Total activity per cooling time",
        radial_decayheat_profiles="Radial profile of decay heat per cooling time",
        sdr_profile_OB_1_b6="D1S spatial profile",
        sdr_time_layers_OB_1_b6="D1S SDR per OB layer",
    ),
)

SIM_VERSION = PKDict(
    hcllSlabAnimation="1.02",
    hcpbSlabAnimation="1.02",
    wcllSlabAnimation="1.02",
)

_SIM_OUTPUT = PKDict(
    slabAnimation=list(_REPORT_TITLE.slabAnimation.keys()),
)

_SIM_TIME = PKDict(
    slabAnimation=679,
)
_LOG_TIME = PKDict(
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

# ------------------------------------------------------------------
# tea manufacturing cost model (stateless_compute_calculate_cost)
#
# categorical cost levels (tooling/equipment/time) for each process, from
# tea's processes_database/*.py - transcribed here since the pip-installed
# tea package doesn't ship its processes_database/geometries_database data
# directories, only the core py-modules (tea_api resolves a Process/Geometry
# straight from these values via build_process()/build_geometry(), no
# on-disk database lookup needed).
_COST_PROCESS_LEVELS = PKDict(
    {
        "CNC": PKDict(
            tooling_level="Low", equipment_level="Low-Medium", time_level="Medium-High"
        ),
        "Cold Rolling": PKDict(
            tooling_level="Medium", equipment_level="High-Very High", time_level="Low"
        ),
        "Diffusion Bonding": PKDict(
            tooling_level="Low-Medium",
            equipment_level="Low-Medium",
            time_level="Medium",
        ),
        "Electron Beam": PKDict(
            tooling_level="Medium", equipment_level="Medium", time_level="Medium"
        ),
        "HIP": PKDict(
            tooling_level="Low-Medium", equipment_level="High", time_level="Medium"
        ),
        "Hot Rolling": PKDict(
            tooling_level="Medium", equipment_level="High-Very High", time_level="Low"
        ),
        "Spray Deposition": PKDict(
            tooling_level="Low-Medium", equipment_level="High", time_level="Medium"
        ),
    }
)

#: relative cost coefficients (Cc/Cs/Ct/Cf) for every process, given to both
#: fixed geometries below - 1.0 (ideal/no penalty) for all of them, same
#: placeholder convention tea's own "Plasma Facing Surface" geometry uses,
#: since there's no DFM curve data for these processes at any thickness
_COST_UNIT_COEFF_MAP = PKDict((n, 1.0) for n in _COST_PROCESS_LEVELS)

# HCPB layer thicknesses (EUDEMO_HCPB_inputs.json: armor_cm=3.2, fw_cm=3.0),
# so the plasma-facing (armor) layer is 3.2-3.0=0.2cm=2mm - exactly tea's
# existing "Plasma Facing Surface" geometry - and the first wall layer is
# 3.0cm=30mm. Volume scales with thickness at the same implied panel area
# as "Plasma Facing Surface" (3,000,000mm^3 / 2mm = 1.5 m^2).
_COST_GEOMETRY_ARMOR = PKDict(
    name="Plasma Facing Surface",
    volume_mm3=3_000_000,
    section_thickness_mm=2,
    shape_class="C1",
    tolerance_mm=0.1,
    surface_finish_um_ra=1,
)
_COST_GEOMETRY_FIRST_WALL = PKDict(
    name="First Wall",
    volume_mm3=45_000_000,
    section_thickness_mm=30,
    shape_class="C1",
    tolerance_mm=0.1,
    surface_finish_um_ra=1,
)

COST_PROCESS_NAMES = tuple(_COST_PROCESS_LEVELS.keys())


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
            simulationSettings=sirepo.simulation_db.read_json(
                run_dir.join(template_common.INPUT_BASE_NAME)
            ).models.simulationSettings,
        )
    return PKDict(
        frameCount=0,
        percentComplete=_percent_complete(),
    )


def stateless_compute_calculate_cost(data, **kwargs):
    """Run the tea manufacturing cost model for a cortex material.

    The heavy part of the CORTEX Cost tab's calculation (building the tea
    Material/Geometry, tea_api.evaluate(), matplotlib chart rendering) -
    dispatched here via statelessCompute so it runs off the api server's
    single-threaded cortexDb action loop. This function can't query the
    cortex database itself (it may run on a different server than the api
    server), so data.args carries a plain material spec built by
    sirepo.sim_api.cortex.tea_cost.material_spec() instead.

    Args:
        data (PKDict): data.args has material (name/density/composition/
            remainder_element), is_plasma_facing, processes (list of
            COST_PROCESS_NAMES), production_qty
    Returns:
        PKDict: summary, material_composition, warnings, chart_png (list
            of bytes), source_code
    """
    try:
        m = _cost_material(data.args.material)
    except tea_api.TeaError as e:
        return PKDict(error=str(e))
    g = _cost_geometry(data.args.is_plasma_facing)
    p = [
        PKDict(name=n, Cmp=1.0, **_COST_PROCESS_LEVELS[n]) for n in data.args.processes
    ]
    r = PKDict(
        tea_api.evaluate(
            material=m,
            processes=p,
            volume_mm3=g.volume_mm3,
            production_qty=data.args.production_qty,
            geometry=g,
            component_name=m.name,
        )
    )
    return r.pkupdate(
        warnings=[_cost_humanize_warning(w) for w in r.warnings],
        chart_png=list(_cost_render_chart(r.summary, r.material_composition)),
        source_code=_cost_source_code(m, g, p, data.args.production_qty),
    )


def plotdef_to_sim_frame(plotdef):

    def _section(stat):
        if "_flux" in stat:
            return "flux"
        if "activity" in stat or "decayheat" in stat or "sdr_layer" in stat:
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
    if plotdef.stat == "flux" or plotdef.stat == "sdr":
        res.alignLegend = "right"
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
    t = re.search(r"(\w+)SlabAnimation", data.report).group(1).upper()
    for n in (
        f"EUDEMO_{t}_inputs.json",
        f"{t}_surface_source.h5",
        f"{t}_armor_current_neutron.json",
    ):
        sirepo.template.openmc.remote_datafile_path(n, compress=False)
    pykern.pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        template_common.render_jinja(
            SIM_TYPE,
            template_common.flatten_data(data.models, PKDict()).pkupdate(
                materialDefinition=_generate_material_definition(data),
                materialDirectory=sirepo.sim_run.cache_dir(
                    sirepo.template.openmc.OPENMC_CACHE_DIR
                ),
                mpiCores=sirepo.mpi.cfg().cores,
                chainPath=sirepo.template.openmc.remote_datafile_path(
                    _SLAB_CHAIN_ENDF_FILE
                ),
                dagmcPath=sirepo.template.openmc.remote_datafile_path(
                    f"eudemo_{t.lower()}.h5m", compress=False
                ).dirname,
                slabType=t,
            ),
            "slab.py",
        ),
    )
    return None


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
                r.append(plot[dim][i])
                r.append(plot[dim][i])
        return r

    with open(str(run_dir.join(_json_filename(stat))), "r") as f:
        d = pykern.pkjson.load_any(f)

    single = len(d.plots) == 1
    # TODO(pjm): assert x points match across plots
    points = [_process_points(d.plots[0], "x")]
    legend = [""]
    for p in d.plots:
        points.append(_process_points(p, "y"))
        legend.append(p.label or d.ylabel)
    for p in d.plots:
        if "lo" not in p:
            continue
        n = "" if single else f"{p.label or d.ylabel}_"
        points.append(_process_points(p, "lo"))
        legend.append(f"{n}low")
        points.append(_process_points(p, "hi"))
        legend.append(f"{n}high")
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
    def _csv_from_plot(plot):
        v = io.StringIO()
        w = csv.writer(v)
        w.writerow([plot.xlabel] + plot.legend[1:])
        for i in range(len(plot.points[0])):
            w.writerow([plot.points[j][i] for j in range(len(plot.points))])
        return v.getvalue()

    def _material_id_from_run_dir():
        return int(
            sirepo.simulation_db.read_json(
                run_dir.join(template_common.INPUT_BASE_NAME)
            ).models.material.material_id
        )

    def _summary_from_csv():
        def _value(v):
            try:
                return float(v)
            except ValueError:
                return v

        m = re.search(r"(\w+)SlabAnimation", report)
        if not m:
            return []
        p = run_dir.join(
            "slab",
            m.group(1).upper(),
            "neutronics_results",
            "OB_1_b6",
            "summary_results.csv",
        )
        if not p.exists():
            return []
        with pykern.pkio.open_text(p) as f:
            return [
                PKDict({k: _value(v) for k, v in row.items()})
                for row in csv.DictReader(f)
            ]

    m = _material_id_from_run_dir()
    summary = PKDict(
        material_id=m,
        model=report,
        version=SIM_VERSION[report],
        completed=pykern.pkcompat.utcnow(),
        plots=[],
        values=_summary_from_csv(),
    )
    for s in stats:
        p = _plot_from_file(run_dir, m, report, s)
        p.csv = _csv_from_plot(p)
        summary.plots.append(p)
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


# ------------------------------------------------------------------
# tea manufacturing cost model private helpers (stateless_compute_calculate_cost)


def _cost_geometry(is_plasma_facing):
    g = _COST_GEOMETRY_ARMOR if is_plasma_facing else _COST_GEOMETRY_FIRST_WALL
    return component_def.build_geometry(
        Cc_map=_COST_UNIT_COEFF_MAP,
        Cs_map=_COST_UNIT_COEFF_MAP,
        Ct_map=_COST_UNIT_COEFF_MAP,
        Cf_map=_COST_UNIT_COEFF_MAP,
        verbose=False,
        **g,
    )


def _cost_humanize_warning(warning):
    """tea_api.material_cost_breakdown() formats a missing-element warning
    with a raw python list repr and a quoted material name, e.g.
    "...elements ['H', 'Na'] in 'Zeolite'."; replace it with a plain
    comma-separated list and an unquoted material name, e.g. "...elements
    H, Na of Zeolite."."""

    def _to_list(m):
        return ", ".join(re.findall(r"'([^']*)'", m.group(0)))

    warning = re.sub(r"\[(?:'[^']*'(?:, )?)+\]", _to_list, warning)
    return re.sub(r"in '([^']*)'", r"of \1", warning)


def _cost_material(material_spec):
    """Build a tea Material from the plain material_spec dict (see
    sirepo.sim_api.cortex.tea_cost.material_spec()) - build_material()
    directly rather than tea_api.resolve_material(): a single-element
    material (e.g. pure Tungsten) has nothing left in composition once the
    remainder element is excluded, and resolve_material's dict-spec branch
    rejects an empty composition even though build_material() itself
    handles it fine (the remainder element alone balances to 100%)."""
    material, captured = tea_api._captured_call(
        material_def.build_material,
        name=material_spec.name,
        density=material_spec.density,
        composition=material_spec.composition,
        remainder_element=material_spec.remainder_element,
        Cmp_map={},
    )
    if material is None:
        raise tea_api.TeaError(
            tea_api._extract_error(
                captured, f"Failed to build material '{material_spec.name}'."
            )
        )
    return material


def _cost_render_chart(summary, material_fraction_rows):
    """Stacked bar of Material + each process's cost, with a "zoom" panel
    showing the Material segment's cost broken down by element.

    Copied (not imported) from tea/webapp/server.py's render_cost_chart():
    that function isn't reachable from the pip-installed `tea` package -
    only tea's core py-modules (component_def, cost_variables,
    material_def, process_def, tea1, tea_api) are packaged, tea/webapp/ is
    not, and matplotlib is only in tea's optional [webapp] extra rather
    than a core dependency. If tea ever packages this function, this copy
    should be replaced with a direct call to it."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    from matplotlib.patches import ConnectionPatch

    ink_primary = "#0b0b0b"
    ink_secondary = "#52514e"
    ink_muted = "#898781"
    gridline = "#e1e0d9"
    baseline = "#c3c2b7"
    surface = "#fcfcfb"
    categorical_palette = [
        "#2a78d6",
        "#eb6834",
        "#1baf7a",
        "#eda100",
        "#e87ba4",
        "#008300",
        "#4a3aa7",
        "#e34948",
    ]
    other_color = ink_muted
    blue_ramp = [
        "#2a78d6",
        "#5598e7",
        "#6da7ec",
        "#86b6ef",
        "#9ec5f4",
        "#b7d3f6",
        "#cde2fb",
    ]

    def _label_ink(hex_color):
        r, g, b = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return "#ffffff" if luminance < 140 else ink_primary

    def _draw_stacked_segments(ax, labels, values, colors, bar_width, value_fmt):
        bottom = 0.0
        texts, bottoms = [], []
        for label, value, color in zip(labels, values, colors):
            ax.bar(
                0,
                value,
                width=bar_width,
                bottom=bottom,
                color=color,
                edgecolor="none",
                linewidth=0,
                zorder=3,
                label=label,
            )
            text = ax.text(
                0,
                bottom + value / 2,
                value_fmt(label, value),
                ha="center",
                va="center",
                fontsize=9,
                color=_label_ink(color),
                zorder=4,
            )
            texts.append(text)
            bottoms.append(bottom)
            bottom += value
        return texts, bottoms

    def _drop_oversized_labels(fig, ax, bar_width, texts, values):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bar_left_px = ax.transData.transform((-bar_width / 2, 0))[0]
        bar_right_px = ax.transData.transform((bar_width / 2, 0))[0]
        available_width_px = (bar_right_px - bar_left_px) - 8
        for text, value in zip(texts, values):
            segment_height_px = (
                ax.transData.transform((0, value))[1]
                - ax.transData.transform((0, 0))[1]
            )
            bbox = text.get_window_extent(renderer=renderer)
            if bbox.width > available_width_px or bbox.height > segment_height_px - 4:
                text.remove()

    def _style_stacked_axis(ax, ylabel, value_fmt):
        ax.set_ylabel(ylabel, color=ink_secondary, fontsize=10)
        ax.set_xlim(-1.0, 1.0)
        ax.set_xticks([])
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: value_fmt(v)))
        ax.tick_params(axis="y", colors=ink_muted, labelsize=9)
        ax.yaxis.grid(True, color=gridline, linewidth=1, zorder=0)
        ax.set_axisbelow(True)
        for spine_name in ("top", "right", "left", "bottom"):
            ax.spines[spine_name].set_visible(False)

    labels = ["Material"] + [p["Process"] for p in summary["Processes"]]
    values = [summary["Cost Breakdown"][label] for label in labels]
    colors = [
        categorical_palette[i] if i < len(categorical_palette) else other_color
        for i in range(len(labels))
    ]

    visible = [r for r in material_fraction_rows if r["fraction"] > 0]
    element_labels = [r["element"] for r in visible]
    element_values = [r["fraction"] * 100 for r in visible]
    element_colors = [
        blue_ramp[i] if i < len(blue_ramp) else other_color
        for i in range(len(element_labels))
    ]

    bar_width = 1.2
    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(8.6, 5.4), dpi=150, gridspec_kw={"width_ratios": [1.3, 1]}
    )
    fig.patch.set_facecolor(surface)
    ax1.set_facecolor(surface)
    ax2.set_facecolor(surface)

    texts1, bottoms1 = _draw_stacked_segments(
        ax1, labels, values, colors, bar_width, value_fmt=lambda label, v: f"${v:,.2f}"
    )
    material_bottom, material_top = bottoms1[0], bottoms1[0] + values[0]

    texts2, bottoms2 = _draw_stacked_segments(
        ax2,
        element_labels,
        element_values,
        element_colors,
        bar_width,
        value_fmt=lambda label, v: f"{v:.1f}% {label}",
    )
    zoom_top = (bottoms2[-1] + element_values[-1]) if element_values else 0.0

    _style_stacked_axis(ax1, "Cost ($)", lambda v: f"${v:,.0f}")
    _style_stacked_axis(ax2, "Share of material cost (%)", lambda v: f"{v:.0f}%")

    for y1, y2 in ((material_top, zoom_top), (material_bottom, 0.0)):
        con = ConnectionPatch(
            xyA=(bar_width / 2, y1),
            coordsA=ax1.transData,
            xyB=(-bar_width / 2, y2),
            coordsB=ax2.transData,
            color=baseline,
            linewidth=1,
            linestyle="--",
            zorder=1,
        )
        fig.add_artist(con)

    legend1 = ax1.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.07),
        frameon=False,
        ncol=2,
        fontsize=8,
        labelcolor=ink_secondary,
        handlelength=1.2,
        handleheight=1.2,
    )
    legend2 = ax2.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.07),
        frameon=False,
        ncol=2,
        fontsize=8,
        labelcolor=ink_secondary,
        handlelength=1.2,
        handleheight=1.2,
    )

    fig.tight_layout()

    _drop_oversized_labels(fig, ax1, bar_width, texts1, values)
    _drop_oversized_labels(fig, ax2, bar_width, texts2, element_values)

    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        facecolor=fig.get_facecolor(),
        bbox_extra_artists=(legend1, legend2),
        bbox_inches="tight",
    )
    plt.close(fig)

    return buf.getvalue()


def _cost_source_code(material, geometry, process_specs, production_qty):
    """A standalone python script that reproduces this calculation with
    only the pip-installed `tea` package (no sirepo) - same calls
    stateless_compute_calculate_cost() itself makes, so running it gives
    identical results. Rendered from cost_source.py.jinja.

    String values are pre-formatted with repr() so the template gets a
    correctly quoted/escaped python literal (jinja's default {{ }}
    stringification would emit them unquoted, which isn't valid python);
    numeric values are passed through as-is, since str() and repr() are
    identical for int/float. composition/coefficient maps/process_specs
    are pre-formatted with _cost_pretty() for consistent indentation."""

    def _cost_pretty(value):
        """Format value (a dict or list of dicts) as an indented, always
        consistently-aligned python literal - pkjson.dump_pretty() nests
        every level at a fixed indent regardless of content size or where
        the result is embedded, unlike pprint's width-based line wrapping
        (whose continuation lines don't line up with this f-string
        template's own 4-space argument indentation). Double-quoted JSON
        strings are valid python syntax, so the result can be pasted
        directly into a script."""
        return pykern.pkjson.dump_pretty(value).rstrip().replace("\n", "\n    ")

    c = PKDict(
        (e, PKDict(wt=v["wt"], type=v["type"]))
        for e, v in material.composition.items()
        if v["type"] != "rem"
    )
    r = next(e for e, v in material.composition.items() if v["type"] == "rem")
    return template_common.render_jinja(
        SIM_TYPE,
        PKDict(
            material_name_text=material.name,
            material_name=repr(material.name),
            material_density=material.density,
            composition=_cost_pretty(c),
            remainder_element=repr(r),
            geometry_name=repr(geometry.name),
            geometry_volume_mm3=geometry.volume_mm3,
            geometry_section_thickness_mm=geometry.section_thickness_mm,
            geometry_shape_class=repr(geometry.shape_class),
            geometry_tolerance_mm=geometry.tolerance_mm,
            geometry_surface_finish_um_ra=geometry.surface_finish_um_ra,
            cc_map=_cost_pretty(geometry.Cc_map),
            cs_map=_cost_pretty(geometry.Cs_map),
            ct_map=_cost_pretty(geometry.Ct_map),
            cf_map=_cost_pretty(geometry.Cf_map),
            process_specs=_cost_pretty([PKDict(p) for p in process_specs]),
            production_qty=production_qty,
        ),
        name="cost_source.py",
    )
