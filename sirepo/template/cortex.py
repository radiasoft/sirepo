"""cortex execution template.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import cortex_tea.component_def
import cortex_tea.material_def
import cortex_tea.plotting
import cortex_tea.tea_api
import csv
import heapq
import io
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
import sirepo.util
import zipfile

CORTEX_RUN_LOG = "cortex.log"
STATEPOINTS = ["neutronics", "depletion"]
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_CHAIN_ENDF_FILE = "chain_endf_b8.0.xml"
_EUDEMO_H5M_FILE = "eudemo_f_1_27a.h5m"
_SLAB_CHAIN_ENDF_FILE = "chain_endfb80_sfr.xml"
_TOKAMAK_INPUTS_FILE = "Tokamak_inputs.json"
_COOLING_TIME = "cooling time (time after irradiation)"

_NUCLIDE_LEGEND = "The legend gives each nuclide and its half-life."

# POSIT: slab.py.jinja _y_to_s_milestones
_SECONDS_PER_YEAR = 365 * 24 * 3600

#: cooling times (seconds after shutdown) a pathway analysis may be of, some of
#: slab.py.jinja DEPLETION_MILESTONE_SECONDS_TO_PLOT
# POSIT: VPathwayAnalysis.vue COOLING_TIMES
_PATHWAY_COOLING_SECONDS = frozenset(
    (
        86_400,
        7 * 86_400,
        _SECONDS_PER_YEAR // 12,
        _SECONDS_PER_YEAR,
        10 * _SECONDS_PER_YEAR,
        100 * _SECONDS_PER_YEAR,
        1_000 * _SECONDS_PER_YEAR,
    )
)

#: cooling times (seconds after shutdown) of the impurity comparison's class table
_IMPURITY_COOLING_SECONDS = (
    86_400,
    _SECONDS_PER_YEAR,
    10 * _SECONDS_PER_YEAR,
    100 * _SECONDS_PER_YEAR,
    1_000 * _SECONDS_PER_YEAR,
)

#: waste summary csv columns for NRC 10 CFR 61.55 Table 1 and Table 2 Class A,
#: B and C, and Fetter; POSIT: slab.py.jinja waste summary csv headers
_NRC_TABLE1 = "NRC Table 1 (long-lived)"
_NRC_TABLE2 = (
    "NRC Table 2 Class A",
    "NRC Table 2 Class B",
    "NRC Table 2 Class C",
)

_FETTER = "Fetter et al. (1990)"

#: waste summary columns drawn by the impurity comparison, with their legend
_IMPURITY_LIMITS = PKDict(
    {
        _NRC_TABLE1: "NRC Table 1",
        _NRC_TABLE2[0]: "NRC Class A",
        _NRC_TABLE2[1]: "NRC Class B",
        _NRC_TABLE2[2]: "NRC Class C",
        _FETTER: "Fetter",
    }
)

#: material layers: title, waste summary file name, the layer's column in the
#: decay heat and shutdown dose csvs, and whether its waste ratings are also
#: structure scaled (Armor is all structure, so they're the same)
# POSIT: slab.py.jinja file names and csv headers
_IMPURITY_LAYERS = PKDict(
    Armor=PKDict(
        decay_heat="Armor",
        shutdown_dose="Armor",
        struct_scaled=False,
        title="Armor",
        waste="Armor",
    ),
    First_Wall=PKDict(
        decay_heat="First wall",
        shutdown_dose="First Wall",
        struct_scaled=True,
        title="First Wall",
        waste="First_wall",
    ),
)

#: impurity comparison plots, in the order shown
# POSIT: VImpurities.vue CLASS_TITLES for the is_waste ones
_IMPURITY_PLOTS = PKDict(
    waste=PKDict(
        is_waste=True,
        title="Waste disposal rating",
        ylabel="Waste disposal rating",
    ),
    waste_struct_scaled=PKDict(
        is_waste=True,
        title="Waste disposal rating, structure scaled",
        ylabel="Waste disposal rating",
    ),
    shutdown_dose=PKDict(
        is_waste=False,
        title="Shutdown dose rate",
        ylabel="Shutdown dose rate [μSv/h]",
    ),
    decay_heat=PKDict(
        is_waste=False,
        title="Decay heat",
        ylabel="Decay heat [W/cm³]",
    ),
)

#: times marked on the impurity comparison plots: seconds after shutdown, label
# POSIT: slab.py.jinja DEPLETION_MILESTONE_SECONDS_TO_PLOT and its plots' refs
_IMPURITY_MILESTONES = (
    (1, "1 s"),
    (60, "1 m"),
    (3_600, "1 h"),
    (86_400, "1 d"),
    (7 * 86_400, "1 w"),
    (_SECONDS_PER_YEAR / 12, "1 mo"),
    (_SECONDS_PER_YEAR, "1 y"),
    (10 * _SECONDS_PER_YEAR, "10 y"),
    (100 * _SECONDS_PER_YEAR, "100 y"),
    (1_000 * _SECONDS_PER_YEAR, "1000 y"),
)

#: impurity comparison ratios aren't drawn where both runs are below this
#: fraction of the curve's peak
_IMPURITY_PEAK_FRACTION = 1e-9

#: impurity comparison ratios of waste ratings aren't drawn where both runs
#: are below this (1% of a limit), since they can't change the class
_IMPURITY_WASTE_MIN = 0.01

#: rows listed by pathway analysis, the rest are summed into "Other"
_PATHWAY_MAX_ROWS = 15

#: openmc_pathway_analysis attribute_material_metric_origins metrics
# POSIT: VPathwayAnalysis.vue METRICS
_PATHWAY_METRICS = frozenset(
    ("activity", "contact_dose", "decay_heat", "waste_disposal_rating")
)

#: openmc nuclide name, e.g. Co60 or Ag108_m1
_PATHWAY_NUCLIDE_RE = re.compile(r"^[A-Z][a-z]?\d{1,3}(?:_m\d)?$")

#: loaded pathway inputs, kept by the agent's analysis process between requests
_pathway = PKDict(stamp=None)

# Section and description of each report, the first pattern matching a stat
# wins so a specific pattern must precede the general one it overlaps. A None
# section is for a report which is only in the output zip, not listed in the UI.
# POSIT: the sections are the keys of VNeutronics.vue's sections, and the
# patterns are the stats in _REPORT_TITLE
_REPORT_GROUP = (
    (r"(cell|decayheat|waste_summary)_(OB|Breeder)", None, ""),
    (r"sdr_(profile|time)", None, ""),
    (r"^radial_", None, ""),
    (
        r"^dpa_",
        "steady_state",
        "Displacement damage in displacements per atom (DPA), from the Norgett-Robinson-Torrens (NRT) model, per full-power year (fpy) through the slab.",
    ),
    (
        r"^h1_",
        "steady_state",
        "Hydrogen gas production in atomic parts per million (appm) per full-power year through the slab.",
    ),
    (
        r"^he_",
        "steady_state",
        "Helium gas production in atomic parts per million (appm) per full-power year through the slab.",
    ),
    (
        r"^heating_",
        "steady_state",
        "Nuclear heating power density (W/cm³) through the slab.",
    ),
    (
        r"^flux_total_",
        "flux",
        "Total neutron and photon flux (1/cm²/s) through the slab.",
    ),
    (
        r"^n_flux_spectrum_",
        "flux",
        "Neutron flux per unit lethargy versus energy, one curve for each layer.",
    ),
    (
        r"^p_flux_spectrum_",
        "flux",
        "Photon flux per unit lethargy versus energy, one curve for each layer.",
    ),
    (
        r"^activity_all_cells$",
        "activity",
        f"Specific activity (Bq/kg) of each layer versus {_COOLING_TIME}.",
    ),
    (
        r"^activity_cell_",
        "activity",
        f"Specific activity (Bq/kg) of the layer by nuclide versus {_COOLING_TIME}. {_NUCLIDE_LEGEND}",
    ),
    (
        r"^decayheat_all_cells$",
        "decay_heat",
        f"Decay heat power density (W/cm³) of each layer versus {_COOLING_TIME}.",
    ),
    (
        r"^decayheat_",
        "decay_heat",
        f"Decay heat power density (W/cm³) of the layer by nuclide versus {_COOLING_TIME}. {_NUCLIDE_LEGEND}",
    ),
    (
        r"^sdr_layer_",
        "waste_dose",
        f"Shutdown dose rate (μSv/h) calculated with the Direct 1-Step (D1S) method versus {_COOLING_TIME}.",
    ),
    (
        r"^waste_summary_.*_struct_scaled$",
        "waste_dose",
        # POSIT: "struct. frac" is the plot title's title_suffix in
        # slab.py.jinja's _plot_waste_summary_one, see cortex_plot_test
        'Waste disposal ratings scaled up by dividing by the layer\'s structural volume fraction ("struct. frac" in the plot title). This approximates the structural material alone, without the coolant or breeder mixed into the layer. The NRC class shading is recomputed from the scaled ratings.',
    ),
    (
        r"^waste_summary_",
        "waste_dose",
        f"Waste disposal rating versus {_COOLING_TIME} for the U.S. Nuclear Regulatory Commission (NRC) limits in Title 10 of the Code of Federal Regulations (CFR) part 61.55 (Table 1 long-lived, Table 2 Class A, B and C) and for Fetter et al. A rating below 1 meets that limit. The shading shows the resulting NRC class.",
    ),
)

# POSIT: each slabAnimation key is the basename of a <key>.png and <key>.png.json
# written by the cortex repo's full_model_bluemira post-processing (e.g.
# waste_summary_<layer> from depletion_post.py, with spaces in the layer name
# replaced by "_") and moved to the run dir by the FLATTEN OUTPUT step in
# slab_src_patches/depletion_post.py.patch. _save_summary_to_database fails if
# any listed file is missing, so a renamed plot or layer there breaks every run.
_REPORT_TITLE = PKDict(
    slabAnimation=PKDict(
        dpa_OB_1_b6="Displacements per atom (DPA)",
        h1_OB_1_b6="Hydrogen",
        he_OB_1_b6="Helium",
        flux_total_OB_1_b6="Flux",
        heating_OB_1_b6="Heating",
        p_flux_spectrum_OB_1_b6="Photon Flux",
        n_flux_spectrum_OB_1_b6="Neutron Flux",
        sdr_layer_00_Armor_OB_1_b6="Shutdown dose rate - Armor",
        sdr_layer_01_First_Wall_OB_1_b6="Shutdown dose rate - First Wall",
        sdr_layer_12_VV_OB_1_b6="Shutdown dose rate - Vacuum Vessel",
        activity_all_cells="Total Activity over cooling time",
        activity_cell_Armor="Activity - Armor",
        activity_cell_First_wall="Activity - First Wall",
        activity_cell_Breeder_layer_1="Activity - Breeder layer 1",
        activity_cell_Breeder_layer_2="Activity - Breeder layer 2",
        activity_cell_Breeder_layer_3="Activity - Breeder layer 3",
        activity_cell_Breeder_layer_4="Activity - Breeder layer 4",
        activity_cell_Breeder_layer_10="Activity - Breeder layer 10",
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
        decayheat_Breeder_layer_10="Decay heat - Breeder layer 10",
        decayheat_VV="Decay heat - Vacuum Vessel",
        radial_activity_profiles="Radial profile of Total activity per cooling time",
        radial_decayheat_profiles="Radial profile of decay heat per cooling time",
        waste_summary_Armor="Waste disposal rating - Armor",
        waste_summary_First_wall="Waste disposal rating - First Wall",
        waste_summary_Breeder_layer_1="Waste disposal rating - Breeder layer 1",
        waste_summary_Breeder_layer_2="Waste disposal rating - Breeder layer 2",
        waste_summary_Breeder_layer_3="Waste disposal rating - Breeder layer 3",
        waste_summary_Breeder_layer_4="Waste disposal rating - Breeder layer 4",
        waste_summary_Breeder_layer_5="Waste disposal rating - Breeder layer 5",
        waste_summary_Breeder_layer_6="Waste disposal rating - Breeder layer 6",
        waste_summary_Breeder_layer_7="Waste disposal rating - Breeder layer 7",
        waste_summary_Breeder_layer_8="Waste disposal rating - Breeder layer 8",
        waste_summary_Breeder_layer_9="Waste disposal rating - Breeder layer 9",
        waste_summary_Breeder_layer_10="Waste disposal rating - Breeder layer 10",
        waste_summary_VV="Waste disposal rating - Vacuum Vessel",
        waste_summary_Armor_struct_scaled="Waste disposal rating, structure scaled - Armor",
        waste_summary_First_wall_struct_scaled="Waste disposal rating, structure scaled - First Wall",
        waste_summary_Breeder_layer_1_struct_scaled="Waste disposal rating, structure scaled - Breeder layer 1",
        waste_summary_Breeder_layer_2_struct_scaled="Waste disposal rating, structure scaled - Breeder layer 2",
        waste_summary_Breeder_layer_3_struct_scaled="Waste disposal rating, structure scaled - Breeder layer 3",
        waste_summary_Breeder_layer_4_struct_scaled="Waste disposal rating, structure scaled - Breeder layer 4",
        waste_summary_Breeder_layer_5_struct_scaled="Waste disposal rating, structure scaled - Breeder layer 5",
        waste_summary_Breeder_layer_6_struct_scaled="Waste disposal rating, structure scaled - Breeder layer 6",
        waste_summary_Breeder_layer_7_struct_scaled="Waste disposal rating, structure scaled - Breeder layer 7",
        waste_summary_Breeder_layer_8_struct_scaled="Waste disposal rating, structure scaled - Breeder layer 8",
        waste_summary_Breeder_layer_9_struct_scaled="Waste disposal rating, structure scaled - Breeder layer 9",
        waste_summary_Breeder_layer_10_struct_scaled="Waste disposal rating, structure scaled - Breeder layer 10",
        waste_summary_VV_struct_scaled="Waste disposal rating, structure scaled - Vacuum Vessel",
        sdr_profile_OB_1_b6="D1S spatial profile",
        sdr_time_layers_OB_1_b6="D1S shutdown dose rate per OB layer",
    ),
)

#: reports run with the material's default composition, listed with the
#: materials and run by batch. The rest of `SIM_VERSION` are impurity reports.
# POSIT: reports.js REPORTS
NEUTRONICS_REPORTS = ("hcllSlabAnimation", "hcpbSlabAnimation", "wcllSlabAnimation")

#: every report, see `report_parts`
SIM_VERSION = PKDict(
    hcllSlabAnimation="1.03",
    hcllSlabMaxImpurityAnimation="1.03",
    hcllSlabMinImpurityAnimation="1.03",
    hcpbSlabAnimation="1.03",
    hcpbSlabMaxImpurityAnimation="1.03",
    hcpbSlabMinImpurityAnimation="1.03",
    wcllSlabAnimation="1.03",
    wcllSlabMaxImpurityAnimation="1.03",
    wcllSlabMinImpurityAnimation="1.03",
)

# POSIT: the keys of SIM_VERSION
_REPORT_RE = re.compile(r"^(hcll|hcpb|wcll)Slab(?:(Max|Min)Impurity)?Animation$")

_SIM_OUTPUT = PKDict(
    slabAnimation=list(_REPORT_TITLE.slabAnimation.keys()),
)

# Seconds of a hcpb run. WCLL has the same output, which is why the report
# type is shared, and is only approximated.
_SIM_TIME = PKDict(
    slabAnimation=451,
)

# Each marker is found in order in the log and the seconds are when it
# was output. The log has three openmc runs: neutronics, D1S, and depletion.
# POSIT: batches are counted in the log, and the markers are only for the
# first 5, which is slab.py.jinja BATCHES. A trigger can run more, and the
# extras don't match a marker, so the progress waits for the next marker.
# The times are from a run which took 451 seconds, see
# tests/template/cortex_plot_test.py::test_log_progress.
_LOG_TIME = PKDict(
    slabAnimation=[
        [v[0], v[1] / _SIM_TIME.slabAnimation]
        for v in (
            # neutronics
            ["Reading model XML file", 45],
            ["Simulating batch 1", 54],
            ["Simulating batch 2", 68],
            ["Simulating batch 3", 81],
            ["Simulating batch 4", 95],
            ["Simulating batch 5", 109],
            ["Creating state point", 122],
            # D1S
            ["Performing D1S run", 126],
            ["Reading model XML file", 132],
            ["Simulating batch 1", 140],
            ["Simulating batch 2", 155],
            ["Simulating batch 3", 170],
            ["Simulating batch 4", 185],
            ["Simulating batch 5", 200],
            ["Creating state point", 216],
            # depletion
            ["Reading model XML file", 230],
            ["Simulating batch 1", 238],
            ["Simulating batch 2", 264],
            ["Simulating batch 3", 289],
            ["Simulating batch 4", 315],
            ["Simulating batch 5", 340],
            ["Creating state point", 365],
            ["[openmc.deplete]", 366],
            ["[waste summary]", 403],
        )
    ],
)

# ------------------------------------------------------------------
# tea manufacturing cost model (stateless_compute_calculate_cost)
#
# categorical cost levels (tooling/equipment/time) for each process,
# transcribed from cortex_tea's database_processes/*.py (tea_api resolves a
# Process/Geometry straight from these values, no on-disk database lookup
# needed).
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


def csv_from_plot(plot):
    """Plot points and legend as csv text, the only stored copy of them

    Read back with `plot_from_csv`.

    Args:
        plot (PKDict): xlabel, legend and points (dimension 0: x, 1: y1, 2: y2 ...)
    Returns:
        str: header is xlabel followed by legend[1:], one column per dimension
    """
    v = io.StringIO()
    w = csv.writer(v)
    w.writerow([plot.xlabel] + plot.legend[1:])
    for i in range(len(plot.points[0])):
        w.writerow([plot.points[j][i] for j in range(len(plot.points))])
    return v.getvalue()


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
            COST_PROCESS_NAMES), cmp ({process: Cmp}, default 1.0),
            production_qty
    Returns:
        PKDict: summary, material_composition, warnings, chart_png and
            curve_png (list of bytes), source_code
    """

    def _processes(args):
        cmp = args.get("cmp") or PKDict()
        rv = []
        for n in args.processes:
            c = float(cmp.get(n, 1.0))
            if c <= 0:
                raise cortex_tea.tea_api.TeaError(
                    f"Compatibility factor for {n} must be greater than zero."
                )
            rv.append(PKDict(name=n, Cmp=c, **_COST_PROCESS_LEVELS[n]))
        return rv

    g = _cost_geometry(data.args.is_plasma_facing)
    try:
        m = _cost_material(data.args.material)
        a = PKDict(
            material=m,
            processes=_processes(data.args),
            volume_mm3=g.volume_mm3,
            production_qty=data.args.production_qty,
            geometry=g,
            component_name=m.name,
        )
    except cortex_tea.tea_api.TeaError as e:
        return PKDict(error=str(e))
    r = PKDict(cortex_tea.tea_api.evaluate(**a))
    c = cortex_tea.tea_api.make_component(**a)
    return r.pkupdate(
        warnings=[_cost_humanize_warning(w) for w in r.warnings],
        chart_png=list(cortex_tea.plotting.cost_breakdown_png(c)),
        curve_png=list(cortex_tea.plotting.process_cost_curves_png(c)),
        source_code=_cost_source_code(m, g, a.processes, data.args.production_qty),
    )


