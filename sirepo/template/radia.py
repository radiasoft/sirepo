"""Radia execution template.

All Radia calls have to be done from here, NOT in jinja files, because otherwise the
Radia "instance" goes away and references no longer have any meaning.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkinspect
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp, pkdlog
from scipy.spatial.transform import Rotation
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import radia_util
from sirepo.template import template_common
import copy
import csv
import h5py
import math
import numpy
import os.path
import re
import sdds
import sirepo.csv
import sirepo.sim_data
import sirepo.util
import trimesh
import uuid

_AXES_UNIT = [1, 1, 1]

_AXIS_ROTATIONS = PKDict(
    x=PKDict(
        x=Rotation.identity(),
        y=Rotation.from_matrix([[0, -1, 0], [1, 0, 0], [0, 0, 1]]),
        z=Rotation.from_matrix([[0, 0, -1], [0, 1, 0], [1, 0, 0]]),
    ),
    y=PKDict(
        x=Rotation.from_matrix([[0, -1, 0], [1, 0, 0], [0, 0, 1]]),
        y=Rotation.identity(),
        z=Rotation.from_matrix([[1, 0, 0], [0, 0, 1], [0, -1, 0]]),
    ),
    z=PKDict(
        x=Rotation.from_matrix([[0, 0, 1], [0, 1, 0], [-1, 0, 0]]),
        y=Rotation.from_matrix([[1, 0, 0], [0, 0, -1], [0, 1, 0]]),
        z=Rotation.identity(),
    ),
)

_DIPOLE_NOTES = PKDict(
    dipoleBasic="Simple dipole with permanent magnets",
    dipoleC="C-bend dipole with a single coil",
    dipoleH="H-bend dipole with two coils",
)

_DMP_FILE = "geometry.dat"

_FREEHAND_NOTES = PKDict(
    freehand="",
)

_UNDULATOR_NOTES = PKDict(
    undulatorBasic="Simple undulator with permanent magnets",
    undulatorHybrid="Undulator with alternating permanent magnets and susceptible poles",
)

_MAGNET_NOTES = PKDict(
    dipole=_DIPOLE_NOTES,
    freehand=_FREEHAND_NOTES,
    undulator=_UNDULATOR_NOTES,
)

_MILLIS_TO_METERS = 0.001

# Note that these column names and units are required by elegant
_FIELD_MAP_COLS = ["x", "y", "z", "Bx", "By", "Bz"]
_FIELD_MAP_UNITS = ["m", "m", "m", "T", "T", "T"]
_KICK_MAP_COLS = ["x", "y", "xpFactor", "ypFactor"]
_KICK_MAP_UNITS = ["m", "m", "(T*m)$a2$n", "(T*m)$a2$n"]
_GEOM_DIR = "geometryReport"
_GEOM_FILE = "geometryReport.h5"
_HEADER_FILE = "header.py"
_KICK_FILE = "kickMap.h5"
_KICK_SDDS_FILE = "kickMap.sdds"
_KICK_TEXT_FILE = "kickMap.txt"
_METHODS = [
    "get_field",
    "get_field_integrals",
    "get_geom",
    "get_kick_map",
    "save_field",
]
_POST_SIM_REPORTS = [
    "electronTrajectoryReport",
    "fieldIntegralReport",
    "kickMapReport",
]
_SIM_REPORTS = ["geometryReport", "optimizerAnimation", "reset", "solverAnimation"]
_REPORTS = [
    "electronTrajectoryReport",
    "fieldIntegralReport",
    "fieldLineoutAnimation",
    "geometryReport",
    "kickMapReport",
    "optimizerAnimation",
    "reset",
    "solverAnimation",
]
_REPORT_RES_MAP = PKDict(
    reset="geometryReport",
    solverAnimation="geometryReport",
)
_RSOPT_OBJECTIVE_FUNCTION_OUT = "objective_function_results.h5"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_SDDS_INDEX = 0
_SIM_FILES = [b.basename for b in _SIM_DATA.sim_file_basenames(None)]

_ZERO = [0, 0, 0]

RADIA_EXPORT_FILE = "radia_export.py"
VIEW_TYPES = [SCHEMA.constants.viewTypeObjects, SCHEMA.constants.viewTypeFields]

# cfg contains sdds instance
_cfg = PKDict(sdds=None)


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    if report == "optimizerAnimation":
        return _rsopt_percent_complete(run_dir, res)
    if is_running:
        res.percentComplete = 0
        return res
    res.percentComplete = 100
    res.frameCount = 1
    if report == "solverAnimation":
        res.solution = _read_solution()
    return res


def code_var(variables):
    return code_variable.CodeVar(variables, code_variable.PurePythonEval())


def extract_report_data(run_dir, sim_in):
    assert sim_in.report in _REPORTS, "report={}: unknown report".format(sim_in.report)
    _SIM_DATA.sim_files_to_run_dir(sim_in, run_dir, post_init=True)
    if sim_in.report == "reset":
        template_common.write_sequential_result({}, run_dir=run_dir)
    if sim_in.report == "geometryReport":
        v_type = sim_in.models.magnetDisplay.viewType
        f_type = (
            sim_in.models.magnetDisplay.fieldType
            if v_type == SCHEMA.constants.viewTypeFields
            else None
        )
        d = _get_geom_data(
            sim_in.models.simulation.simulationId,
            get_g_id(),
            sim_in.models.simulation.name,
            v_type,
            f_type,
            field_paths=sim_in.models.fieldPaths.paths,
        )
        template_common.write_sequential_result(
            d,
            run_dir=run_dir,
        )
    if sim_in.report == "kickMapReport":
        template_common.write_sequential_result(
            _kick_map_plot(sim_in.models.kickMapReport),
            run_dir=run_dir,
        )
    if sim_in.report == "fieldIntegralReport":
        template_common.write_sequential_result(
            _generate_field_integrals(
                sim_in.models.simulation.simulationId,
                get_g_id(),
                sim_in.models.fieldPaths.paths or [],
            ),
            run_dir=run_dir,
        )
    if sim_in.report == "electronTrajectoryReport":
        a = sim_in.models.electronTrajectoryReport.initialAngles
        a.append(0)
        angles = [0, 0, 0]
        angles[radia_util.axes_index(sim_in.models.simulation.widthAxis)] = a[0]
        angles[radia_util.axes_index(sim_in.models.simulation.heightAxis)] = a[1]
        template_common.write_sequential_result(
            _electron_trajectory_plot(
                sim_in.models.simulation.simulationId,
                energy=sim_in.models.electronTrajectoryReport.energy,
                pos=sim_in.models.electronTrajectoryReport.initialPosition,
                angles=angles,
                y_final=sim_in.models.electronTrajectoryReport.finalBeamPosition,
                num_points=sim_in.models.electronTrajectoryReport.numPoints,
                beam_axis=sim_in.models.simulation.beamAxis,
                width_axis=sim_in.models.simulation.widthAxis,
                height_axis=sim_in.models.simulation.heightAxis,
                rotation=_rotate_axis(
                    to_axis="y", from_axis=sim_in.models.simulation.beamAxis
                ),
            )
        )
    if sim_in.report == "extrudedPolyReport":
        template_common.write_sequential_result(
            _extruded_points_plot(
                sim_in.models.geomObject.name,
                sim_in.models.extrudedPoly.points,
                sim_in.models.extrudedPoly.widthAxis,
                sim_in.models.extrudedPoly.heightAxis,
            ),
            run_dir=run_dir,
        )


def generate_field_data(sim_id, g_id, name, field_type, field_paths):
    assert (
        field_type in radia_util.FIELD_TYPES
    ), "field_type={}: invalid field type".format(field_type)
    try:
        if field_type == radia_util.FIELD_TYPE_MAG_M:
            f = radia_util.get_magnetization(g_id)
        else:
            f = radia_util.get_field(g_id, field_type, _build_field_points(field_paths))
        return radia_util.vector_field_to_data(
            g_id, name, f, radia_util.FIELD_UNITS[field_type]
        )
    except RuntimeError as e:
        _backend_alert(sim_id, g_id, e)


def get_data_file(run_dir, model, frame, options):
    assert model in _REPORTS, "model={}: unknown report".format(model)
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    sim = data.models.simulation
    name = sim.name
    sim_id = sim.simulationId
    rpt = data.models[model]
    sfx = options.suffix or SCHEMA.constants.dataDownloads._default[0].suffix
    f = f"{model}.{sfx}"
    if model == "electronTrajectoryReport":
        if sfx == "csv":
            return _save_trajectory_csv(
                f,
                beam_axis=sim.beamAxis,
                output=simulation_db.read_json(
                    run_dir.join(template_common.OUTPUT_BASE_NAME)
                ),
            )
        return f
    if model == "kickMapReport":
        return _save_kick_map_sdds(
            name, f, _read_or_generate_kick_map(get_g_id(), data.models.kickMapReport)
        )
    if model == "fieldLineoutAnimation":
        beam_axis = _rotate_axis(to_axis="z", from_axis=sim.beamAxis)
        f_type = rpt.fieldType
        fd = generate_field_data(sim_id, get_g_id(), name, f_type, [rpt.fieldPath])
        v = fd.data[0].vectors
        if sfx == "sdds":
            return _save_fm_sdds(name, v, beam_axis, f)
        if sfx == "csv":
            return _save_field_csv(f_type, v, beam_axis, f)
        if sfx == "zip":
            return _save_field_srw(
                data.models[data.models.simulation.undulatorType].gap,
                v,
                beam_axis,
                pkio.py_path(f),
            )
        return f
    if model == "optimizerAnimation":
        return template_common.text_data_file("optimize.out", run_dir)
    if model == "geometryReport":
        return template_common.JobCmdFile(
            reply_uri=f"{name}.{sfx}",
            reply_path=pkio.py_path(_DMP_FILE),
        )
    if model == "fieldIntegralReport":
        return _save_field_integrals_csv(
            data.models.fieldPaths.paths,
            simulation_db.read_json(run_dir.join(template_common.OUTPUT_BASE_NAME)),
            f,
        )
    raise AssertionError(f"unknown model={model}")


def get_g_id():
    return radia_util.load_bin(pkio.read_binary(_DMP_FILE))


def new_simulation(data, new_sim_data, qcall, **kwargs):
    _prep_new_sim(data, new_sim_data=new_sim_data)
    dirs = _geom_directions(new_sim_data.beamAxis, new_sim_data.heightAxis)
    t = new_sim_data.get("magnetType", "freehand")
    s = new_sim_data[f"{t}Type"]
    m = data.models[s]
    pkinspect.module_functions("_build_")[f"_build_{t}_objects"](
        data.models.geometryReport.objects,
        m,
        qcall=qcall,
        matrix=_get_coord_matrix(dirs, data.models.simulation.coordinateSystem),
        height_dir=dirs.height_dir,
        length_dir=dirs.length_dir,
        width_dir=dirs.width_dir,
    )


def post_execution_processing(success_exit, is_parallel, run_dir, **kwargs):
    if success_exit or not is_parallel:
        return None
    return template_common.parse_mpi_log(run_dir)


def prepare_for_client(data, qcall, **kwargs):
    return data


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data, False, for_export=True, qcall=qcall)


def save_field_srw(gap, vectors, beam_axis, filename):
    return _save_field_srw(
        gap,
        vectors,
        _rotate_axis(to_axis="z", from_axis=beam_axis),
        pkio.py_path(filename),
    )


def sim_frame_fieldLineoutAnimation(frame_args):
    return _field_lineout_plot(
        frame_args.sim_in.models.simulation.simulationId,
        frame_args.sim_in.models.simulation.name,
        frame_args.sim_in.models.fieldLineoutAnimation.fieldType,
        frame_args.sim_in.models.fieldLineoutAnimation.fieldPath,
        frame_args.sim_in.models.fieldLineoutAnimation.plotAxis,
        field_data=pkjson.load_any(pkio.py_path("field_data.json")),
    )


def sim_frame_optimizerAnimation(frame_args):
    return _extract_optimization_results(frame_args)


def stateful_compute_import_file(data, **kwargs):
    res = simulation_db.default_data(SIM_TYPE)
    res.models.simulation.pkupdate(
        dmpImportFile=data.args.basename,
        name=data.args.purebasename,
    )
    _prep_new_sim(res)
    # _prep_new_sim sets _MAGNET_NOTES for notes so overwrite after
    res.models.simulation.notes = f"Imported from {data.args.basename}"
    return PKDict(imported_data=res)


def stateful_compute_recompute_rpn_cache_values(data, **kwargs):
    code_var(data.variables, data.cache).recompute_cache(data.cache)
    return data


def stateless_compute_build_shape_points(data, **kwargs):
    o = _evaluated_object(data.args.object, code_var(data.args.rpnVariables))
    if not o.get("pointsFile"):
        return PKDict(
            points=pkinspect.module_functions("_get_")[f"_get_{o.type}_points"](
                o, _get_stemmed_info(o)
            )
        )
    pts = sirepo.csv.read_as_number_list(
        _SIM_DATA.lib_file_abspath(
            _SIM_DATA.lib_file_name_with_model_field(
                "extrudedPoints", "pointsFile", o.pointsFile
            )
        )
    )
    # Radia does not like it if the path is closed
    if all(numpy.isclose(pts[0], pts[-1])):
        del pts[-1]
    return PKDict(points=pts)


def stateless_compute_stl_size(data, **kwargs):
    f = _SIM_DATA.lib_file_abspath(
        _SIM_DATA.lib_file_name_with_type(data.args.file, SCHEMA.constants.fileTypeSTL)
    )
    m = _create_stl_trimesh(f)
    return PKDict(
        center=(m.bounding_box.bounds[0] + 0.5 * m.bounding_box.extents).tolist(),
        size=m.bounding_box.primitive.extents.tolist(),
    )


def validate_file(file_type, path):
    p = path.ext.lower()
    if p not in (".csv", ".dat", ".stl", ".txt"):
        return f"invalid file type: {path.ext}"
    if file_type == "extrudedPoints-pointsFile":
        try:
            _ = sirepo.csv.read_as_number_list(path)
        except RuntimeError as e:
            return e
    if p == ".stl":
        mesh = _create_stl_trimesh(path)
        if trimesh.convex.is_convex(mesh) == False:
            return f"not convex model: {path.basename}"
        elif len(mesh.faces) > 600:
            return f"too many faces({len(mesh.faces)}): {path.basename}"
    return None


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data, is_parallel, run_dir=run_dir, qcall=None),
    )
    if is_parallel:
        return template_common.get_exec_parameters_cmd(
            is_mpi=data.report not in ("optimizerAnimation",)
        )
    return None


def _add_obj_lines(field_data, obj):
    for d in obj.data:
        field_data.data.append(PKDict(lines=d.lines))


def _backend_alert(sim_id, g_id, e):
    raise sirepo.util.UserAlert(
        "backend Radia runtime error={} in simulation={} for key={}".format(
            e, sim_id, g_id
        )
    )


def _build_clone_xform(num_copies, alt_fields, transforms):
    tx = _build_geom_obj("cloneTransform")
    tx.numCopies = num_copies
    tx.alternateFields = alt_fields
    tx.transforms = transforms
    return tx


def _build_dipole_objects(geom_objs, model, **kwargs):
    geom_objs.append(model.pole)
    if model.dipoleType in ["dipoleC", "dipoleH"]:
        geom_objs.append(model.magnet)
        geom_objs.append(model.coil)
        g = _update_group(
            model.corePoleGroup, [model.magnet, model.pole], do_replace=True
        )
        geom_objs.append(g)
        geom_objs.append(
            _update_group(model.magnetCoilGroup, [g, model.coil], do_replace=True)
        )

    return _update_geom_from_dipole(geom_objs, model, **kwargs)


def _build_field_axis(length, axis):
    beam_dir = radia_util.AXIS_VECTORS[axis]
    f = PKDict(
        begin=((-length / 2) * beam_dir).tolist(),
        end=((length / 2) * beam_dir).tolist(),
        name=f"{axis.upper()}-Axis",
        numPoints=round(length / 2) + 1,
        start=-length / 2,
        stop=length / 2,
    )
    _SIM_DATA.update_model_defaults(f, "linePath")
    return f


# have to include points for file type?
def _build_field_file_pts(f_path):
    pts_file = _SIM_DATA.lib_file_abspath(
        _SIM_DATA.lib_file_name_with_type(
            f_path.fileName, SCHEMA.constants.fileTypePathPts
        )
    )
    lines = [float(l.strip()) for l in pkio.read_text(pts_file).split(",")]
    if len(lines) % 3 != 0:
        raise ValueError("Invalid file data {}".format(f_path.file_data))
    return lines


def _build_field_points(paths):
    res = []
    for p in paths:
        res.extend(_FIELD_PT_BUILDERS[p.type](p))
    return res


def _build_field_line_pts(f_path):
    p1 = list(f_path.begin)
    p2 = list(f_path.end)
    res = p1
    r = range(len(p1))
    n = int(f_path.numPoints) - 1
    for i in range(1, n):
        res.extend([p1[j] + i * (p2[j] - p1[j]) / n for j in r])
    res.extend(p2)
    return res


def _build_field_manual_pts(f_path):
    return [float(f_path.ptX), float(f_path.ptY), float(f_path.ptZ)]


def _build_field_map_pts(f_path):
    res = []
    n = int(f_path.numPoints)
    dx, dy, dz = (
        f_path.size[0] / (n - 1),
        f_path.size[1] / (n - 1),
        f_path.size[2] / (n - 1),
    )
    for i in range(n):
        x = f_path.center[0] - 0.5 * f_path.size[0] + i * dx
        for j in range(n):
            y = f_path.center[1] - 0.5 * f_path.size[1] + j * dy
            for k in range(n):
                z = f_path.center[2] - 0.5 * f_path.size[2] + k * dz
                res.extend([x, y, z])
    return res


def _build_field_circle_pts(f_path):
    ctr = f_path.center
    r = float(f_path.radius)
    # theta is a rotation about the x-axis
    th = float(f_path.eulers[0])
    # phi is a rotation about the z-axis
    phi = float(f_path.eulers[1])
    n = int(f_path.numPoints)
    dpsi = 2.0 * math.pi / n
    # psi is the angle in the circle's plane
    res = []
    for i in range(0, n):
        psi = i * dpsi
        # initial position of the point...
        # a = [r * math.sin(psi), r * math.cos(psi), 0]
        # ...rotate around x axis
        # a' = [
        #    a[0],
        #    a[1] * math.cos(th) - a[2] * math.sin(th),
        #    a[1] * math.sin(th) + a[2] * math.cos(th),
        # ]
        # ...rotate around z axis
        # a'' = [
        #    aa[0] * math.cos(phi) - aa[1] * math.cos(th),
        #    aa[0] * math.sin(phi) + aa[1] * math.cos(phi),
        #    aa[2]
        # ]
        # ...translate to final position
        # a''' = [
        #    ctr[0] + aaa[0],
        #    ctr[1] + aaa[1],
        #    ctr[2] + aaa[2],
        # ]
        # final position:
        res.extend(
            [
                r * math.sin(psi) * math.cos(phi)
                - r * math.cos(psi) * math.cos(th) * math.sin(phi)
                + ctr[0],
                r * math.sin(psi) * math.sin(phi)
                - r * math.cos(psi) * math.cos(th) * math.cos(phi)
                + ctr[1],
                r * math.cos(psi) * math.sin(th) + ctr[2],
            ]
        )
    return res


def _build_freehand_objects(geom, model, **kwargs):
    return geom


def _build_geom_obj(model_name, **kwargs):
    o = PKDict(
        model=model_name,
    )
    _SIM_DATA.update_model_defaults(o, model_name)
    o.pkupdate(kwargs)
    if not o.get("name"):
        o.name = f"{model_name}.{o.id}"
    return o


def _build_group(members, name=None):
    return _update_group(
        _build_geom_obj("geomGroup", name=name), members, do_replace=True
    )


def _build_symm_xform(plane, type, point=None):
    tx = _build_geom_obj("symmetryTransform")
    tx.symmetryPlane = plane.tolist()
    tx.symmetryPoint = point.tolist() if point else _ZERO
    tx.symmetryType = type
    return tx


def _build_translate_clone(dist):
    tx = _build_geom_obj("translateClone")
    tx.distance = dist.tolist()
    return tx


def _build_undulator_objects(geom_objs, model, **kwargs):
    geom_objs.append(model.magnet)

    oct_grp = []

    if model.undulatorType in ("undulatorBasic",):
        oct_grp.extend([model.magnet])

    if model.undulatorType in ("undulatorHybrid",):
        geom_objs.append(model.halfPole)
        geom_objs.append(model.pole)
        geom_objs.append(
            _update_group(
                model.corePoleGroup, [model.magnet, model.pole], do_replace=True
            )
        )
        t_grp = []
        for t in model.terminations:
            o = t.object
            _SIM_DATA.update_model_defaults(o, o.type)
            _update_geom_obj(
                o,
                size=radia_util.multiply_vector_by_matrix(
                    o.size,
                    kwargs["matrix"],
                ),
            )
            t_grp.append(o)
        geom_objs.extend(t_grp)
        geom_objs.append(_update_group(model.terminationGroup, t_grp, do_replace=True))
        oct_grp.extend([model.halfPole, model.corePoleGroup, model.terminationGroup])

    geom_objs.append(_update_group(model.octantGroup, oct_grp, do_replace=True))

    return _update_geom_from_undulator(geom_objs, model, **kwargs)


def _create_stl_trimesh(file_path):
    readParam = "r"
    keyType = "ascii"
    if _is_binary(file_path):
        readParam = "rb"
        keyType = "binary"
    with open(file_path, readParam) as f:
        m = trimesh.exchange.stl.load_stl(file_obj=f)
        if "geometry" in m:
            return trimesh.Trimesh(
                vertices=m["geometry"][keyType]["vertices"],
                faces=m["geometry"][keyType]["faces"],
                process=True,
            )
        return trimesh.Trimesh(vertices=m["vertices"], faces=m["faces"], process=True)


# deep copy of an object, but with a new id
def _copy_geom_obj(o):
    import copy

    o_copy = copy.deepcopy(o)
    o_copy.id = str(uuid.uuid4())
    return o_copy


def _extruded_points_plot(name, points, width_axis, height_axis):
    pts = numpy.array(points).T
    plots = PKDict(points=pts[1].tolist(), label=None, style="line")
    return template_common.parameter_plot(
        pts[0].tolist(),
        plots,
        PKDict(),
        PKDict(
            title=name,
            y_label=f"{width_axis} [mm]",
            x_label=f"{height_axis} [mm]",
            summaryData=PKDict(),
        ),
    )


_FIELD_PT_BUILDERS = {
    "axisPath": _build_field_line_pts,
    "circlePath": _build_field_circle_pts,
    "fieldMapPath": _build_field_map_pts,
    "filePath": _build_field_file_pts,
    "linePath": _build_field_line_pts,
    "manualPath": _build_field_manual_pts,
}


def _electron_trajectory_plot(sim_id, **kwargs):
    d = PKDict(kwargs)
    t = _generate_electron_trajectory(sim_id, get_g_id(), **kwargs)
    pts = (_MILLIS_TO_METERS * t[radia_util.axes_index(d.beam_axis)]).tolist()
    plots = []
    a = [d.width_axis, d.height_axis]
    for i in range(2):
        plots.append(
            PKDict(
                points=(_MILLIS_TO_METERS * t[radia_util.axes_index(a[i])]).tolist(),
                label=f"{a[i]}",
                style="line",
            )
        )

    return template_common.parameter_plot(
        pts,
        plots,
        PKDict(),
        PKDict(
            title=f"{d.energy} GeV",
            y_label="Position [m]",
            x_label=f"{d.beam_axis} [m]",
            summaryData=PKDict(),
        ),
    )


def _evaluate_var(var, code_variable):
    e = code_variable.eval_var(var)
    if e[1] is not None:
        raise RuntimeError("Error evaluating field: {}: {}".format(var, e[1]))
    return e[0]


def _evaluated_object(o, code_variable):
    c = copy.deepcopy(o)
    for f in _find_scriptables(c):
        c[f] = _evaluate_var(f"{c.name}.{f}", code_variable)
    return c


def _evaluate_objects(objs, vars, code_variable):
    for o in objs:
        for f in _find_scriptables(o):
            o[f] = _evaluate_var(f"{o.name}.{f}", code_variable)


def _export_rsopt_config(ctx, run_dir):

    for f in _export_rsopt_files().values():
        pkio.write_text(
            run_dir.join(f),
            template_common.render_jinja(SIM_TYPE, ctx, f),
        )


def _export_rsopt_files():
    files = PKDict()
    for t in (
        "py",
        "sh",
        "yml",
    ):
        files[f"{t}FileName"] = f"optimize.{t}"
    return files


def _extract_optimization_results(args):
    def nat_order(path):
        import pathlib

        return [
            int(c) if c.isdigit() else c
            for c in re.split(r"(\d+)", pathlib.PurePath(path).parent.name)
        ]

    plots = []
    objective_vals = []
    params = PKDict()
    summaryData = PKDict()
    out_files = sorted(
        pkio.walk_tree(args.run_dir, _RSOPT_OBJECTIVE_FUNCTION_OUT), key=nat_order
    )
    for f in out_files:
        with h5py.File(f, "r") as h:
            d = template_common.h5_to_dict(h)
            objective_vals.append(d.val)
            for k, v in d.parameters.items():
                if k not in params:
                    params[k] = []
                params[k].append(v)
                summaryData[k] = v
    plots.append(
        PKDict(
            points=objective_vals,
            label="Objective function results",
            style="line",
        )
    )
    for k, v in params.items():
        plots.append(
            PKDict(
                points=v,
                label=k,
                style="line",
            )
        )
    return template_common.parameter_plot(
        numpy.arange(1, len(out_files) + 1).tolist(),
        plots,
        PKDict(),
        PKDict(
            title="Optimization Output",
            y_label="Result",
            x_label=f"Run",
            summaryData=summaryData,
        ),
    )


def _field_lineout_plot(sim_id, name, f_type, f_path, plot_axis, field_data=None):
    v = (
        field_data
        if field_data
        else (
            generate_field_data(sim_id, get_g_id(), name, f_type, [f_path])
            .data[0]
            .vectors
        )
    )
    pts = _MILLIS_TO_METERS * numpy.array(v.vertices).reshape(-1, 3)
    plots = []
    f = numpy.array(v.directions).reshape(-1, 3)
    m = numpy.array(v.magnitudes)

    for i, c in enumerate(radia_util.AXES):
        plots.append(
            PKDict(
                points=(m * f[:, i]).tolist(),
                label=f"{f_type}_{c} [{radia_util.FIELD_UNITS[f_type]}]",
                style="line",
            )
        )
    return template_common.parameter_plot(
        pts[:, radia_util.axes_index(plot_axis)].tolist(),
        plots,
        PKDict(),
        PKDict(
            title=f"{f_type} on {f_path.name}",
            y_label=f_type,
            x_label=f"{plot_axis} [m]",
            summaryData=PKDict(),
        ),
    )


def _find_by_id(arr, obj_id):
    return sirepo.util.find_obj(arr, "id", obj_id)


def _find_scriptables(model):
    m = SCHEMA.model[model.type]
    return [f for f in m if "Scriptable" in m[f][1]]


def _fit_poles_in_c_bend(**kwargs):
    d = PKDict(kwargs)
    s = (
        d.mag_sz * d.length_dir
        + d.pole_width * d.width_dir
        + d.mag_sz * d.height_dir / 2
        - d.arm_height * d.height_dir
        - d.gap * d.height_dir / 2
    )
    c = s * d.height_dir / 2 + d.gap * d.height_dir / 2
    return s, c


def _fit_poles_in_h_bend(**kwargs):
    d = PKDict(kwargs)
    s = (
        d.mag_sz * d.length_dir
        + d.pole_width * d.width_dir / 2
        + d.mag_sz * d.height_dir
        - d.arm_height * d.height_dir
        - d.gap * d.height_dir / 2
    )
    c = (
        s * d.height_dir / 2
        + d.gap * d.height_dir / 2
        + s * d.length_dir / 2
        + s * d.width_dir / 2
    )
    return s, c


def _generate_electron_trajectory(sim_id, g_id, **kwargs):
    try:
        return radia_util.get_electron_trajectory(g_id, **kwargs)
    except RuntimeError as e:
        _backend_alert(sim_id, g_id, e)


def _generate_field_integrals(sim_id, g_id, f_paths):
    l_paths = [fp for fp in f_paths if fp.type in ("linePath", "axisPath")]
    if len(l_paths) == 0:
        # return something or server.py will raise an exception
        return PKDict(warning="No paths")
    try:
        res = PKDict(x_range=[])
        for p in l_paths:
            res[p.name] = PKDict()
            p1 = p.begin
            p2 = p.end
            for i_type in radia_util.INTEGRABLE_FIELD_TYPES:
                res[p.name][i_type] = radia_util.field_integral(g_id, i_type, p1, p2)
        return res
    except RuntimeError as e:
        _backend_alert(sim_id, g_id, e)


def _generate_data(sim_id, g_id, name, view_type, field_type, field_paths=None):
    try:
        o = _generate_obj_data(g_id, name)
        if view_type == SCHEMA.constants.viewTypeObjects:
            return o
        elif view_type == SCHEMA.constants.viewTypeFields:
            g = generate_field_data(sim_id, g_id, name, field_type, field_paths)
            _add_obj_lines(g, o)
            return g
    except RuntimeError as e:
        _backend_alert(sim_id, g_id, e)


def _generate_kick_map(g_id, model):
    km = radia_util.kick_map(
        g_id,
        model.begin,
        model.direction,
        int(model.numPeriods),
        float(model.periodLength),
        model.transverseDirection,
        float(model.transverseRange1),
        int(model.numTransPoints1),
        float(model.transverseRange2),
        int(model.numTransPoints2),
    )
    return PKDict(h=km[0], v=km[1], lmsqr=km[2], x=km[3], y=km[4])


def _generate_obj_data(g_id, name):
    return radia_util.geom_to_data(g_id, name=name)


def _generate_parameters_file(data, is_parallel, qcall, for_export=False, run_dir=None):
    import jinja2

    report = data.get("report", "")
    rpt_out = f"{_REPORT_RES_MAP.get(report, report)}"
    res, v = template_common.generate_parameters_file(data)
    if report == "fieldLineoutAnimation":
        v.beam_axis = data.models.simulation.beamAxis
        v.f_type = data.models.fieldLineoutAnimation.fieldType
        v.f_path = data.models.fieldLineoutAnimation.fieldPath
        v.gap = data.models[data.models.simulation.undulatorType].gap
        v.name = data.models.simulation.name
        v.sim_id = data.models.simulation.simulationId
        return template_common.render_jinja(
            SIM_TYPE,
            v,
            f"{rpt_out}.py",
            jinja_env=PKDict(loader=jinja2.PackageLoader("sirepo", "template")),
        )

    if rpt_out in _POST_SIM_REPORTS:
        return res

    g = data.models.geometryReport
    v.simId = data.models.simulation.simulationId

    if report == "optimizerAnimation":
        v.solverMode = "solve"
    elif report == "solverAnimation":
        v.solverMode = data.models.solverAnimation.get("mode")
    elif for_export:
        v.solverMode = "solve"
    do_generate = _normalize_bool(g.get("doGenerate", True)) or v.get("solverMode")
    if not do_generate:
        try:
            # use the previous results
            _SIM_DATA.sim_files_to_run_dir(data, run_dir, post_init=True)
        except Exception as e:
            if not pkio.exception_is_not_found(e):
                raise
            do_generate = True

    if not do_generate:
        return res

    # ensure old files are gone
    for f in _SIM_FILES:
        pkio.unchecked_remove(f)

    v.isParallel = is_parallel

    # include methods from non-template packages
    if for_export:
        pass

    v.dmpOutputFile = _DMP_FILE
    if "dmpImportFile" in data.models.simulation:
        v.dmpImportFile = (
            data.models.simulation.dmpImportFile
            if for_export
            else simulation_db.simulation_lib_dir(SIM_TYPE, qcall=qcall).join(
                f"{SCHEMA.constants.fileTypeRadiaDmp}.{data.models.simulation.dmpImportFile}"
            )
        )
    v.isExample = data.models.simulation.get("isExample", False)
    v.magnetType = data.models.simulation.get("magnetType", "freehand")
    dirs = _geom_directions(
        data.models.simulation.beamAxis, data.models.simulation.heightAxis
    )
    v.matrix = _get_coord_matrix(dirs, data.models.simulation.coordinateSystem)
    st = f"{v.magnetType}Type"
    v[st] = data.models.simulation[st]
    v.objects = g.get("objects", [])
    if data.models.get("rpnVariables"):
        _evaluate_objects(
            v.objects, data.models.rpnVariables, code_var(data.models.rpnVariables)
        )
    pkinspect.module_functions("_update_geom_from_")[
        f"_update_geom_from_{v.magnetType}"
    ](
        v.objects,
        data.models[v[st]],
        height_dir=dirs.height_dir,
        length_dir=dirs.length_dir,
        width_dir=dirs.width_dir,
        qcall=qcall,
    )
    _validate_objects(v.objects)

    for o in v.objects:
        if o.get("type"):
            o.super_classes = SCHEMA.model[o.type]._super
    v.geomName = g.name
    disp = data.models.magnetDisplay
    v_type = disp.viewType

    # for rendering conveneince
    v.VIEW_TYPE_OBJ = SCHEMA.constants.viewTypeObjects
    v.VIEW_TYPE_FIELD = SCHEMA.constants.viewTypeFields
    v.FIELD_TYPE_MAG_M = radia_util.FIELD_TYPE_MAG_M
    v.POINT_FIELD_TYPES = radia_util.POINT_FIELD_TYPES
    v.INTEGRABLE_FIELD_TYPES = radia_util.INTEGRABLE_FIELD_TYPES

    f_type = None
    if v_type not in VIEW_TYPES:
        raise ValueError("Invalid view {} ({})".format(v_type, VIEW_TYPES))
    v.viewType = v_type
    v.dataFile = _GEOM_FILE if for_export else f"{rpt_out}.h5"
    if v_type == SCHEMA.constants.viewTypeFields or for_export:
        f_type = disp.fieldType
        if f_type not in radia_util.FIELD_TYPES:
            raise ValueError(
                "Invalid field {} ({})".format(f_type, radia_util.FIELD_TYPES)
            )
        v.fieldType = f_type
        v.fieldPaths = data.models.fieldPaths.get("paths", [])
        v.fieldPoints = _build_field_points(data.models.fieldPaths.get("paths", []))
    v.kickMap = data.models.get("kickMapReport")
    if v.get("solverMode") == "solve":
        s = data.models.solverAnimation
        v.solvePrec = s.precision
        v.solveMaxIter = s.maxIterations
        v.solveMethod = s.method
    v.h5FieldPath = _geom_h5_path(SCHEMA.constants.viewTypeFields, f_type)
    v.h5KickMapPath = _H5_PATH_KICK_MAP
    v.h5ObjPath = _geom_h5_path(SCHEMA.constants.viewTypeObjects)
    v.h5SolutionPath = _H5_PATH_SOLUTION
    v.h5IdMapPath = _H5_PATH_ID_MAP

    if report == "optimizerAnimation":
        rx = _rsopt_jinja_context(data)
        rx.update(v)
        _export_rsopt_config(rx, run_dir=run_dir)
        return f"""import subprocess
