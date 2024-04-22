"""Warp VND/WARP execution template.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp, pkdlog
from rswarp.cathode import sources
from rswarp.utilities.file_utils import readparticles
from scipy import constants
from sirepo import simulation_db
from sirepo.template import template_common
import h5py
import msgpack
import numpy as np
import os.path
import py.path
import re
import sirepo.sim_data
import sirepo.util
import sirepo.sim_run


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

COMPARISON_STEP_SIZE = 100
WANT_BROWSER_FRAME_CACHE = True
MPI_SUMMARY_FILE = "mpi-info.json"

_ALL_PARTICLES_FILE = "all-particles.npy"
_COMPARISON_FILE = "diags/fields/electric/data00{}.h5".format(COMPARISON_STEP_SIZE)
_CULL_PARTICLE_SLOPE = 1e-4
_DENSITY_FILE = "density.h5"
_EGUN_CURRENT_FILE = "egun-current.npy"
_EGUN_STATUS_FILE = "egun-status.txt"
_FIELD_ESTIMATE_FILE = "estimates.json"
_OPTIMIZER_OUTPUT_FILE = "opt.out"
_OPTIMIZER_RESULT_FILE = "opt.json"
_OPTIMIZER_STATUS_FILE = "opt-run.out"
_OPTIMIZE_PARAMETER_FILE = "parameters-optimize.py"
_OPT_RESULT_INDEX = 3
_PARTICLE_FILE = "particles.msgpack"
_PARTICLE_PERIOD = 100
_POTENTIAL_FILE = "potential.h5"
_STL_POLY_FILE = "polygons.h5"


def analysis_job_compute_simulation_steps(data, run_dir, **kwargs):
    f = run_dir.join(_FIELD_ESTIMATE_FILE)
    if f.exists():
        res = simulation_db.read_json(f)
        if res and "tof_expected" in res:
            return PKDict(
                timeOfFlight=res["tof_expected"],
                steps=res["steps_expected"],
                electronFraction=res["e_cross"] if "e_cross" in res else 0,
            )
    return PKDict()


def background_percent_complete(report, run_dir, is_running):
    if report == "optimizerAnimation":
        return _optimizer_percent_complete(run_dir, is_running)
    return _simulation_percent_complete(report, run_dir, is_running)


def sim_frame_currentAnimation(frame_args):
    return _extract_current(
        frame_args.sim_in,
        open_data_file(
            frame_args.run_dir, frame_args.frameReport, frame_args.frameIndex
        ),
    )


def sim_frame_egunCurrentAnimation(frame_args):
    return _extract_egun_current(
        frame_args.sim_in,
        frame_args.run_dir.join(_EGUN_CURRENT_FILE),
        frame_args.frameIndex,
    )


def sim_frame_fieldAnimation(frame_args):
    return _extract_field(
        frame_args.field,
        frame_args.sim_in,
        open_data_file(
            frame_args.run_dir, frame_args.frameReport, frame_args.frameIndex
        ),
        frame_args,
    )


def sim_frame_fieldCalcAnimation(frame_args):
    return generate_field_report(frame_args.sim_in, frame_args.run_dir, args=frame_args)


def sim_frame_fieldComparisonAnimation(frame_args):
    return generate_field_comparison_report(
        frame_args.sim_in,
        frame_args.run_dir,
        args=frame_args,
    )


def sim_frame_impactDensityAnimation(frame_args):
    return _extract_impact_density(frame_args.run_dir, frame_args.sim_in)


def sim_frame_optimizerAnimation(frame_args):
    return _extract_optimization_results(
        frame_args.run_dir, frame_args.sim_in, frame_args
    )


def sim_frame_particleAnimation(frame_args):
    return _extract_particle(
        frame_args.run_dir,
        frame_args.frameReport,
        frame_args.sim_in,
        frame_args,
    )


sim_frame_particle3d = sim_frame_particleAnimation


def generate_field_comparison_report(data, run_dir, args=None):
    params = args if args is not None else data["models"]["fieldComparisonAnimation"]
    grid = data["models"]["simulationGrid"]
    dimension = params["dimension"]
    with h5py.File(str(py.path.local(run_dir).join(_COMPARISON_FILE)), "r") as f:
        values = f["data/{}/meshes/E/{}".format(COMPARISON_STEP_SIZE, dimension)]
        values = values[()]

    radius = _meters(data["models"]["simulationGrid"]["channel_width"] / 2.0)
    half_height = _meters(grid["channel_height"] / 2.0)
    ranges = {
        "x": [-radius, radius],
        "y": [-half_height, half_height],
        "z": [0, _meters(grid["plate_spacing"])],
    }
    plot_range = ranges[dimension]
    plots, plot_y_range = _create_plots(
        dimension, params, values, ranges, _SIM_DATA.warpvnd_is_3d(data)
    )
    return {
        "title": "Comparison of E {}".format(dimension),
        "y_label": "E {} [V/m]".format(dimension),
        "x_label": "{} [m]".format(dimension),
        "y_range": plot_y_range,
        "x_range": [plot_range[0], plot_range[1], len(plots[0]["points"])],
        "plots": plots,
        "summaryData": {"runMode3d": _SIM_DATA.warpvnd_is_3d(data)},
    }


def generate_field_report(data, run_dir, args=None):
    grid = data.models.simulationGrid
    axes, slice_axis, phi_slice, show3d = _field_input(args)
    slice_text = (
        " ({} = {}µm)".format(slice_axis, round(phi_slice, 3))
        if _SIM_DATA.warpvnd_is_3d(data)
        else ""
    )

    f = str(py.path.local(run_dir).join(_POTENTIAL_FILE))
    with h5py.File(f, "r") as hf:
        potential = np.array(template_common.h5_to_dict(hf, path="potential"))

    # if 2d potential, asking for 2d vs 3d doesn't matter
    if len(potential.shape) == 2:
        values = potential[: grid.num_x + 1, : grid.num_z + 1]
    else:
        values = _field_values(potential, axes, phi_slice, grid)

    vals_equal = np.isclose(np.std(values), 0.0, atol=1e-9)

    if np.isnan(values).any():
        raise sirepo.util.UserAlert(
            "Results could not be calculated.\n\nThe Simulation Grid may"
            " require adjustments to the Grid Points and Channel Width."
        )
    res = _field_plot(values, axes, grid, _SIM_DATA.warpvnd_is_3d(data))
    res.title = "ϕ Across Whole Domain" + slice_text
    res.global_min = np.min(potential) if vals_equal else None
    res.global_max = np.max(potential) if vals_equal else None
    res.frequency_title = "Volts"
    return res


def get_data_file(run_dir, model, frame, options):
    if (
        model == "particleAnimation"
        or model == "egunCurrentAnimation"
        or model == "particle3d"
    ):
        return (
            _PARTICLE_FILE
            if model in ("particleAnimation", "particle3d")
            else _EGUN_CURRENT_FILE
        )
    files = _h5_file_list(run_dir, model)
    # TODO(pjm): last client file may have been deleted on a canceled animation,
    # give the last available file instead.
    if len(files) < frame + 1:
        frame = -1
    return str(files[int(frame)])


def get_zcurrent_new(particle_array, momenta, mesh, particle_weight, dz):
    """
    Find z-directed current on a per cell basis
    particle_array: z positions at a given step
    momenta: particle momenta at a given step in SI units
    mesh: Array of Mesh spacings
    particle_weight: Weight from Warp
    dz: Cell Size
    """
    current = np.zeros_like(mesh)
    velocity = (
        constants.c
        * momenta
        / np.sqrt(momenta**2 + (constants.electron_mass * constants.c) ** 2)
        * particle_weight
    )

    for index, zval in enumerate(particle_array):
        bucket = np.round(zval / dz)  # value of the bucket/index in the current array
        current[int(bucket)] += velocity[index]

    return current * constants.elementary_charge / dz


def new_simulation(data, new_simulation_data, qcall, **kwargs):
    if "conductorFile" in new_simulation_data:
        c_file = new_simulation_data.conductorFile
        if c_file:
            # verify somehow?
            data.models.simulation.conductorFile = c_file
            data.models.simulationGrid.simulation_mode = "3d"


def open_data_file(run_dir, model_name, file_index=None):
    """Opens data file_index'th in run_dir

    Args:
        run_dir (py.path): has subdir ``hdf5``
        file_index (int): which file to open (default: last one)

    Returns:
        PKDict: various parameters
    """
    files = _h5_file_list(run_dir, model_name)
    res = PKDict()
    res.num_frames = len(files)
    res.frame_index = res.num_frames - 1 if file_index is None else file_index
    res.filename = str(files[res.frame_index])
    res.iteration = int(re.search(r"data(\d+)", res.filename).group(1))
    return res


def prepare_sequential_output_file(run_dir, data):
    if data.report == "fieldComparisonReport" or data.report == "fieldReport":
        fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if fn.exists():
            fn.remove()
            if data.report == "fieldComparisonReport":
                template_common.write_sequential_result(
                    generate_field_comparison_report(data, run_dir),
                    run_dir=run_dir,
                )
            else:
                template_common.write_sequential_result(
                    generate_field_report(data, run_dir),
                    run_dir=run_dir,
                )


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data, qcall=qcall)[0]


def remove_last_frame(run_dir):
    for m in ("currentAnimation", "fieldAnimation", "fieldCalculationAnimation"):
        files = _h5_file_list(run_dir, m)
        if len(files) > 0:
            pkio.unchecked_remove(files[-1])


def stateful_compute_save_stl_polys(data, **kwargs):
    if "polys" not in data:
        return PKDict(error='"polys" must be supplied')
    b = _stl_polygon_file(data.filename)
    if not _SIM_DATA.lib_file_exists(b):
        with sirepo.sim_run.tmp_dir() as t:
            p = t.join(b)
            template_common.write_dict_to_h5(data, p, h5_path="/")
            _SIM_DATA.lib_file_write(b, p)
    return PKDict()


def write_parameters(data, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    txt, v = _generate_parameters_file(data)
    if v["isOptimize"]:
        pkio.write_text(
            run_dir.join(_OPTIMIZE_PARAMETER_FILE),
            txt,
        )
        pkio.write_text(
            run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
            _generate_optimizer_file(data, v),
        )
    else:
        pkio.write_text(
            run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
            txt,
        )


def _add_margin(bounds):
    width = bounds[1] - bounds[0]
    if width:
        margin = width * 0.05
    else:
        margin = 0.05
    return [bounds[0] - margin, bounds[1] + margin]


def _add_particle_paths(electrons, x_points, y_points, z_points, half_height, limit):
    # adds paths for the particleAnimation report
    # culls adjacent path points with similar slope
    count = 0
    cull_count = 0
    for i in range(min(len(electrons[1]), limit)):
        res = {"x": [], "y": [], "z": []}
        num_points = len(electrons[1][i])
        prev = [None, None, None]
        for j in range(num_points):
            curr = [
                electrons[1][i][j],
                electrons[0][i][j],
                electrons[2][i][j],
            ]
            if 0 < j < num_points - 1:
                next = [
                    electrons[1][i][j + 1],
                    electrons[0][i][j + 1],
                    electrons[2][i][j + 1],
                ]
                if _cull_particle_point(curr, next, prev):
                    cull_count += 1
                    continue
            res["x"].append(curr[0])
            res["y"].append(curr[1])
            res["z"].append(curr[2])
            prev = curr
        count += len(res["x"])
        x_points.append(res["x"])
        y_points.append(res["y"])
        z_points.append(res["z"])
    pkdc(
        "particles: {} paths, {} points {} points culled",
        len(x_points),
        count,
        cull_count,
    )


def _compute_delta_for_field(data, bounds, field):
    # TODO(pjm): centralize list of meter fields
    if field in ("xLength", "yLength", "zLength", "xCenter", "yCenter", "zCenter"):
        bounds[0] = _meters(bounds[0])
        bounds[1] = _meters(bounds[1])
    delta = {
        "z": _grid_delta(data, "plate_spacing", "num_z"),
        "x": _grid_delta(data, "channel_width", "num_x"),
        "y": _grid_delta(data, "channel_height", "num_y"),
    }
    m = re.search(r"^(\w)Center$", field)
    if m:
        dim = m.group(1)
        bounds += [delta[dim], False]
        return
    _DEFAULT_SIZE = data.models.optimizer.continuousFieldSteps
    res = (bounds[1] - bounds[0]) / _DEFAULT_SIZE
    bounds += [res if res else bounds[1], True]


def _create_plots(dimension, params, values, ranges, is3d):
    show3d = params.displayMode == "3d"
    all_axes = "xyz" if is3d and show3d else "xz"
    other_axes = re.sub("[" + dimension + "]", "", all_axes)
    y_range = None
    plots = []
    color = SCHEMA.constants.cellColors
    label_fmts = {"x": "{:.0f} nm", "y": "{:.0f} nm", "z": "{:.3f} µm"}
    label_factors = {"x": 1e9, "y": 1e9, "z": 1e6}
    shapes = {"x": values.shape[0], "y": values.shape[1], "z": values.shape[2]}
    x_points = {}
    for axis in all_axes:
        if axis not in other_axes:
            continue
        x_points[axis] = np.linspace(ranges[axis][0], ranges[axis][1], shapes[axis])
    for i in (1, 2, 3):
        other_indices = {}
        for axis in all_axes:
            if axis not in other_axes:
                continue
            f = "{}Cell{}".format(axis, i)
            index = int(params[f])
            max_index = shapes[axis]
            if index >= max_index:
                index = max_index - 1
            other_indices[axis] = index
        y_index = other_indices["y"] if "y" in other_indices else 0
        if dimension == "x":
            points = values[:, y_index, other_indices["z"]].tolist()
        elif dimension == "y":
            points = values[other_indices["x"], :, other_indices["z"]].tolist()
        else:
            points = values[other_indices["x"], y_index, :].tolist()

        label = ""
        for axis in other_indices:
            v = x_points[axis][other_indices[axis]]
            pos = label_fmts[axis].format(v * label_factors[axis])
            label = label + "{} Location {} ".format(axis.upper(), pos)
        plots.append(
            {
                "points": points,
                # TODO(pjm): refactor with template_common.compute_plot_color_and_range()
                "color": color[i - 1],
                "label": label,
            }
        )
        if y_range:
            y_range[0] = min(y_range[0], min(points))
            y_range[1] = max(y_range[1], max(points))
        else:
            y_range = [min(points), max(points)]
    return plots, y_range


def _cull_particle_point(curr, next, prev):
    # check all three dimensions xy, xz, yz
    if (
        _particle_line_has_slope(curr, next, prev, 0, 1)
        or _particle_line_has_slope(curr, next, prev, 0, 2)
        or _particle_line_has_slope(curr, next, prev, 1, 2)
    ):
        return False
    return True


def _extract_current(data, data_file):
    grid = data["models"]["simulationGrid"]
    plate_spacing = _meters(grid["plate_spacing"])
    dz = plate_spacing / grid["num_z"]
    zmesh = np.linspace(
        0, plate_spacing, grid["num_z"] + 1
    )  # holds the z-axis grid points in an array
    report_data = readparticles(data_file.filename)
    data_time = report_data["time"]
    with h5py.File(data_file.filename, "r") as f:
        weights = np.array(
            f["data/{}/particles/beam/weighting".format(data_file.iteration)]
        )
    curr = get_zcurrent_new(
        report_data["beam"][:, 4], report_data["beam"][:, 5], zmesh, weights, dz
    )
    return _extract_current_results(data, curr, data_time)


def _extract_current_results(data, curr, data_time):
    grid = data["models"]["simulationGrid"]
    plate_spacing = _meters(grid["plate_spacing"])
    zmesh = np.linspace(
        0, plate_spacing, grid["num_z"] + 1
    )  # holds the z-axis grid points in an array
    beam = data["models"]["beam"]
    if _SIM_DATA.warpvnd_is_3d(data):
        cathode_area = _meters(grid["channel_width"]) * _meters(grid["channel_height"])
    else:
        cathode_area = _meters(grid["channel_width"])
    RD_ideal = (
        sources.j_rd(beam["cathode_temperature"], beam["cathode_work_function"])
        * cathode_area
    )
    JCL_ideal = (
        sources.cl_limit(
            beam["cathode_work_function"],
            beam["anode_work_function"],
            beam["anode_voltage"],
            plate_spacing,
        )
        * cathode_area
    )

    if beam["currentMode"] == "2" or (
        beam["currentMode"] == "1" and beam["beam_current"] >= JCL_ideal
    ):
        curr2 = np.full_like(zmesh, JCL_ideal)
        y2_title = "Child-Langmuir cold limit"
    else:
        curr2 = np.full_like(zmesh, RD_ideal)
        y2_title = "Richardson-Dushman"
    return {
        "title": "Current for Time: {:.4e}s".format(data_time),
        "x_range": [0, plate_spacing],
        "y_label": "Current [A]",
        "x_label": "Z [m]",
        "points": [
            curr.tolist(),
            curr2.tolist(),
        ],
        "x_points": zmesh.tolist(),
        "y_range": [min(np.min(curr), np.min(curr2)), max(np.max(curr), np.max(curr2))],
        "y1_title": "Current",
        "y2_title": y2_title,
    }


def _extract_egun_current(data, data_file, frame_index):
    v = np.load(str(data_file))
    if frame_index >= len(v):
        frame_index = -1
    # the first element in the array is the time, the rest are the current measurements
    return _extract_current_results(data, v[frame_index][1:], v[frame_index][0])


def _extract_field(field, data, data_file, args=None):
    grid = data.models.simulationGrid
    axes, slice_axis, field_slice, show3d = _field_input(args)

    selector = field if field == "phi" else "E/{}".format(field)
    with h5py.File(data_file.filename, "r") as hf:
        field_values = np.array(
            hf["data/{}/meshes/{}".format(data_file.iteration, selector)]
        )
        data_time = hf["data/{}".format(data_file.iteration)].attrs["time"]
        dt = hf["data/{}".format(data_file.iteration)].attrs["dt"]

    slice_text = (
        " ({} = {}µm)".format(slice_axis, round(field_slice, 3))
        if _SIM_DATA.warpvnd_is_3d(data)
        else ""
    )

    if field == "phi":
        title = "ϕ"
        if not _SIM_DATA.warpvnd_is_3d(data):
            values = field_values[0, :, :]
        else:
            values = _field_values(field_values, axes, field_slice, grid)
    else:
        title = "E {}".format(field)
        if not _SIM_DATA.warpvnd_is_3d(data):
            values = field_values[:, 0, :]
        else:
            values = _field_values(field_values, axes, field_slice, grid)

    vals_equal = np.isclose(np.std(values), 0.0, atol=1e-9)

    res = _field_plot(values, axes, grid, _SIM_DATA.warpvnd_is_3d(data))
    res.title = "{}{} for Time: {:.4e}s, Step {}".format(
        title, slice_text, data_time, data_file.iteration
    )
    res.global_min = np.min(field_values) if vals_equal else None
    res.global_max = np.max(field_values) if vals_equal else None
    return res


def _extract_impact_density(run_dir, data):
    if _SIM_DATA.warpvnd_is_3d(data):
        return _extract_impact_density_3d(run_dir, data)
    return _extract_impact_density_2d(run_dir, data)


def _extract_impact_density_2d(run_dir, data):
    # use a simple heatmap instead due to a normalization problem in rswarp
    if not pkio.py_path(run_dir.join(_ALL_PARTICLES_FILE)).exists():
        return PKDict(
            error="No impact data recorded",
        )
    all_particles = np.load(_ALL_PARTICLES_FILE)
    grid = data.models.simulationGrid
    plate_spacing = _meters(grid.plate_spacing)
    channel_width = _meters(grid.channel_width)
    m = PKDict(
        histogramBins=200,
        plotRangeType="fixed",
        horizontalSize=plate_spacing * 1.02,
        horizontalOffset=plate_spacing / 2,
        verticalSize=channel_width,
        verticalOffset=0,
    )
    return template_common.heatmap(
        [all_particles[1].tolist(), all_particles[0].tolist()],
        m,
        PKDict(
            x_label="z [m]",
            y_label="x [m]",
            title="Impact Density",
            aspectRatio=4.0 / 7,
        ),
    )


def _extract_impact_density_3d(run_dir, data):
    try:
        with h5py.File(str(run_dir.join(_DENSITY_FILE)), "r") as hf:
            plot_info = template_common.h5_to_dict(hf, path="density")
    except IOError:
        plot_info = {"error": "Cannot load density file"}
    if "error" in plot_info:
        if not _SIM_DATA.warpvnd_is_3d(data):
            return plot_info
        # for 3D, continue on so particle trace is still rendered
        plot_info = {
            "dx": 0,
            "dz": 0,
            "min": 0,
            "max": 0,
        }
    # TODO(pjm): consolidate these parameters into one routine used by all reports
    grid = data.models.simulationGrid
    plate_spacing = _meters(grid.plate_spacing)
    radius = _meters(grid.channel_width / 2.0)
    width = 0

    dx = plot_info["dx"]
    dy = 0
    dz = plot_info["dz"]

    if _SIM_DATA.warpvnd_is_3d(data):
        dy = 0  # plot_info['dy']
        width = _meters(grid.channel_width)

    return {
        "title": "Impact Density",
        "x_range": [0, plate_spacing],
        "y_range": [-radius, radius],
        "z_range": [-width / 2.0, width / 2.0],
        "y_label": "x [m]",
        "x_label": "z [m]",
        "z_label": "y [m]",
        "density": plot_info["density"] if "density" in plot_info else [],
        "v_min": plot_info["min"],
        "v_max": plot_info["max"],
    }


def _extract_optimization_results(run_dir, data, args):
    x_index = int(args.x or "0")
    y_index = int(args.y or "0")
    # steps, time, tolerance, result, p1, ... pn
    res, best_row = _read_optimizer_output(run_dir)
    field_info = res[:, :4]
    field_values = res[:, 4:]
    fields = data.models.optimizer.fields
    if x_index > len(fields) - 1:
        x_index = 0
    if y_index > len(fields) - 1:
        y_index = 0
    x = field_values[:, x_index]
    y = field_values[:, y_index]
    if x_index == y_index:
        y = np.zeros(len(y))
    score = field_info[:, _OPT_RESULT_INDEX]
    return {
        "title": "",
        "v_min": min(score),
        "v_max": max(score),
        "x_range": _add_margin([min(x), max(x)]),
        "y_range": _add_margin([min(y), max(y)]),
        "x_field": fields[x_index].field,
        "y_field": fields[y_index].field,
        "optimizerPoints": field_values.tolist(),
        "optimizerInfo": field_info.tolist(),
        "x_index": x_index,
        "y_index": y_index,
        "fields": [x.field for x in fields],
    }


def _extract_particle(run_dir, model_name, data, args):
    limit = int(args.renderCount)
    with open(_PARTICLE_FILE, "rb") as f:
        d = msgpack.unpackb(f.read())
        kept_electrons = d["kept"]
        lost_electrons = d["lost"]
    grid = data["models"]["simulationGrid"]
    plate_spacing = _meters(grid["plate_spacing"])
    radius = _meters(grid["channel_width"] / 2.0)
    half_height = grid["channel_height"] if "channel_height" in grid else 5.0
    half_height = _meters(half_height / 2.0)
    x_points = []
    y_points = []
    z_points = []
    _add_particle_paths(
        kept_electrons, x_points, y_points, z_points, half_height, limit
    )
    lost_x = []
    lost_y = []
    lost_z = []
    _add_particle_paths(lost_electrons, lost_x, lost_y, lost_z, half_height, limit)
    data_file = open_data_file(run_dir, model_name, None)
    with h5py.File(data_file.filename, "r") as f:
        field = np.array(f["data/{}/meshes/{}".format(data_file.iteration, "phi")])
    return {
        "title": "Particle Trace",
        "x_range": [0, plate_spacing],
        "y_label": "x [m]",
        "x_label": "z [m]",
        "z_label": "y [m]",
        "points": y_points,
        "x_points": x_points,
        "z_points": z_points,
        "y_range": [-radius, radius],
        "z_range": [-half_height, half_height],
        "lost_x": lost_x,
        "lost_y": lost_y,
        "lost_z": lost_z,
        "field": field.tolist(),
    }


def _field_input(args):
    show3d = (
        args.displayMode == "3d"
        if args is not None and "displayMode" in args
        else False
    )
    a = args.axes if args is not None and "axes" in args else "xz"
    axes = (a if show3d else "xz") if a else "xz"
    slice_axis = re.sub("[" + axes + "]", "", "xyz")
    field_slice = (
        (float(args.slice) if args.slice else 0.0)
        if args and "slice" in args and show3d
        else 0.0
    )
    return axes, slice_axis, field_slice, show3d


def _field_plot(values, axes, grid, is3d):
    plate_spacing = _meters(grid.plate_spacing)
    radius = _meters(grid.channel_width / 2.0)
    half_height = _meters(grid.channel_height / 2.0)

    if axes == "xz":
        xr = [0, plate_spacing]
        yr = [-radius, radius]
        x_label = "z [m]"
        y_label = "x [m]"
        ar = 6.0 / 14
    elif axes == "xy":
        xr = [-half_height, half_height]
        yr = [-radius, radius]
        x_label = "y [m]"
        y_label = "x [m]"
        ar = (radius / half_height,)
    else:
        xr = [0, plate_spacing]
        yr = [-half_height, half_height]
        x_label = "z [m]"
        y_label = "y [m]"
        ar = 6.0 / 14

    xr.append(len(values[0]))
    yr.append(len(values))

    return PKDict(
        {
            "aspectRatio": ar,
            "x_range": xr,
            "y_range": yr,
            "x_label": x_label,
            "y_label": y_label,
            "z_matrix": values.tolist(),
            "summaryData": {"runMode3d": is3d},
        }
    )


def _field_values(values, axes, field_slice, grid):
    dx = grid.channel_width / grid.num_x
    dy = grid.channel_height / grid.num_y
    dz = grid.plate_spacing / grid.num_z
    if axes == "xz":
        return values[
            :,
            _get_slice_index(
                field_slice, -grid.channel_height / 2.0, dy, grid.num_y - 1
            ),
            :,
        ]
    elif axes == "xy":
        return values[:, :, _get_slice_index(field_slice, 0.0, dz, grid.num_z - 1)]
    else:
        return values[
            _get_slice_index(
                field_slice, -grid.channel_width / 2.0, dx, grid.num_x - 1
            ),
            :,
            :,
        ]


def _find_by_id(container, id):
    for c in container:
        if str(c.id) == str(id):
            return c
    assert False, "missing id: {} in container".format(id)


def _get_slice_index(x, min_x, dx, max_index):
    return min(max_index, max(0, int(round((x - min_x) / dx))))


def _grid_delta(data, length_field, count_field):
    grid = data.models.simulationGrid
    # TODO(pjm): already converted to meters
    return grid[length_field] / grid[count_field]


def _generate_optimizer_file(data, v):
    # iterate opt vars and compute [min, max, dx, is_continuous]
    for opt in data.models.optimizer.fields:
        m, f, container, id = _parse_optimize_field(opt.field)
        opt.bounds = [opt.minimum, opt.maximum]
        _compute_delta_for_field(data, opt.bounds, f)
    v["optField"] = data.models.optimizer.fields
    v["optimizerStatusFile"] = _OPTIMIZER_STATUS_FILE
    v["optimizerOutputFile"] = _OPTIMIZER_OUTPUT_FILE
    v["optimizerResultFile"] = _OPTIMIZER_RESULT_FILE
    return _render_jinja("optimizer", v)


def _generate_parameters_file(data, qcall=None):
    v = None
    template_common.validate_models(data, SCHEMA)
    res, v = template_common.generate_parameters_file(data)
    v["allParticlesFile"] = _ALL_PARTICLES_FILE
    v["particlePeriod"] = _PARTICLE_PERIOD
    v["particleFile"] = _PARTICLE_FILE
    v["potentialFile"] = _POTENTIAL_FILE
    v["stepSize"] = COMPARISON_STEP_SIZE
    v["densityFile"] = _DENSITY_FILE
    v["egunCurrentFile"] = _EGUN_CURRENT_FILE
    v["estimateFile"] = _FIELD_ESTIMATE_FILE
    v["conductors"] = _prepare_conductors(data, qcall=qcall)
    v["maxConductorVoltage"] = _max_conductor_voltage(data)
    v["is3D"] = _SIM_DATA.warpvnd_is_3d(data)
    v["saveIntercept"] = (
        v["anode_reflectorType"] != "none" or v["cathode_reflectorType"] != "none"
    )
    for c in data.models.conductors:
        if c.conductor_type.type == "stl":
            # if any conductor is STL then don't save the intercept
            v["saveIntercept"] = False
            v["polyFile"] = _SIM_DATA.lib_file_abspath(
                _stl_polygon_file(c.conductor_type.name),
                qcall=qcall,
            )
            break
        if c.conductor_type.reflectorType != "none":
            v["saveIntercept"] = True
    if not v["is3D"]:
        v["simulationGrid_num_y"] = v["simulationGrid_num_x"]
        v["simulationGrid_channel_height"] = v["simulationGrid_channel_width"]
    if "report" not in data:
        data["report"] = "animation"
    v["isOptimize"] = data["report"] == "optimizerAnimation"
    if v["isOptimize"]:
        _replace_optimize_variables(data, v)
    res = _render_jinja("base", v)
    if data["report"] == "animation":
        if data["models"]["simulation"]["egun_mode"] == "1":
            v["egunStatusFile"] = _EGUN_STATUS_FILE
            res += _render_jinja("egun", v)
        else:
            res += _render_jinja("visualization", v)
        res += _render_jinja("impact-density", v)
    elif data["report"] == "optimizerAnimation":
        res += _render_jinja("parameters-optimize", v)
    else:
        res += _render_jinja("source-field", v)
    return res, v


def _h5_file_list(run_dir, model_name):
    return pkio.walk_tree(
        run_dir.join(
            "diags/xzsolver/hdf5"
            if model_name == "currentAnimation"
            else "diags/fields/electric"
        ),
        r"\.h5$",
    )


def _max_conductor_voltage(data):
    res = data.models.beam.anode_voltage
    for c in data.models.conductors:
        # conductor_type has been added to conductor during _prepare_conductors()
        if float(c.conductor_type.voltage) > float(res):
            res = c.conductor_type.voltage
    return res


def _meters(v):
    # convert microns to meters
    return float(v) * 1e-6


def _mpi_core_count(run_dir):
    mpi_file = py.path.local(run_dir).join(MPI_SUMMARY_FILE)
    if mpi_file.exists():
        info = simulation_db.read_json(mpi_file)
        if "mpiCores" in info:
            return info["mpiCores"]
    return 0


def _optimizer_percent_complete(run_dir, is_running):
    if not run_dir.exists():
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    res, best_row = _read_optimizer_output(run_dir)
    summary_data = None
    frame_count = 0
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    optimizer = data.models.optimizer
    if res is not None:
        frame_count = len(res)
        if not is_running:
            result_file = run_dir.join(_OPTIMIZER_RESULT_FILE)
            if result_file.exists():
                summary_data = simulation_db.read_json(result_file)
        if not summary_data:
            best_row = best_row.tolist()
            summary_data = {
                "fun": best_row[3],
                "x": best_row[4:],
            }
        summary_data["fields"] = optimizer.fields
    if is_running:
        status_file = run_dir.join(_OPTIMIZER_STATUS_FILE)
        if status_file.exists():
            try:
                if not summary_data:
                    summary_data = {}
                rows = np.loadtxt(str(status_file))
                if len(rows.shape) == 1:
                    rows = np.array([rows])
                summary_data["statusRows"] = rows.tolist()
                summary_data["fields"] = optimizer.fields
                summary_data["frameCount"] = frame_count
                summary_data["initialSteps"] = optimizer.initialSteps
                summary_data["optimizerSteps"] = optimizer.optimizerSteps
            except TypeError:
                pass
            except ValueError:
                pass
    if summary_data:
        return PKDict(
            percentComplete=0 if is_running else 100,
            frameCount=frame_count,
            summary=summary_data,
        )
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    # TODO(pjm): determine optimization error
    return PKDict(
        percentComplete=0,
        frameCount=0,
        error="optimizer produced no data",
        state="error",
    )


def _parse_optimize_field(text):
    # returns (model_name, field_name, container_name, id)
    m, f = text.split(".")
    container, id = None, None
    if re.search(r"#", m):
        name, id = m.split("#")
        container = "conductors" if name == "conductorPosition" else "conductorTypes"
    return m, f, container, id


def _particle_line_has_slope(curr, next, prev, i1, i2):
    return (
        abs(
            _slope(curr[i1], curr[i2], next[i1], next[i2])
            - _slope(prev[i1], prev[i2], curr[i1], curr[i2])
        )
        >= _CULL_PARTICLE_SLOPE
    )


def _prepare_conductors(data, qcall):
    type_by_id = {}
    for ct in data.models.conductorTypes:
        if ct is None:
            continue
        type_by_id[ct.id] = ct
        # pkdlog('!PREP CONDS {}', ct)
        for f in ("xLength", "yLength", "zLength"):
            ct[f] = _meters(ct[f])
        if not _SIM_DATA.warpvnd_is_3d(data):
            ct.yLength = 1
        ct.permittivity = ct.permittivity if ct.isConductor == "0" else "None"
        ct.file = (
            _SIM_DATA.lib_file_abspath(_stl_file(ct), qcall=qcall)
            if "file" in ct
            else "None"
        )
    for c in data.models.conductors:
        if c.conductorTypeId not in type_by_id:
            continue
        c.conductor_type = type_by_id[c.conductorTypeId]
        for f in ("xCenter", "yCenter", "zCenter"):
            c[f] = _meters(c[f])
        if not _SIM_DATA.warpvnd_is_3d(data):
            c.yCenter = 0
    return data.models.conductors


def _read_optimizer_output(run_dir):
    # only considers unique points as steps
    opt_file = run_dir.join(_OPTIMIZER_OUTPUT_FILE)
    if not opt_file.exists():
        return None, None
    try:
        values = np.loadtxt(str(opt_file))
        if values.any():
            if len(values.shape) == 1:
                values = np.array([values])
        else:
            return None, None
    except TypeError:
        return None, None
    except ValueError:
        return None, None

    res = []
    best_row = None
    # steps, time, tolerance, result, p1, ... pn
    for v in values:
        res.append(v)
        if best_row is None or v[_OPT_RESULT_INDEX] > best_row[_OPT_RESULT_INDEX]:
            best_row = v
    return np.array(res), best_row


def _render_jinja(template, v):
    return template_common.render_jinja(SIM_TYPE, v, "{}.py".format(template))


def _replace_optimize_variables(data, v):
    v["optimizeFields"] = []
    v["optimizeConstraints"] = []
    fields = []
    for opt in data.models.optimizer.fields:
        fields.append(opt.field)
    for constraint in data.models.optimizer.constraints:
        for idx in range(len(fields)):
            if constraint[0] == fields[idx]:
                v["optimizeConstraints"].append(idx)
                break
        fields.append(constraint[2])
    for field in fields:
        v["optimizeFields"].append(field)
        value = "opts['{}']".format(field)
        m, f, container, id = _parse_optimize_field(field)
        if container:
            model = _find_by_id(data.models[container], id)
            model[f] = value
        else:
            v["{}_{}".format(m, f)] = value


def _simulation_percent_complete(report, run_dir, is_running):
    if report == "fieldCalculationAnimation":
        if run_dir.join(_POTENTIAL_FILE).exists():
            return PKDict(
                {
                    "percentComplete": 100,
                    "frameCount": 1,
                }
            )
        return PKDict(
            {
                "percentComplete": 0,
                "frameCount": 0,
            }
        )
    files = _h5_file_list(run_dir, "currentAnimation")
    if (is_running and len(files) < 2) or (not run_dir.exists()):
        return PKDict(
            mpiCores=_mpi_core_count(run_dir),
            percentComplete=0,
            frameCount=0,
        )
    if len(files) == 0:
        return PKDict(
            percentComplete=100,
            frameCount=0,
            error="simulation produced no frames",
            state="error",
        )
    file_index = len(files) - 1
    res = PKDict(
        mpiCores=_mpi_core_count(run_dir),
        lastUpdateTime=int(os.path.getmtime(str(files[file_index]))),
    )
    # look at 2nd to last file if running, last one may be incomplete
    if is_running:
        file_index -= 1
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    percent_complete = 0
    if data.models.simulation.egun_mode == "1":
        status_file = run_dir.join(_EGUN_STATUS_FILE)
        if status_file.exists():
            with open(str(status_file), "r") as f:
                m = re.search(r"([\d\.]+)\s*/\s*(\d+)", f.read())
            if m:
                percent_complete = float(m.group(1)) / int(m.group(2))
        egun_current_file = run_dir.join(_EGUN_CURRENT_FILE)
        if egun_current_file.exists():
            v = np.load(str(egun_current_file))
            res.egunCurrentFrameCount = len(v)
    else:
        percent_complete = (
            (file_index + 1.0) * _PARTICLE_PERIOD / data.models.simulationGrid.num_steps
        )
        percent_complete /= 2.0
    if percent_complete < 0:
        percent_complete = 0
    elif percent_complete > 1.0:
        percent_complete = 1.0
    res.percentComplete = percent_complete * 100
    res.frameCount = file_index + 1
    return res


def _slope(x1, y1, x2, y2):
    if x2 - x1 == 0:
        # treat no slope as flat for comparison
        return 0
    return (y2 - y1) / (x2 - x1)


def _stl_file(conductor_type):
    return _SIM_DATA.lib_file_name_with_model_field("stl", "file", conductor_type.file)


def _stl_polygon_file(filename):
    return _SIM_DATA.lib_file_name_with_model_field("stl", filename, _STL_POLY_FILE)