def stateless_compute_impurity_comparison(data, **kwargs):
    """Compare the material's layer with impurities at their max and at 0

    sim_api.cortex reads the csv files (`impurity_comparison_files`) stored by
    the max and min impurity runs and passes them here, so the plots are drawn
    off the api server.

    Args:
        data (PKDict): data.args has layer (key of `_IMPURITY_LAYERS`), max
            and min (PKDict csv text by key of `impurity_comparison_files`)
    Returns:
        PKDict: layer (title), classes (PKDict by waste key: list of PKDict
            coolingSeconds, max and min (PKDict nrcClass, fetterExceeds); the
            structure scaled ones only if they differ from the unscaled ones)
            and plots (list of PKDict name, title and png: list of bytes)
    """
    a = data.args
    l = _IMPURITY_LAYERS[a.layer]
    t = PKDict()
    for i in ("max", "min"):
        t[i] = PKDict({k: _impurity_table(v) for k, v in a[i].items()})
    if sorted(t.max) != sorted(t.min):
        raise AssertionError("max and min runs have different files")
    rv = PKDict(classes=PKDict(), layer=l.title, plots=[])
    for k, x in _IMPURITY_PLOTS.items():
        if k not in t.max:
            continue
        if not numpy.array_equal(t.max[k].years, t.min[k].years):
            raise AssertionError(f"{k} max and min runs have different times")
        if x.is_waste:
            rv.classes[k] = _impurity_classes(t.max[k], t.min[k])
            c = _IMPURITY_LIMITS
        else:
            c = PKDict({l[k]: None})
        rv.plots.append(
            PKDict(
                name=k,
                title=x.title,
                png=list(
                    _impurity_png(
                        t.max[k].years,
                        [
                            PKDict(
                                label=v,
                                max=t.max[k].columns[n],
                                min=t.min[k].columns[n],
                            )
                            for n, v in c.items()
                        ],
                        f"{x.title} - {l.title}",
                        x.ylabel,
                        is_waste=x.is_waste,
                    ),
                ),
            ),
        )
    if rv.classes.get("waste_struct_scaled") == rv.classes.get("waste"):
        # same table twice; the plot is still shown, its values differ
        rv.classes.pkdel("waste_struct_scaled")
    return rv