subprocess.call(['bash', 'optimize.sh'])
"""
    h = (
        template_common.render_jinja(
            SIM_TYPE,
            v,
            _HEADER_FILE,
            jinja_env=PKDict(loader=jinja2.PackageLoader("sirepo", "template")),
        )
        if for_export or rpt_out in _SIM_REPORTS
        else ""
    )

    j_file = RADIA_EXPORT_FILE if for_export else f"{rpt_out}.py"
    return h + template_common.render_jinja(
        SIM_TYPE,
        v,
        j_file,
        jinja_env=PKDict(loader=jinja2.PackageLoader("sirepo", "template")),
    )


# "Length" is along the beam axis; "Height" is along the gap axis; "Width" is
# along the remaining axis
def _geom_directions(beam_axis, height_axis):
    beam_dir = radia_util.AXIS_VECTORS[beam_axis]
    if not height_axis or height_axis == beam_axis:
        height_axis = SCHEMA.constants.heightAxisMap[beam_axis]
    height_dir = radia_util.AXIS_VECTORS[height_axis]

    # we don't care about the direction of the cross product
    return PKDict(
        length_dir=beam_dir,
        height_dir=height_dir,
        width_dir=abs(numpy.cross(beam_dir, height_dir)),
    )


def _geom_h5_path(view_type, field_type=None):
    p = f"geometry/{view_type}"
    if field_type is not None:
        p += f"/{field_type}"
    return p


def _get_cee_points(o, stemmed_info):
    p = stemmed_info.points
    sy2 = p.sy1 + o.armHeight
    return _orient_stemmed_points(
        o,
        [
            [p.ax1, p.ay1],
            [p.ax2, p.ay1],
            [p.ax2, p.ay2],
            [p.sx2, p.ay2],
            [p.sx2, sy2],
            [p.ax2, sy2],
            [p.ax2, p.sy1],
            [p.sx1, p.sy1],
        ],
        stemmed_info.plane_ctr,
    )


def _get_coord_matrix(dirs, coords_type):
    i = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    return PKDict(
        beam=[
            dirs.width_dir.tolist(),
            dirs.height_dir.tolist(),
            dirs.length_dir.tolist(),
        ],
        standard=i,
    ).get(coords_type, i)


def _get_ell_points(o, stemmed_info):
    p = stemmed_info.points
    return _orient_stemmed_points(
        o,
        [
            [p.ax1, p.ay1],
            [p.ax2, p.ay1],
            [p.ax2, p.ay2],
            [p.sx2, p.ay2],
            [p.sx2, p.sy1],
            [p.sx1, p.sy1],
        ],
        stemmed_info.plane_ctr,
    )


def _get_geom_data(
    sim_id,
    g_id,
    name,
    view_type,
    field_type,
    field_paths=None,
    geom_types=[SCHEMA.constants.geomTypeLines, SCHEMA.constants.geomTypePolys],
):
    assert view_type in VIEW_TYPES, "view_type={}: invalid view type".format(view_type)
    if view_type == SCHEMA.constants.viewTypeFields:
        res = generate_field_data(sim_id, g_id, name, field_type, field_paths)
        res.data += _get_geom_data(
            sim_id,
            g_id,
            name,
            SCHEMA.constants.viewTypeObjects,
            None,
            geom_types=[SCHEMA.constants.geomTypeLines],
        ).data
        return res

    geom_types.extend(["center", "name", "size", "id"])
    res = _read_or_generate(sim_id, g_id, name, view_type, None)
    rd = res.data if "data" in res else []
    res.data = [{k: d[k] for k in d.keys() if k in geom_types} for d in rd]
    res.idMap = _read_id_map()
    res.solution = _read_solution()
    return res


def _get_jay_points(o, stemmed_info):
    p = stemmed_info.points
    jx1 = stemmed_info.plane_ctr[0] + stemmed_info.plane_size[0] / 2 - o.hookWidth
    jy1 = p.ay2 - o.hookHeight

    return _orient_stemmed_points(
        o,
        [
            [p.ax1, p.ay1],
            [p.ax2, p.ay1],
            [p.ax2, jy1],
            [jx1, jy1],
            [jx1, p.ay2],
            [p.sx2, p.ay2],
            [p.sx2, p.sy1],
            [p.sx1, p.sy1],
        ],
        stemmed_info.plane_ctr,
    )


def _get_radia_objects(geom_objs, model):
    o = PKDict(groupedObjects=PKDict())
    o_ids = []
    for f in model:
        try:
            if "_super" not in model[f]:
                continue
            s = model[f]._super
            if "radiaObject" in s or "radiaObject" in SCHEMA.model[s]._super:
                o[f] = _find_by_id(geom_objs, model[f].id)
                o_ids.append(model[f].id)
        # ignore non-objects
        except TypeError:
            pass
    for f in o:
        if o[f].get("model") == "geomGroup":
            o.groupedObjects[f] = [
                _find_by_id(geom_objs, m_id)
                for m_id in o[f].members
                if m_id not in o_ids
            ]
    return o


def _get_sdds(cols, units):
    if _cfg.sdds is None:
        _cfg.sdds = sdds.SDDS(_SDDS_INDEX)
        # TODO(mvk): elegant cannot read these binary files; figure that out
        # _cfg.sdds = sd.SDDS_BINARY
        for i, n in enumerate(cols):
            # name, symbol, units, desc, format, type, len)
            _cfg.sdds.defineColumn(n, "", units[i], n, "", _cfg.sdds.SDDS_DOUBLE, 0)
    return _cfg.sdds


def _is_binary(file_path):
    return bool(
        open(file_path, "rb")
        .read(1024)
        .translate(
            None,
            bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F}),
        )
    )


def _kick_map_plot(model):
    from sirepo import srschema

    g_id = get_g_id()
    component = model.component
    km = _generate_kick_map(g_id, model)
    if not km:
        return None
    z = km[component]
    return PKDict(
        title=f'{srschema.get_enums(SCHEMA, "KickMapComponent")[component]} (T2m2)',
        x_range=[_MILLIS_TO_METERS * km.x[0], _MILLIS_TO_METERS * km.x[-1], len(z)],
        y_range=[_MILLIS_TO_METERS * km.y[0], _MILLIS_TO_METERS * km.y[-1], len(z[0])],
        x_label="x [m]",
        y_label="y [m]",
        z_matrix=z,
    )


def _normalize_bool(x):
    bool_map = {"1": True, "0": False}
    return bool_map[x] if x in bool_map else x


def _calculate_objective_def(models):
    o = models.optimizer
    t = o.objective
    if t == "custom":
        return o.code
    c = """def _calculate_objective(g_id):