def stateless_compute_pathway_analysis(data, **kwargs):
    """Attribute a layer's metric after cooling to the layer's original components

    Runs openmc_pathway_analysis on the inputs that sim_api.cortex staged
    in the user's lib dir (see SimData.pathway_lib_file).

    Args:
        data (PKDict): data.args has layer (material name in the material map,
            e.g. First_Wall), metric (one of `_PATHWAY_METRICS`), by_element
            (bool, else by nuclide), cooling_seconds (one of
            `_PATHWAY_COOLING_SECONDS`), and stamp (identifies the staged inputs)
    Returns:
        PKDict: layer, metric, units, coolingSeconds (of the depletion step
            nearest cooling_seconds), total, wasteClass (of the layer at that
            step), rows (origins), radionuclides (final nuclides which carry
            the metric) and skipped (final nuclides which couldn't be traced).
            rows and radionuclides are name, value, percent; largest first.
    """
    a = data.args
    if a.metric not in _PATHWAY_METRICS:
        raise AssertionError(f"invalid metric={a.metric}")
    s = _pathway_step(a)
    r = s.pathways.attribute_material_metric_origins(
        material_id=s.material_id,
        metric=a.metric,
        end_step=s.step,
        aggregate_origins_by_element=bool(a.by_element),
    )
    return PKDict(
        coolingSeconds=s.cooling_seconds,
        layer=a.layer,
        metric=a.metric,
        radionuclides=_pathway_rows(r.target_value, r.total_value),
        rows=_pathway_rows(r.origin_value, r.total_value),
        skipped=sorted(r.skipped_targets),
        total=r.total_value,
        units=r.units,
        wasteClass=str(
            s.pathways.get_material(
                s.material_id, timestep_index=s.step
            ).waste_classification()
        ),
    )


def stateless_compute_pathway_nuclide(data, **kwargs):
    """Production pathway of a final nuclide of a layer after cooling

    Args:
        data (PKDict): data.args has layer, cooling_seconds and stamp (see
            `stateless_compute_pathway_analysis`), and nuclide (e.g. Mn53)
    Returns:
        PKDict: nuclide, origins (name, percent of the nuclide's atoms;
            largest first) and chain (name, channel: the reaction or decay
            which produced it, None for the first) from the largest origin
            along the path which carries the most atoms, or error
    """
    a = data.args
    if not _PATHWAY_NUCLIDE_RE.search(a.nuclide):
        raise AssertionError(f"invalid nuclide={a.nuclide}")
    s = _pathway_step(a)
    # same args as attribute_material_metric_origins, which is cached
    r = s.pathways.target_origins(
        material_id=s.material_id,
        target=a.nuclide,
        end_step=s.step,
    )
    if r.notes:
        return PKDict(error=" ".join(r.notes))
    o = _pathway_rows(
        PKDict(
            (u, float(d.get("fraction", 0)))
            for u, _, d in r.condensed_graph.edges(data=True)
        ),
        1.0,
    )
    return PKDict(
        chain=_pathway_chain(r.combined_graph, o[0].name, a.nuclide) if o else [],
        nuclide=a.nuclide,
        origins=o,
    )