"""
    if t == "objectiveFunctionQuality":
        q = models.objectiveFunctionQuality
        s = models.optimizationSoftwareDFOLS
        c = (
            c
            + f"""
    import numpy

    f = numpy.array([])
    p1 = {q.begin}
    p2 = {q.end}
    c = 'B{q.component}'
    f0 = radia_util.field_integral(g_id, c, p1, p2)
    for d in numpy.linspace(-1 * numpy.array({q.deviation}), 1 * numpy.array({q.deviation}), {s.components}):
        f = numpy.append(f, radia_util.field_integral(g_id, c, (p1 + d).tolist(), (p2 + d).tolist()))
    res = f - f0
    return numpy.sum(res**2), res.tolist()
"""
        )
    else:
        raise ValueError("objective_functon={}: unknown function".format(t))
    return c


def _orient_stemmed_points(o, points, plane_ctr):
    idx = [int(o.stemPosition), int(o.armPosition)]
    return [
        [2 * plane_ctr[i] * idx[i] + (-1) ** idx[i] * v for (i, v) in enumerate(p)]
        for p in points
    ]


def _prep_new_sim(data, new_sim_data=None):
    def _electron_initial_pos(axis, factor):
        return factor * radia_util.AXIS_VECTORS[axis]

    data.models.geometryReport.name = data.models.simulation.name
    if new_sim_data is None:
        return
    sim = data.models.simulation
    if new_sim_data.get("dmpImportFile"):
        sim.appMode = "imported"
    sim.beamAxis = new_sim_data.beamAxis
    sim.enableKickMaps = new_sim_data.enableKickMaps
    t = new_sim_data.get("magnetType", "freehand")
    s = new_sim_data[f"{t}Type"]
    m = data.models[s]
    sim.notes = _MAGNET_NOTES[t][s]
    data.models.electronTrajectoryReport.initialPosition = _electron_initial_pos(
        new_sim_data.beamAxis,
        -1.0,
    ).tolist()
    data.models.fieldLineoutAnimation.plotAxis = new_sim_data.beamAxis
    if t != "undulator":
        return
    sim.coordinateSystem = "beam"
    if s == "undulatorBasic":
        data.models.geometryReport.isSolvable = "0"
    f = (m.numPeriods + 0.5) * m.periodLength
    data.models.fieldPaths.paths.append(_build_field_axis(3 * f, new_sim_data.beamAxis))
    data.models.electronTrajectoryReport.initialPosition = _electron_initial_pos(
        new_sim_data.beamAxis,
        -f,
    ).tolist()
    data.models.electronTrajectoryReport.finalBeamPosition = f
    sim.enableKickMaps = "1"
    _update_kickmap(data.models.kickMapReport, m, new_sim_data.beamAxis)


def _read_data(view_type, field_type):
    res = _read_h5_path(_GEOM_FILE, _geom_h5_path(view_type, field_type))
    if res:
        res.idMap = _read_id_map()
        res.solution = _read_solution()
    return res


def _read_h5_path(filename, h5path):
    try:
        with h5py.File(filename, "r") as f:
            return template_common.h5_to_dict(f, path=h5path)
    except IOError as e:
        if pkio.exception_is_not_found(e):
            pkdlog("filename={} not found", filename)
            # need to generate file
            return None
    except template_common.NoH5PathError:
        # no such path in file
        pkdlog("h5Path={} not found in filename={}", h5path, filename)
        return None
    # propagate other errors


def _read_h_m_file(file_name, qcall=None):
    return sirepo.csv.read_as_number_list(
        _SIM_DATA.lib_file_abspath(
            _SIM_DATA.lib_file_name_with_type(file_name, SCHEMA.constants.fileTypeHM),
            qcall=qcall,
        )
    )


def _read_id_map():
    m = _read_h5_path(_GEOM_FILE, _H5_PATH_ID_MAP)
    return (
        PKDict()
        if not m
        else PKDict(
            {
                k: (v if isinstance(v, int) else pkcompat.from_bytes(v))
                for k, v in m.items()
            }
        )
    )


def _read_kick_map():
    return _read_h5_path(_KICK_FILE, _H5_PATH_KICK_MAP)


def _read_or_generate(sim_id, g_id, name, view_type, field_type, field_paths=None):
    res = _read_data(view_type, field_type)
    if res:
        return res
    # No such file or path, so generate the data and write to the existing file
    template_common.write_dict_to_h5(
        _generate_data(sim_id, g_id, name, view_type, field_type, field_paths),
        _GEOM_FILE,
        h5_path=_geom_h5_path(view_type, field_type),
    )
    return _get_geom_data(sim_id, g_id, name, view_type, field_type, field_paths)


def _read_or_generate_kick_map(g_id, data):
    res = _read_kick_map()
    if res:
        return res
    return _generate_kick_map(g_id, data)


def _read_solution():
    s = _read_h5_path(
        _GEOM_FILE,
        _H5_PATH_SOLUTION,
    )
    if not s:
        return None
    return PKDict(steps=s[3], time=s[0], maxM=s[1], maxH=s[2])


def _read_stl_file(file_name, qcall=None):
    path = str(
        _SIM_DATA.lib_file_abspath(
            _SIM_DATA.lib_file_name_with_type(file_name, SCHEMA.constants.fileTypeSTL),
            qcall=qcall,
        )
    )
    return _create_stl_trimesh(path)


def _rotate_axis(to_axis="z", from_axis="x"):
    return _AXIS_ROTATIONS[to_axis][from_axis]


# mm -> m, rotate so the beam axis is aligned with z
def _rotate_fields(vectors, scipy_rotation, do_flatten):
    pts = _MILLIS_TO_METERS * _rotate_flat_vector_list(vectors.vertices, scipy_rotation)
    mags = numpy.array(vectors.magnitudes)
    dirs = _rotate_flat_vector_list(vectors.directions, scipy_rotation)
    if do_flatten:
        dirs = dirs.flatten()
        pts = pts.flatten()
    return pts, mags, dirs


def _rotate_flat_vector_list(vectors, scipy_rotation):
    return scipy_rotation.apply(numpy.reshape(vectors, (-1, 3)))


def _rsopt_percent_complete(run_dir, res):
    def _scan_stats(search_re):
        for line in pkio.read_text("libE_stats.txt").split("\n"):
            m = re.match(search_re, line, re.IGNORECASE)
            if m:
                return m
        return None

    res.frameCount = 0
    res.percentComplete = 0
    out_files = pkio.walk_tree(run_dir, _RSOPT_OBJECTIVE_FUNCTION_OUT)
    if not out_files:
        return res
    count = len(out_files)
    dm = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME)).models
    res.frameCount = count
    p = count / dm.optimizer.maxIterations
    # errors that allow completion
    if pkio.sorted_glob("H_*.npy"):
        p = 1
        m = _scan_stats(r"Worker\s*(\d+):\s+sim_id\s*(\d+).*Status:\s*Task Failed")
        if m:
            p = 0
            res.state = "error"
            res.error = (
                f"Error during optimization: worker {m.group(1)} sim id {m.group(2)}"
            )
    # errors that interrupt
    else:
        m = _scan_stats(
            r"Worker\s*(\d+):\s+Gen no\s*(\d+).*Status:\s*Exception occurred"
        )
        if m:
            p = 0
            res.state = "error"
            res.error = (
                f"Error during optimization: worker {m.group(1)} gen no {m.group(2)}"
            )
    res.percentComplete = 100 * p
    return res


def _rsopt_jinja_context(data):
    import multiprocessing

    res = PKDict(
        errFileName="optimize.err",
        libFiles=_SIM_DATA.lib_file_basenames(data),
        numWorkers=max(1, multiprocessing.cpu_count() - 1),
        optimizer=data.models.optimizer,
        objectiveFunctionDef=_calculate_objective_def(data.models),
        outFileName="optimize.out",
        objectiveFunctionResultsFileName=_RSOPT_OBJECTIVE_FUNCTION_OUT,
    )
    m = data.models.get(res.optimizer.software.type, {})
    for k in m:
        res.optimizer.software[k] = m[k]
    res.update(_export_rsopt_files())
    return res


def _save_field_csv(field_type, vectors, scipy_rotation, path):
    # reserve first line for a header
    data = [f"x,y,z,{field_type}x,{field_type}y,{field_type}z"]
    pts, mags, dirs = _rotate_fields(vectors, scipy_rotation, True)
    for i in range(len(mags)):
        j = 3 * i
        r = pts[j : j + 3]
        r = numpy.append(r, mags[i] * dirs[j : j + 3])
        data.append(",".join(map(str, r)))
    return pkio.write_text(path, "\n".join(data))


# zip file - data plus index.  This will likely be used to generate files for a range
# of gaps later
def _save_field_srw(gap, vectors, scipy_rotation, path):
    # no whitespace in filenames
    base_name = re.sub(r"\s", "_", path.purebasename)
    data_path = path.dirpath().join(f"{base_name}_{gap}.dat")
    index_path = path.dirpath().join(f"{base_name}_sum.txt")
    pkio.unchecked_remove(path, data_path, index_path)

    data = [
        "#Bx [T], By [T], Bz [T] on 3D mesh: inmost loop vs X (horizontal transverse position), outmost loop vs Z (longitudinal position)"
    ]
    pts, mags, dirs = _rotate_fields(vectors, scipy_rotation, True)
    num_pts = len(pts) // 3
    dims = ["X", "Y", "Z"]
    for j in range(len(dims)):
        data.append(f"#{pts[j]} #initial {dims[j]} position [m]")
        data.append(
            f"#{(pts[len(pts) - (len(dims) - j)] - pts[j]) / num_pts} #step of {dims[j]} [m]"
        )
        data.append(
            f"#{num_pts if j == len(dims) - 1 else 1} #number of points vs {dims[j]}"
        )
    for i in range(len(mags)):
        j = 3 * i
        data.append("\t".join(map(str, mags[i] * dirs[j : j + 3])))
    pkio.write_text(data_path, "\n".join(data))

    # index file
    data = [f"{gap}\tp1\t0\t{data_path.basename}\t1\t1"]
    pkio.write_text(index_path, "\n".join(data))

    files = [data_path, index_path]

    # zip file
    with sirepo.util.write_zip(str(path)) as z:
        for f in files:
            z.write(str(f), f.basename)

    return path


def _save_fm_sdds(name, vectors, scipy_rotation, path):
    s = _get_sdds(_FIELD_MAP_COLS, _FIELD_MAP_UNITS)
    s.setDescription(f"Field Map for {name}", "x(m), y(m), z(m), Bx(T), By(T), Bz(T)")
    pts, mags, dirs = _rotate_fields(vectors, scipy_rotation, False)
    ind = numpy.lexsort((pts[:, 0], pts[:, 1], pts[:, 2]))
    pts = pts[ind]
    v = [mags[j // 3] * d for (j, d) in enumerate(dirs)]
    fld = numpy.reshape(v, (-1, 3))[ind]
    col_data = []
    for i in range(3):
        col_data.append([pts[:, i].tolist()])
    for i in range(3):
        col_data.append([fld[:, i].tolist()])
    for i, n in enumerate(_FIELD_MAP_COLS):
        s.setColumnValueLists(n, col_data[i])
    s.save(str(path))
    return path


def _save_field_integrals_csv(integral_paths, integrals, file_path):
    with open(file_path, "w") as f:
        out = csv.writer(f)
        out.writerow(
            [
                "Path",
                "x0",
                "y0",
                "z0",
                "x1",
                "y1",
                "z1",
                "Bx",
                "By",
                "Bz",
                "Hx",
                "Hy",
                "Hz",
            ]
        )
        for p in [x for x in integral_paths if x.type in ("axisPath", "linePath")]:
            row = [p.name, *p.begin, *p.end]
            for t in ("B", "H"):
                row.extend(integrals[p.name][t])
            out.writerow(row)
    return file_path


def _save_kick_map_sdds(name, path, km_data):
    s = _get_sdds(_KICK_MAP_COLS, _KICK_MAP_UNITS)
    s.setDescription(f"Kick Map for {name}", "x(m), y(m), h(T2m2), v(T2m2)")
    col_data = [
        [
            numpy.tile(
                _MILLIS_TO_METERS * numpy.array(km_data.x), len(km_data.x)
            ).tolist()
        ],
        [
            numpy.repeat(
                _MILLIS_TO_METERS * numpy.array(km_data.y), len(km_data.y)
            ).tolist()
        ],
        [numpy.array(km_data.h).flatten().tolist()],
        [numpy.array(km_data.v).flatten().tolist()],
    ]
    for i, n in enumerate(_KICK_MAP_COLS):
        s.setColumnValueLists(n, col_data[i])
    s.save(str(path))
    return path


def _save_trajectory_csv(path, **kwargs):
    d = PKDict(kwargs)
    data = d.output
    with open(path, "w") as f:
        out = csv.writer(f)
        out.writerow([d.beam_axis] + [p.label for p in data.plots])
        out.writerows(
            numpy.array([data.x_points] + [p.points for p in data.plots]).T.tolist()
        )
    return path


# For consistency, always set the width and height axes of the extruded shape in
# permutation order based on the extrusion axis:
#   x -> (y, z), y -> (z, x), z -> (x, y)
def _update_extruded(o):
    o.widthAxis = radia_util.next_axis(o.extrusionAxis)
    o.heightAxis = radia_util.next_axis(o.widthAxis)

    # Radia's extrusion routine seems to involve rotations, one result being that
    # segmentation in the extrusion direction must be along 'x' regardless of the
    # actual direction
    o.segments = list(
        _AXES_UNIT + radia_util.AXIS_VECTORS.x * (o.extrusionAxisSegments - 1)
    )
    return o


def _update_dipoleBasic(model, assembly, qcall=None, **kwargs):
    d = PKDict(kwargs)
    sz = assembly.pole.size
    return _update_geom_obj(
        assembly.pole,
        size=sz,
        center=sz * d.height_dir / 2 + model.gap * d.height_dir / 2,
        transforms=[_build_symm_xform(d.height_dir, "parallel")],
        qcall=qcall,
    )


def _update_dipoleC(model, assembly, qcall=None, **kwargs):
    d = PKDict(kwargs)
    mag_sz = numpy.array(assembly.magnet.size)
    pole_sz, pole_ctr = _fit_poles_in_c_bend(
        arm_height=model.magnet.armHeight,
        gap=model.gap,
        mag_sz=mag_sz,
        pole_width=model.poleWidth,
        **kwargs,
    )
    mag_ctr = mag_sz * d.width_dir / 2 - pole_sz * d.width_dir / 2
    _update_geom_obj(
        assembly.pole,
        center=pole_ctr,
        size=pole_sz,
        transforms=[_build_symm_xform(d.height_dir, "parallel")],
        qcall=qcall,
    )
    _update_geom_obj(assembly.magnet, center=mag_ctr, qcall=qcall)
    _update_geom_obj(
        assembly.coil,
        center=mag_ctr
        + mag_sz * d.width_dir / 2
        - model.magnet.stemWidth * d.width_dir / 2,
        qcall=qcall,
    )
    return assembly.magnetCoilGroup


def _update_dipoleH(model, assembly, qcall=None, **kwargs):
    d = PKDict(kwargs)
    # magnetSize is for the entire magnet - split it here so we can apply symmetries
    mag_sz = numpy.array(model.magnetSize) / 2
    pole_sz, pole_ctr = _fit_poles_in_h_bend(
        arm_height=model.magnet.armHeight,
        gap=model.gap,
        mag_sz=mag_sz,
        pole_width=model.poleWidth,
        **kwargs,
    )
    _update_geom_obj(assembly.pole, center=pole_ctr, size=pole_sz, qcall=qcall)
    _update_geom_obj(assembly.coil, center=pole_ctr * d.height_dir, qcall=qcall)
    _update_geom_obj(assembly.magnet, size=mag_sz, center=mag_sz / 2, qcall=qcall)
    # length and width symmetries
    assembly.corePoleGroup.transforms = [
        _build_symm_xform(d.length_dir, "perpendicular"),
        _build_symm_xform(d.width_dir, "perpendicular"),
    ]
    # height symmetry
    assembly.magnetCoilGroup.transforms = [_build_symm_xform(d.height_dir, "parallel")]
    return assembly.magnetCoilGroup


def _update_geom_from_dipole(geom_objs, model, qcall=None, **kwargs):
    _update_geom_objects(geom_objs, qcall=qcall)
    return pkinspect.module_functions("_update_")[f"_update_{model.dipoleType}"](
        model, _get_radia_objects(geom_objs, model), **kwargs
    )


def _update_geom_from_freehand(geom_objs, model, qcall=None, **kwargs):
    _update_geom_objects(geom_objs, qcall=qcall)


def _update_geom_from_undulator(geom_objs, model, qcall=None, **kwargs):
    _update_geom_objects(geom_objs, qcall=qcall)
    return pkinspect.module_functions("_update_")[f"_update_{model.undulatorType}"](
        model, _get_radia_objects(geom_objs, model), qcall=qcall, **kwargs
    )


def _update_undulatorBasic(model, assembly, qcall=None, **kwargs):
    d = PKDict(kwargs)

    sz = numpy.array(model.magnet.size)

    sz = sz / 2 * d.width_dir + sz * d.height_dir + sz * d.length_dir
    _update_geom_obj(
        assembly.magnet,
        center=sz / 2 + model.gap / 2 * d.height_dir + model.airGap * d.length_dir / 2,
        size=sz,
        qcall=qcall,
    )

    assembly.magnet.transforms = (
        []
        if model.numPeriods < 2
        else [
            _build_clone_xform(
                model.numPeriods - 1,
                True,
                [
                    _build_translate_clone(
                        sz * d.length_dir + model.airGap * d.length_dir
                    )
                ],
            )
        ]
    )

    assembly.octantGroup.transforms = [
        _build_symm_xform(d.width_dir, "perpendicular"),
        _build_symm_xform(d.height_dir, "parallel"),
        _build_symm_xform(d.length_dir, "perpendicular"),
    ]
    return assembly.octantGroup


def _update_undulatorHybrid(model, assembly, qcall=None, **kwargs):
    d = PKDict(kwargs)

    pole_x = model.poleCrossSection
    mag_x = model.magnetCrossSection

    gap_half_height = model.gap / 2 * d.height_dir
    gap_offset = model.gapOffset * d.height_dir

    pos = 0
    sz = (
        pole_x[0] / 2 * d.width_dir
        + d.height_dir * pole_x[1]
        + model.poleLength / 2 * d.length_dir
    )

    for f in (
        "color",
        "material",
        "materialFile",
        "modifications",
        "remanentMag",
        "type",
        "segments",
    ):
        assembly.halfPole[f] = copy.deepcopy(assembly.pole[f])
    _update_geom_obj(
        assembly.halfPole, center=pos + sz / 2 + gap_half_height, size=sz, qcall=qcall
    )
    pos += sz * d.length_dir

    sz = (
        mag_x[0] / 2 * d.width_dir
        + mag_x[1] * d.height_dir
        + (model.periodLength / 2 - model.poleLength) * d.length_dir
    )
    _update_geom_obj(
        assembly.magnet,
        center=pos + sz / 2 + gap_half_height + gap_offset,
        size=sz,
        qcall=qcall,
    )
    pos += sz * d.length_dir

    sz = (
        pole_x[0] / 2 * d.width_dir
        + d.height_dir * pole_x[1]
        + model.poleLength * d.length_dir
    )
    _update_geom_obj(
        assembly.pole,
        center=pos + sz / 2 + gap_half_height,
        size=sz,
        qcall=qcall,
    )

    pos = (model.poleLength + model.numPeriods * model.periodLength) / 2 * d.length_dir
    for t in model.terminations:
        o = t.object
        m = assembly.groupedObjects.get("terminationGroup", [])
        sz = numpy.array(o.size)
        _update_geom_obj(
            _find_by_id(m, o.id),
            center=pos
            + sz / 2
            + t.airGap * d.length_dir
            + gap_half_height
            + t.gapOffset * d.height_dir,
            qcall=qcall,
        )
        pos += sz * d.length_dir + t.airGap * d.length_dir

    assembly.corePoleGroup.transforms = (
        []
        if model.numPeriods < 2
        else [
            _build_clone_xform(
                model.numPeriods - 1,
                True,
                [_build_translate_clone(model.periodLength / 2 * d.length_dir)],
            )
        ]
    )

    assembly.octantGroup.transforms = [
        _build_symm_xform(d.width_dir, "perpendicular"),
        _build_symm_xform(d.height_dir, "parallel"),
        _build_symm_xform(d.length_dir, "perpendicular"),
    ]
    return assembly.octantGroup


def _update_geom_objects(objects, qcall=None):
    for o in objects:
        _update_geom_obj(o, qcall=qcall)


def _update_geom_obj(o, qcall=None, **kwargs):
    # uses the "shoelace formula" to calculate the area of a polygon
    def _poly_area(pts):
        t = numpy.array(pts).T
        return 0.5 * numpy.abs(
            numpy.dot(t[0], numpy.roll(t[1], 1)) - numpy.dot(t[1], numpy.roll(t[0], 1))
        )

    d = PKDict(
        center=[0.0, 0.0, 0.0],
        magnetization=[0.0, 0.0, 0.0],
        segments=[1, 1, 1],
        size=[1.0, 1.0, 1.0],
        stlVertices=[],
        stlFaces=[],
        stlCentroid=[],
        # TODO(BG) Not implemented
        # stlSlices = [],
    )
    for k in d:
        v = kwargs.get(k)
        if k in o and v is None:
            continue
        if v is None:
            o[k] = d[k]
        else:
            # remove the key from kwargs so it doesn't conflict with the update
            o[k] = list(v)
            del kwargs[k]

    o.update(kwargs)
    if "type" not in o:
        return o
    s = SCHEMA.model[o.type]._super
    if "extrudedPoly" in s:
        _update_extruded(o)
    if "stemmed" in s:
        o.points = pkinspect.module_functions("_get_")[f"_get_{o.type}_points"](
            o, _get_stemmed_info(o)
        )
    if o.get("points"):
        o.area = _poly_area(o.points)
    if o.type == "stl":
        mesh = _read_stl_file(o.file, qcall=qcall)
        for v in list(mesh.vertices):
            d.stlVertices.append(list(v))
        for f in list(mesh.faces):
            d.stlFaces.append(list(f))
        o.stlVertices = d.stlVertices
        o.stlFaces = d.stlFaces
        o.stlBoundsCenter = list(
            mesh.bounding_box.bounds[0] + 0.5 * mesh.bounding_box.extents
        )
        o.size = list(mesh.bounding_box.primitive.extents)
        o.stlCentroid = mesh.centroid.tolist()

        # TODO(BG) Mesh slicing implementation, option for meshes with 400+ faces although will be approximation
        """
        z_extents = mesh.bounds[:,2]
        z_levels  = numpy.arange(*z_extents, step=1)
        meshSlices = trimesh.intersections.mesh_multiplane(mesh=mesh, plane_origin=mesh.bounds[0], plane_normal=[0,0,1], heights=z_levels)[0]
        formattedSlices = []
        index = 0
        for s in meshSlices:
            slicePoints = []
            for l in s:
                for p in l:
                    #Remove redundant points by rounding
                    p[0] = round(p[0],5)
                    p[1] = round(p[1],5)
                    if list(p) not in slicePoints:
                        slicePoints.append(list(p))
            formattedSlices.append([list(slicePoints), z_levels[index]])
            index += 1
        for s in formattedSlices:
            s[0] = sort_points_clockwise(s[0])
        o.stlSlices = formattedSlices
        """
    o.h_m_curve = (
        _read_h_m_file(o.materialFile, qcall=qcall)
        if o.get("material") == "custom" and o.get("materialFile")
        else None
    )
    return o


def _update_racetrack(o, **kwargs):
    return _update_geom_obj(o, **kwargs)


def _get_stemmed_info(o):
    w, h = radia_util.AXIS_VECTORS[o.widthAxis], radia_util.AXIS_VECTORS[o.heightAxis]
    c = o.center
    s = o.size

    plane_ctr = [numpy.sum(w * c), numpy.sum(h * c)]
    plane_size = [numpy.sum(w * s), numpy.sum(h * s)]

    # start with arm top, stem left - then reflect across centroid axes as needed
    ax1 = plane_ctr[0] - plane_size[0] / 2
    ax2 = ax1 + plane_size[0]
    ay1 = plane_ctr[1] + plane_size[1] / 2
    ay2 = ay1 - o.armHeight

    sx1 = plane_ctr[0] - plane_size[0] / 2
    sx2 = sx1 + o.stemWidth
    sy1 = plane_ctr[1] - plane_size[1] / 2

    return PKDict(
        plane_ctr=plane_ctr,
        plane_size=plane_size,
        points=PKDict(ax1=ax1, ax2=ax2, ay1=ay1, ay2=ay2, sx1=sx1, sx2=sx2, sy1=sy1),
    )


def _update_group(g, members, do_replace=False):
    if do_replace:
        g.members = []
    for m in members:
        m.groupId = g.id
        g.members.append(m.id)
    return g


def _update_kickmap(km, und, beam_axis):
    km.direction = radia_util.AXIS_VECTORS[beam_axis].tolist()
    km.transverseDirection = radia_util.AXIS_VECTORS[
        SCHEMA.constants.heightAxisMap[beam_axis]
    ].tolist()
    km.transverseRange1 = und.gap
    km.numPeriods = und.numPeriods
    km.periodLength = und.periodLength


# TODO(BG) Necessary helper function to implement object slicing with radia.radObjMltExtPgn()
# Edge Case: Need to remove linear points along same vecter before returning
"""
def _sort_points_clockwise(points):
    angles = []
    center = (sum([p[0] for p in points]) / len(points), sum([p[1] for p in points]) / len(points))
    for p in points:
        vector = [p[0] - center[0], p[1] - center[1]]
        vlength = math.sqrt(pow(vector[0], 2) + pow(vector[1], 2))
        if vlength == 0:
            angles.append(-numpy.pi)
        else:
            normalized = [vector[0] / vlength, vector[1] / vlength]
            angle = math.atan2(normalized[0], normalized[1])
            # function checks against x-positive, if negative angle add to 2pi for mirror
            if angle < 0:
                angle = 2 * numpy.pi + angle
            angles.append(angle)
    for i in range(len(angles)):
        angles[i] = [angles[i], points[i]]
    angles.sort()
    # might have to check by lengths as well if angles are the same
    return [x[1] for x in angels]
"""


def _validate_objects(objects):
    import numpy.linalg

    for o in objects:
        if "material" in o and o.material in SCHEMA.constants.anisotropicMaterials:
            if numpy.linalg.norm(o.magnetization) == 0:
                raise ValueError(
                    "name={}, : material={}: anisotropic material requires non-0 magnetization".format(
                        o.name, o.material
                    )
                )


_H5_PATH_ID_MAP = _geom_h5_path("idMap")
_H5_PATH_KICK_MAP = _geom_h5_path("kickMap")
_H5_PATH_SOLUTION = _geom_h5_path("solution")