def plot_from_csv(text):
    """Parse plot points and legend written by `csv_from_plot`

    Args:
        text (str): csv text
    Returns:
        PKDict: legend and points (dimension 0: x, 1: y1, 2: y2 ...)
    """
    c = list(csv.reader(io.StringIO(text)))
    return PKDict(
        # POSIT: the x legend is always empty, see _plot_from_file
        legend=[""] + c[0][1:],
        points=[[float(r[i]) for r in c[1:]] for i in range(len(c[0]))],
    )


def plotdef_to_sim_frame(plotdef):
    g = _report_group(plotdef.stat)
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
            section=g.section,
            description=g.description,
        ),
    )
    res.y_range = template_common.compute_plot_color_and_range(res.plots)
    if plotdef.stat == "flux" or plotdef.stat == "sdr":
        res.alignLegend = "right"
    return res


def report_is_listed(stat):
    """Whether a report is listed in the UI, otherwise it is only in the output zip

    Args:
        stat (str): plot name, e.g. dpa_OB_1_b6
    Returns:
        bool: True if the report has a section
    """
    return _report_group(stat).section is not None


def impurity_comparison_files(layer):
    """csv files of the impurity runs which the comparison uses

    Args:
        layer (str): key of `_IMPURITY_LAYERS`
    Returns:
        PKDict: basename (in material_db.cortexdb_path) by key of
            `_IMPURITY_PLOTS`
    """
    l = _IMPURITY_LAYERS[layer]
    rv = PKDict(
        decay_heat="decayheat_all_cells.csv",
        shutdown_dose="sdr_time_layers_OB_1_b6.csv",
        waste=f"waste_summary_{l.waste}.csv",
    )
    if l.struct_scaled:
        rv.waste_struct_scaled = f"waste_summary_{l.waste}_struct_scaled.csv"
    return rv


def impurity_report(report, impurity):
    """The impurity report of a neutronics report

    Args:
        report (str): one of `NEUTRONICS_REPORTS`, e.g. hcpbSlabAnimation
        impurity (str): max or min
    Returns:
        str: e.g. hcpbSlabMaxImpurityAnimation
    """
    if report not in NEUTRONICS_REPORTS:
        raise AssertionError(f"invalid report={report}")
    rv = report.replace(
        "SlabAnimation", f"Slab{impurity.capitalize()}ImpurityAnimation"
    )
    if rv not in SIM_VERSION:
        raise AssertionError(f"invalid impurity={impurity}")
    return rv


def report_parts(report):
    """The blanket and the impurity case of a report

    Args:
        report (str): one of `SIM_VERSION`, e.g. hcpbSlabMaxImpurityAnimation
    Returns:
        PKDict: blanket (e.g. HCPB, the slab type) and impurity (None for the
            material's default composition, else max or min)
    """
    if not (m := _REPORT_RE.search(report)):
        raise AssertionError(f"invalid report={report}")
    return PKDict(
        blanket=m.group(1).upper(),
        impurity=m.group(2).lower() if m.group(2) else None,
    )


def write_parameters(data, run_dir, is_parallel):
    pykern.pkio.write_text(
        "cortex_plot.py",
        template_common.render_jinja(SIM_TYPE, PKDict(), "cortex_plot.py"),
    )
    pykern.pkio.write_text(
        "cortex_materials.py",
        template_common.render_jinja(SIM_TYPE, PKDict(), "cortex_materials.py"),
    )
    t = report_parts(data.report).blanket
    # POSIT: slab_src_patches/inputs.py.patch also reads {t}_tbr_scaling.json
    # from dagmcPath. It isn't in the data repo yet, so it isn't fetched here
    # and the sim falls back to the local (unscaled) TBR. Add it to this list
    # once it's uploaded.
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
    for c in _impurity_components(m.components, report_parts(data.report).impurity):
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


def _impurity_classes(max_table, min_table):
    """NRC class of each run at `_IMPURITY_COOLING_SECONDS`

    Args:
        max_table (PKDict): waste summary of the max run, see `_impurity_table`
        min_table (PKDict): of the min run
    Returns:
        list: PKDict coolingSeconds, max and min (PKDict nrcClass and
            fetterExceeds: the Fetter rating is over 1, which the run's plots
            show next to the class)
    """
    rv = []
    for s in _IMPURITY_COOLING_SECONDS:
        i = int(numpy.argmin(numpy.abs(max_table.years - s / _SECONDS_PER_YEAR)))
        rv.append(
            PKDict(
                coolingSeconds=float(max_table.years[i] * _SECONDS_PER_YEAR),
                **{
                    k: PKDict(
                        fetterExceeds=bool(t.columns[_FETTER][i] > 1.0),
                        nrcClass=_nrc_class(t.columns, i),
                    )
                    for k, t in (("max", max_table), ("min", min_table))
                },
            ),
        )
    return rv


def _impurity_components(components, impurity):
    """The material's components for an impurity report

    An impurity is a component with a min of 0 and a max greater than 0. They
    are set to their max (impurity="max") or 0 ("min"), and the change goes to
    the largest component which isn't an impurity (the balance). Every other
    component keeps its percent.

    Args:
        components (list): sim materialComponent: percent, min_percent,
            max_percent (None if the component has no range)
        impurity (str): None (unchanged), max or min, see `report_parts`
    Returns:
        list: copies of the components
    """

    def _is_impurity(component):
        return (
            component.get("min_percent") == 0
            and (component.get("max_percent") or 0) > 0
        )

    rv = [PKDict(c) for c in components]
    if impurity is None:
        return rv
    b = [c for c in rv if not _is_impurity(c)]
    if not b:
        raise sirepo.util.UserAlert(
            "The material has only impurities, so the impurities can't be changed",
            "no balance component",
        )
    b = max(b, key=lambda c: c.percent)
    for c in rv:
        if _is_impurity(c):
            x = c.max_percent if impurity == "max" else 0.0
            b.percent -= x - c.percent
            c.percent = x
    if b.percent < 0:
        raise sirepo.util.UserAlert(
            f"{b.component} would be negative with the impurities at their maximum",
            "balance={} percent={}",
            b.component,
            b.percent,
        )
    return rv


def _impurity_png(years, series, title, ylabel, is_waste=False):
    """Values of both runs on top and their ratio below

    The ratio (max / no impurities) is on a log axis, so it shows both small
    and very large effects (linear if it spans less than a decade, where log
    and linear look alike). It isn't drawn where both runs are negligible:
    ratings below `_IMPURITY_WASTE_MIN` (they can't change the class), or
    other values below `_IMPURITY_PEAK_FRACTION` of the curve's peak.

    Args:
        years (numpy.array): time after irradiation
        series (list): PKDict label (None if only one), max and min (numpy
            arrays of each run)
        title (str): of the plot
        ylabel (str): of the top panel
        is_waste (bool): waste ratings: the rating = 1 limit and 0.1
            reference lines, and the `_IMPURITY_WASTE_MIN` cutoff
    Returns:
        bytes: png
    """
    import matplotlib.backends.backend_agg
    import matplotlib.figure
    import matplotlib.ticker

    def _positive(values):
        # not drawn on a log scale
        return numpy.where(values > 0, values, numpy.nan)

    def _ratio(m, n):
        x = numpy.fmax(m, n)
        t = (
            _IMPURITY_WASTE_MIN
            if is_waste
            else _IMPURITY_PEAK_FRACTION * numpy.nanmax(x)
        )
        return numpy.where(x > t, m / n, numpy.nan)

    # the size of most of the run's plots (about 2180 x 1170 pixels)
    f = matplotlib.figure.Figure(figsize=(11, 6), dpi=200)
    matplotlib.backends.backend_agg.FigureCanvasAgg(f)
    a, d = f.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    for i, x in enumerate(series):
        c = f"C{i}"
        m = _positive(x.max)
        n = _positive(x.min)
        l = f"{x.label}, " if x.label else ""
        a.plot(years, m, color=c, label=f"{l}max impurities")
        a.plot(years, n, color=c, linestyle="--", label=f"{l}no impurities")
        d.plot(years, _ratio(m, n), color=c, label=x.label)
    # as the run's plots: dashed lines on both panels, labeled on the top one
    for t, l in _IMPURITY_MILESTONES:
        for x in a, d:
            x.axvline(
                t / _SECONDS_PER_YEAR,
                color="gray",
                linestyle="--",
                linewidth=1,
                alpha=0.6,
            )
        a.text(
            t / _SECONDS_PER_YEAR,
            0.98,
            l,
            transform=a.get_xaxis_transform(),
            rotation=90,
            va="top",
            ha="right",
            fontsize=8,
            alpha=0.8,
        )
    if is_waste:
        # as slab.py.jinja _plot_waste_summary_one: the limit and a reference
        a.axhline(1.0, color="black", linestyle="--", linewidth=1)
        a.axhline(0.1, color="black", linestyle=":", linewidth=1)
    a.set_yscale("log")
    a.set_ylabel(ylabel)
    a.set_title(title)
    a.grid(True, alpha=0.3)
    a.legend(fontsize="x-small", ncol=2 if len(series) > 1 else 1)
    d.axhline(1, color="black", linewidth=0.8)
    d.set_xscale("log")
    d.set_yscale("log")
    y = d.get_ylim()
    if y[1] / y[0] < 10:
        # within a decade a log axis is nearly linear, and its ticks are
        # minor ones with too few digits to tell apart (e.g. ×1 ×1 ×1)
        d.set_yscale("linear")
        # the panel is short, the default would give two ticks. Steps of
        # 1, 2 or 5 times a power of ten need exactly that power's digits.
        d.yaxis.set_major_locator(
            matplotlib.ticker.MaxNLocator(nbins=5, steps=[1, 2, 5, 10]),
        )
        t = d.yaxis.get_major_locator().tick_values(*d.get_ylim())
        n = max(0, -math.floor(math.log10(t[1] - t[0]) + 1e-9))
        d.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda y, _: f"×{y:.{n}f}"),
        )
    else:
        d.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda y, _: f"×{y:g}"),
        )
        # unlabeled: they'd overlap
        d.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    d.set_xlabel("Time after irradiation [years]")
    d.set_ylabel("Max / no impurities")
    d.grid(True, which="both", alpha=0.3)
    f.tight_layout()
    b = io.BytesIO()
    f.savefig(b, format="png")
    return b.getvalue()


def _impurity_table(text):
    """Parse a plot csv written by a run

    Args:
        text (str): csv whose first column is the time after irradiation
            in years, e.g. waste_summary_<layer>.csv
    Returns:
        PKDict: years (numpy array) and columns (PKDict name to numpy array)
    """
    p = plot_from_csv(text)
    return PKDict(
        columns=PKDict((k, numpy.array(v)) for k, v in zip(p.legend[1:], p.points[1:])),
        years=numpy.array(p.points[0]),
    )


def _json_filename(stat):
    return f"{_png_filename(stat)}.json"


def _nrc_class(columns, index):
    """NRC 10 CFR 61.55 class from the ratings at a time

    POSIT: a port of slab.py.jinja _classify_from_ratios

    Args:
        columns (PKDict): waste summary columns, see `_impurity_table`
        index (int): row
    Returns:
        str: Class A, Class B, Class C or GTCC
    """

    def _table2(a, b, c):
        if a < 1.0:
            return "Class A"
        if b < 1.0:
            return "Class B"
        if c < 1.0:
            return "Class C"
        return "GTCC"

    t1 = float(columns[_NRC_TABLE1][index])
    t2 = [float(columns[k][index]) for k in _NRC_TABLE2]
    if t1 > 0.0 and any(x > 0.0 for x in t2):
        if t1 < 0.1:
            return _table2(*t2)
        if t1 < 1.0:
            return "Class C" if t2[2] < 1.0 else "GTCC"
        return "GTCC"
    if t1 > 0.0:
        if t1 < 0.1:
            return "Class A"
        return "Class C" if t1 < 1.0 else "GTCC"
    if any(x > 0.0 for x in t2):
        return _table2(*t2)
    return "Class A"


def _pathway_chain(graph, origin, nuclide):
    """Path from origin to nuclide which carries the most atoms

    The path whose smallest edge (atoms moved) is largest. Parallel edges
    (the same nuclides, different channels or steps) count as their largest.

    Args:
        graph (networkx.MultiDiGraph): target_origins combined_graph, edges
            have atoms and channel
        origin (str): initial nuclide
        nuclide (str): final nuclide
    Returns:
        list: PKDict name and channel (None for origin), empty if no path
    """
    if origin == nuclide:
        # in the material from the start
        return [PKDict(name=origin, channel=None)]
    # largest atoms and its channel by nuclide and its product
    e = PKDict()
    for u, v, d in graph.edges(data=True):
        n = float(d.get("atoms", 0))
        if n > e.setdefault(u, PKDict()).get(v, (-1.0, None))[0]:
            e[u][v] = (n, d.get("channel"))
    # widest path search: w is the largest smallest edge to reach a nuclide
    w = PKDict({origin: math.inf})
    prev = PKDict()
    q = [(-math.inf, origin)]
    while q:
        b, u = heapq.heappop(q)
        if u == nuclide:
            break
        for v, (n, c) in e.get(u, PKDict()).items():
            # -1 so a path is found even if edges carry no atoms
            if min(-b, n) > w.get(v, -1.0):
                w[v] = min(-b, n)
                prev[v] = (u, c)
                heapq.heappush(q, (-w[v], v))
    if nuclide not in prev:
        return []
    rv = []
    v = nuclide
    while v != origin:
        rv.insert(0, PKDict(name=v, channel=prev[v][1]))
        v = prev[v][0]
    return [PKDict(name=origin, channel=None)] + rv


def _pathway_cooling_step(results, cooling_seconds):
    """Depletion step nearest `cooling_seconds` after shutdown

    Shutdown is the step after the last one with a source.

    Args:
        results (openmc.deplete.Results): depletion results
        cooling_seconds (int): time after shutdown
    Returns:
        tuple: step index (int), seconds after shutdown of that step (float)
    """
    t = numpy.array(results.get_times(time_units="s"))
    s = numpy.nonzero([r.source_rate for r in results])[0]
    if not len(s) or s[-1] + 1 >= len(t):
        raise AssertionError("depletion results have no cooling steps")
    t = t - t[s[-1] + 1]
    rv = int(numpy.argmin(numpy.abs(t - cooling_seconds)))
    return rv, float(t[rv])


def _pathway_inputs(run_dir, report):
    """openmc-pathway-analysis inputs written by the run's depletion

    Args:
        run_dir (py.path): run directory
        report (str): one of `SIM_VERSION`
    Returns:
        list: py.path of each of `SimData.PATHWAY_FILES`, empty if any is missing
    """
    # POSIT: slab.py.jinja DEPLETION_RUN_DIR and R2S_ACTIVATION_DIR
    d = run_dir.join("slab", report_parts(report).blanket, "depletion_run")
    f = _SIM_DATA.PATHWAY_FILES
    rv = [
        d.join(f.chain),
        d.join("r2s", "activation", f.material_map),
        d.join("r2s", "activation", f.results),
    ]
    if all(p.exists() for p in rv):
        return rv
    pkdlog("missing pathway inputs run_dir={} report={}", run_dir, report)
    return []


def _pathway_load(stamp):
    """Load the staged pathway inputs, unless already loaded for `stamp`

    Loading takes several seconds, so the agent's analysis process keeps the
    last inputs it loaded in `_pathway`.

    Args:
        stamp (str): identifies the staged inputs, see sim_api.cortex
    Returns:
        PKDict: material_map (material name to depletion material id) and
            pathways (openmc_pathway_analysis.ActivationPathways)
    """
    import openmc_pathway_analysis

    if _pathway.stamp == stamp:
        return _pathway
    f = PKDict(
        {
            k: _SIM_DATA.lib_file_abspath(_SIM_DATA.pathway_lib_file(k))
            for k in _SIM_DATA.PATHWAY_FILES
        }
    )
    with pykern.pkio.open_text(f.material_map) as x:
        m = PKDict((r["material_name"], r["mat_id"]) for r in csv.DictReader(x))
    # invalidate in case loading fails
    _pathway.stamp = None
    _pathway.pkupdate(
        material_map=m,
        pathways=openmc_pathway_analysis.ActivationPathways(
            str(f.results), chain=str(f.chain)
        ),
        stamp=stamp,
    )
    return _pathway


def _pathway_rows(values, total):
    """Largest values as table rows, the rest summed into "Other"

    Args:
        values (dict): value by name
        total (float): of all the values, for percent
    Returns:
        list: PKDict name, percent, value; largest first, at most
            `_PATHWAY_MAX_ROWS` and "Other"
    """
    v = sorted(((k, float(x)) for k, x in values.items() if x > 0), key=lambda x: -x[1])
    rv = [PKDict(name=k, value=x) for k, x in v[:_PATHWAY_MAX_ROWS]]
    if len(v) > _PATHWAY_MAX_ROWS:
        rv.append(PKDict(name="Other", value=sum(x[1] for x in v[_PATHWAY_MAX_ROWS:])))
    for r in rv:
        r.percent = r.value / total * 100 if total > 0 else 0.0
    return rv


def _pathway_step(args):
    """Load the staged inputs and find the layer's material and the cooling step

    Args:
        args (PKDict): layer, cooling_seconds and stamp, see
            `stateless_compute_pathway_analysis`
    Returns:
        PKDict: pathways (ActivationPathways), material_id, step and
            cooling_seconds (of step)
    """
    if args.cooling_seconds not in _PATHWAY_COOLING_SECONDS:
        raise AssertionError(f"invalid cooling_seconds={args.cooling_seconds}")
    p = _pathway_load(args.stamp)
    if args.layer not in p.material_map:
        raise AssertionError(f"layer={args.layer} not in the material map")
    s, c = _pathway_cooling_step(p.pathways.depletion_results, args.cooling_seconds)
    return PKDict(
        cooling_seconds=c,
        material_id=p.material_map[args.layer],
        pathways=p.pathways,
        step=s,
    )


def _plot_from_file(plot_json, material_id, report, stat):
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

    single = len(plot_json.plots) == 1
    # TODO(pjm): assert x points match across plots
    points = [_process_points(plot_json.plots[0], "x")]
    # POSIT: the x legend is always empty, see plot_from_csv
    legend = [""]
    for p in plot_json.plots:
        points.append(_process_points(p, "y"))
        legend.append(p.label or plot_json.ylabel)
    for p in plot_json.plots:
        if "lo" not in p:
            continue
        n = "" if single else f"{p.label or plot_json.ylabel}_"
        points.append(_process_points(p, "lo"))
        legend.append(f"{n}low")
        points.append(_process_points(p, "hi"))
        legend.append(f"{n}high")
    return PKDict(
        material_id=material_id,
        title=_REPORT_TITLE[_report_type(report)][stat],
        xlabel=_label(plot_json.xlabel),
        ylabel=_label(plot_json.ylabel),
        plot_type=plot_json.type or "linear",
        model=report,
        stat=stat,
        legend=legend,
        points=points,
    )


def _png_filename(stat):
    return f"{stat}.png"


def _report_group(stat):
    for p, s, d in _REPORT_GROUP:
        if re.search(p, stat):
            return PKDict(section=s, description=d)
    raise AssertionError(f"no report group stat={stat}")


def _report_type(report):
    # validates report; every report is a slab
    report_parts(report)
    return "slabAnimation"


def _save_summary_to_database(run_dir, report, stats):
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

        p = run_dir.join(
            "slab",
            report_parts(report).blanket,
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
    # one file, so the database side never sees a partial result
    # POSIT: sim_api.cortex.check_for_sim_summary reads this zip and extracts
    # the entries as is, action_stat_image and load_output_zip read them
    z = run_dir.join("summary.zip")
    with zipfile.ZipFile(str(z), "w", zipfile.ZIP_DEFLATED) as f:
        for s in stats:
            d = pykern.pkjson.load_any(
                pykern.pkio.read_text(run_dir.join(_json_filename(s)))
            )
            if not d.plots:
                # POSIT: cortex_plot.pyplot.savefig writes figures with no lines,
                # e.g. the D1S "No positive SDR values" layer plot
                pkdlog("plot has no lines, not saved stat={} run_dir={}", s, run_dir)
                continue
            p = _plot_from_file(d, m, report, s)
            p.csv = csv_from_plot(p)
            summary.plots.append(p)
            f.write(str(run_dir.join(_png_filename(s))), f"{s}.png")
        for s in STATEPOINTS:
            f.write(str(run_dir.join(f"{s}.hdf5")), f"{s}.hdf5")
        for p in _pathway_inputs(run_dir, report):
            f.write(str(p), p.basename)
        f.writestr(_SIM_DATA.SUMMARY_JSON, pykern.pkjson.dump_str(summary))
    _SIM_DATA.lib_file_write(_SIM_DATA.summary_file_from_parts(report, m), z)


# ------------------------------------------------------------------
# tea manufacturing cost model private helpers (stateless_compute_calculate_cost)


def _cost_geometry(is_plasma_facing):
    g = _COST_GEOMETRY_ARMOR if is_plasma_facing else _COST_GEOMETRY_FIRST_WALL
    return cortex_tea.component_def.build_geometry(
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
    material, captured = cortex_tea.tea_api._captured_call(
        cortex_tea.material_def.build_material,
        name=material_spec.name,
        density=material_spec.density,
        composition=material_spec.composition,
        remainder_element=material_spec.remainder_element,
        Cmp_map={},
    )
    if material is None:
        raise cortex_tea.tea_api.TeaError(
            cortex_tea.tea_api._extract_error(
                captured, f"Failed to build material '{material_spec.name}'."
            )
        )
    return material


def _cost_source_code(material, geometry, process_specs, production_qty):
    """A standalone python script that reproduces this calculation with
    only the pip-installed `cortex_tea` package (no sirepo) - same calls
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
