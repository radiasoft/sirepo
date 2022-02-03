# -*- coding: utf-8 -*-
u"""Radia execution template.

All Radia calls have to be done from here, NOT in jinja files, because otherwise the
Radia "instance" goes away and references no longer have any meaning.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcompat
from pykern import pkinspect
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp, pkdlog
from scipy.spatial.transform import Rotation
from sirepo import simulation_db
from sirepo.template import radia_examples
from sirepo.template import radia_util
from sirepo.template import template_common
import h5py
import math
import numpy
import re
import sdds
import sirepo.csv
import sirepo.sim_data
import sirepo.util
import uuid

_AXES_UNIT = [1, 1, 1]

_AXIS_ROTATIONS = PKDict(
    x=Rotation.from_matrix([[0, 0, 1], [0, 1, 0], [-1, 0, 0]]),
    y=Rotation.from_matrix([[1, 0, 0], [0, 0, -1], [0, 1, 0]]),
    z=Rotation.from_matrix([[1, 0, 0], [0, 1, 0], [0, 0, 1]]),
)

_DIPOLE_NOTES = PKDict(
    dipoleBasic='Simple dipole with permanent magnets',
    dipoleC='C-bend dipole with a single coil',
    dipoleH='H-bend dipole with two coils',
)

_DMP_FILE = 'geometry.dat'

_FREEHAND_NOTES = PKDict(
    freehand='',
)

_UNDULATOR_NOTES = PKDict(
    undulatorBasic='Simple undulator with permanent magnets',
    undulatorHybrid='Undulator with alternating permanent magnets and susceptible poles',
)

_MAGNET_NOTES = PKDict(
    dipole=_DIPOLE_NOTES,
    freehand=_FREEHAND_NOTES,
    undulator=_UNDULATOR_NOTES,
)

# Note that these column names and units are required by elegant
_FIELD_MAP_COLS = ['x', 'y', 'z', 'Bx', 'By', 'Bz']
_FIELD_MAP_UNITS = ['m', 'm', 'm', 'T', 'T', 'T']
_KICK_MAP_COLS = ['x', 'y', 'xpFactor', 'ypFactor']
_KICK_MAP_UNITS = ['m', 'm', '(T*m)$a2$n', '(T*m)$a2$n']
_GEOM_DIR = 'geometryReport'
_GEOM_FILE = 'geometryReport.h5'
_KICK_FILE = 'kickMap.h5'
_KICK_SDDS_FILE = 'kickMap.sdds'
_KICK_TEXT_FILE = 'kickMap.txt'
_METHODS = ['get_field', 'get_field_integrals', 'get_geom', 'get_kick_map', 'save_field']
_POST_SIM_REPORTS = ['fieldIntegralReport', 'fieldLineoutReport', 'kickMapReport']
_SIM_REPORTS = ['geometryReport', 'reset', 'solverAnimation']
_REPORTS = ['fieldIntegralReport', 'fieldLineoutReport', 'geometryReport', 'kickMapReport', 'reset', 'solverAnimation']
_REPORT_RES_MAP = PKDict(
    reset='geometryReport',
    solverAnimation='geometryReport',
)
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_SDDS_INDEX = 0
_SIM_FILES = [b.basename for b in _SIM_DATA.sim_file_basenames(None)]

_ZERO = [0, 0, 0]

RADIA_EXPORT_FILE = 'radia_export.py'
VIEW_TYPES = [SCHEMA.constants.viewTypeObjects, SCHEMA.constants.viewTypeFields]

# cfg contains sdds instance
_cfg = PKDict(sdds=None)


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    if is_running:
        res.percentComplete = 0.0
        return res
    return PKDict(
        percentComplete=100,
        frameCount=1,
        solution=_read_solution(),
    )


def create_archive(sim):
    from sirepo import http_reply
    if sim.filename.endswith('dat'):
        return sirepo.http_reply.gen_file_as_attachment(
            simulation_db.simulation_dir(SIM_TYPE, sid=sim.id).join(_DMP_FILE),
            content_type='application/octet-stream',
            filename=sim.filename,
        )
    return False


def extract_report_data(run_dir, sim_in):
    assert sim_in.report in _REPORTS, 'report={}: unknown report'.format(sim_in.report)
    _SIM_DATA.sim_files_to_run_dir(sim_in, run_dir, post_init=True)
    if 'reset' in sim_in.report:
        template_common.write_sequential_result({}, run_dir=run_dir)
    if 'geometryReport' in sim_in.report:
        v_type = sim_in.models.magnetDisplay.viewType
        f_type = sim_in.models.magnetDisplay.fieldType if v_type ==\
            SCHEMA.constants.viewTypeFields else None
        d = _get_geom_data(
                sim_in.models.simulation.simulationId,
                _get_g_id(),
                sim_in.models.simulation.name,
                v_type,
                f_type,
                field_paths=sim_in.models.fieldPaths.paths
            )
        template_common.write_sequential_result(
            d,
            run_dir=run_dir,
        )
    if 'kickMapReport' in sim_in.report:
        template_common.write_sequential_result(
            _kick_map_plot(sim_in.models.kickMapReport),
            run_dir=run_dir,
        )
    if 'fieldIntegralReport' in sim_in.report:
        template_common.write_sequential_result(
            _generate_field_integrals(
                sim_in.models.simulation.simulationId,
                _get_g_id(),
                sim_in.models.fieldPaths.paths or []
            ),
            run_dir=run_dir
        )
    if 'fieldLineoutReport' in sim_in.report:
        beam_axis = sim_in.models.simulation.beamAxis
        v_axis = sim_in.models.simulation.heightAxis
        h_axis = next(iter(set(radia_util.AXES) - {beam_axis, v_axis}))
        template_common.write_sequential_result(
            _field_lineout_plot(
                sim_in.models.simulation.simulationId,
                sim_in.models.simulation.name,
                sim_in.models.fieldLineoutReport.fieldType,
                sim_in.models.fieldLineoutReport.fieldPath,
                beam_axis,
                v_axis,
                h_axis
            ),
            run_dir=run_dir,
        )


# if the file exists but the data we seek does not, have Radia generate it here.  We
# should only have to blow away the file after a solve or geometry change
# begin deprrecating this...except for save field?
def get_application_data(data, **kwargs):
    if 'method' not in data:
        raise RuntimeError('no application data method')
    if data.method not in SCHEMA.constants.getDataMethods:
        raise RuntimeError('unknown application data method: {}'.format(data.method))

    g_id = -1
    sim_id = data.simulationId
    try:
        g_id = _get_g_id()
    except IOError as e:
        if pkio.exception_is_not_found(e):
            # No Radia dump file
            return PKDict(warning='No Radia dump')
        # propagate other errors
    id_map = _read_id_map()
    if data.method == 'get_field':
        f_type = data.get('fieldType')
        res = _generate_field_data(
            sim_id, g_id, data.name, f_type, data.get('fieldPaths')
        )
        res.solution = _read_solution()
        res.idMap = id_map
        tmp_f_type = data.fieldType
        data.fieldType = None
        data.geomTypes = [SCHEMA.constants.geomTypeLines]
        data.method = 'get_geom'
        data.viewType = SCHEMA.constants.viewTypeObjects
        new_res = get_application_data(data)
        res.data += new_res.data
        data.fieldType = tmp_f_type
        return res

    if data.method == 'get_field_integrals':
        return _generate_field_integrals(sim_id, g_id, data.fieldPaths)
    if data.method == 'get_kick_map':
        return _read_or_generate_kick_map(g_id, data)
    if data.method == 'get_geom':
        g_types = data.get(
            'geomTypes',
            [SCHEMA.constants.geomTypeLines, SCHEMA.constants.geomTypePolys]
        )
        g_types.extend(['center', 'name', 'size', 'id'])
        res = _read_or_generate(sim_id, g_id, data)
        rd = res.data if 'data' in res else []
        res.data = [{k: d[k] for k in d.keys() if k in g_types} for d in rd]
        res.idMap = id_map
        return res
    if data.method == 'save_field':
        data.method = 'get_field'
        res = get_application_data(data)
        file_path = simulation_db.simulation_lib_dir(SIM_TYPE).join(
            f'{sim_id}_{res.name}.{data.fileExt}'
        )
        # we save individual field paths, so there will be one item in the list
        vectors = res.data[0].vectors
        if data.exportType == 'sdds':
            return _save_fm_sdds(
                res.name,
                vectors,
                _AXIS_ROTATIONS[data.beamAxis],
                file_path
            )
        elif data.exportType == 'csv':
            return _save_field_csv(
                data.fieldType,
                vectors,
                _AXIS_ROTATIONS[data.beamAxis],
                file_path
            )
        elif data.exportType == 'SRW':
            return _save_field_srw(
                data.fieldType,
                data.gap,
                vectors,
                _AXIS_ROTATIONS[data.beamAxis],
                file_path
            )
        return res


def get_data_file(run_dir, model, frame, options=None, **kwargs):
    assert model in _REPORTS, 'model={}: unknown report'.format(model)
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    sim = data.models.simulation
    name = sim.name
    sim_id = sim.simulationId
    beam_axis = _AXIS_ROTATIONS[sim.beamAxis]
    rpt = data.models[model]
    default_sfx = SCHEMA.constants.dataDownloads._default[0].suffix
    sfx = (options.suffix or default_sfx) if options and 'suffix' in options else \
        default_sfx
    f = f'{model}.{sfx}'
    if model == 'kickMapReport':
        km_dict = _read_or_generate_kick_map(_get_g_id(), data.models.kickMapReport)
        if sfx == 'sdds':
            _save_kick_map_sdds(name, km_dict.x, km_dict.y, km_dict.h, km_dict.v, f)
        if sfx == 'txt':
            pkio.write_text(f, km_dict.txt)
        return f
    if model == 'fieldLineoutReport':
        f_type = rpt.fieldType
        fd = _generate_field_data(
            sim_id, _get_g_id(), name, f_type, [rpt.fieldPath]
        )
        v = fd.data[0].vectors
        if sfx == 'sdds':
            return _save_fm_sdds(name, v, beam_axis, f)
        if sfx == 'csv':
            return _save_field_csv(f_type, v, beam_axis, f)
        if sfx == 'zip':
            return _save_field_srw(
                f_type,
                data.models.hybridUndulator.gap,
                v,
                beam_axis,
                pkio.py_path(f)
            )
        return f


def import_file(req, tmp_dir=None, **kwargs):
    data = simulation_db.default_data(req.type)
    data.models.simulation.pkupdate(
        {k: v for k, v in req.req_data.items() if k in data.models.simulation}
    )
    data.models.simulation.pkupdate(_parse_input_file_arg_str(req.import_file_arguments))
    _prep_new_sim(data)
    return data


def new_simulation(data, new_simulation_data):
    data.models.simulation.beamAxis = new_simulation_data.beamAxis
    data.models.simulation.enableKickMaps = new_simulation_data.enableKickMaps
    _prep_new_sim(data)
    dirs = _geom_directions(new_simulation_data.beamAxis, new_simulation_data.heightAxis)
    t = new_simulation_data.get('magnetType', 'freehand')
    s = new_simulation_data[f'{t}Type']
    m = data.models[s]
    data.models.simulation.notes = _MAGNET_NOTES[t][s]
    pkinspect.module_functions('_build_')[f'_build_{t}_objects'](
        data.models.geometryReport,
        m,
        height_dir=dirs.height_dir,
        length_dir=dirs.length_dir,
        width_dir=dirs.width_dir,
    )
    if t == 'undulator':
        data.models.fieldPaths.paths.append(_build_field_axis(
            (m.numPeriods + 0.5) * m.periodLength,
            new_simulation_data.beamAxis
        ))
        data.models.simulation.enableKickMaps = '1'
        _update_kickmap(data.models.kickMapReport, m, new_simulation_data.beamAxis)


def post_execution_processing(success_exit=True, is_parallel=False, run_dir=None, **kwargs):
    if success_exit or not is_parallel:
        return None
    return template_common.parse_mpi_log(run_dir)


def python_source_for_model(data, model):
    return _generate_parameters_file(data, False, for_export=True)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data, is_parallel, run_dir=run_dir),
    )
    if is_parallel:
        return template_common.get_exec_parameters_cmd(mpi=True)
    return None


def _add_obj_lines(field_data, obj):
    for d in obj.data:
        field_data.data.append(PKDict(lines=d.lines))


def _backend_alert(sim_id, g_id, e):
    raise sirepo.util.UserAlert(
        'backend Radia runtime error={} in simulation={} for key={}'.format(e, sim_id, g_id)
    )


def _build_clone_xform(num_copies, alt_fields, transforms):
    tx = _build_geom_obj('cloneTransform')
    tx.numCopies = num_copies
    tx.alternateFields = alt_fields
    tx.transforms = transforms
    return tx


def _build_cuboid(**kwargs):
    return _update_cuboid(_build_geom_obj('cuboid', **kwargs), **kwargs)


def _build_dipole_objects(geom, model, **kwargs):
    geom.objects.append(model.pole)
    if model.dipoleType in ['dipoleC', 'dipoleH']:
        geom.objects.append(model.magnet)
        geom.objects.append(model.coil)
        g = _update_group(model.corePoleGroup, [model.magnet, model.pole], do_replace=True)
        geom.objects.append(g)
        geom.objects.append(_update_group(model.magnetCoilGroup, [g, model.coil], do_replace=True))

    return _update_geom_from_dipole(geom, model, **kwargs)


# have to include points for file type?
def _build_field_file_pts(f_path):
    pts_file = _SIM_DATA.lib_file_abspath(_SIM_DATA.lib_file_name_with_type(
        f_path.fileName,
        SCHEMA.constants.pathPtsFileType
    ))
    lines = [float(l.strip()) for l in pkio.read_text(pts_file).split(',')]
    if len(lines) % 3 != 0:
        raise ValueError('Invalid file data {}'.format(f_path.file_data))
    return lines


def _build_field_points(paths):
    res = []
    for p in paths:
        res.extend(_FIELD_PT_BUILDERS[p.type](p))
    return res


def _build_field_line_pts(f_path):
    p1 = sirepo.util.split_comma_delimited_string(f_path.begin, float)
    p2 = sirepo.util.split_comma_delimited_string(f_path.end, float)
    res = p1
    r = range(len(p1))
    n = int(f_path.numPoints) - 1
    for i in range(1, n):
        res.extend(
            [p1[j] + i * (p2[j] - p1[j]) / n for j in r]
        )
    res.extend(p2)
    return res


def _build_field_manual_pts(f_path):
    return [float(f_path.ptX), float(f_path.ptY), float(f_path.ptZ)]


def _build_field_map_pts(f_path):
    res = []
    n = int(f_path.numPoints)
    dx, dy, dz = f_path.lenX / (n - 1), f_path.lenY / (n - 1), f_path.lenZ / (n - 1)
    for i in range(n):
        x = f_path.ctrX - 0.5 * f_path.lenX + i * dx
        for j in range(n):
            y = f_path.ctrY - 0.5 * f_path.lenY + j * dy
            for k in range(n):
                z = f_path.ctrZ - 0.5 * f_path.lenZ + k * dz
                res.extend([x, y, z])
    return res


def _build_field_circle_pts(f_path):
    ctr = [float(f_path.ctrX), float(f_path.ctrY), float(f_path.ctrZ)]
    r = float(f_path.radius)
    # theta is a rotation about the x-axis
    th = float(f_path.theta)
    # phi is a rotation about the z-axis
    phi = float(f_path.phi)
    n = int(f_path.numPoints)
    dpsi = 2. * math.pi / n
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
        res.extend([
            r * math.sin(psi) * math.cos(phi) -
            r * math.cos(psi) * math.cos(th) * math.sin(phi) + ctr[0],
            r * math.sin(psi) * math.sin(phi) -
            r * math.cos(psi) * math.cos(th) * math.cos(phi) + ctr[1],
            r * math.cos(psi) * math.sin(th) + ctr[2]
        ])
    return res


def _build_geom_obj(model_name, **kwargs):
    o = PKDict(model=model_name,)
    _SIM_DATA.update_model_defaults(o, model_name)
    o.pkupdate(kwargs)
    if not o.name:
        o.name = f'{model_name}.{o.id}'
    return o


def _build_group(members, name=None):
    return _update_group(
        _build_geom_obj('geomGroup', name=name), members, do_replace=True
    )


def _build_symm_xform(plane, type, point=None):
    tx = _build_geom_obj('symmetryTransform')
    tx.symmetryPlane = sirepo.util.to_comma_delimited_string(plane)
    tx.symmetryPoint = sirepo.util.to_comma_delimited_string(point or _ZERO)
    tx.symmetryType = type
    return tx


def _build_translate_clone(dist):
    tx = _build_geom_obj('translateClone')
    tx.distance = sirepo.util.to_comma_delimited_string(dist)
    return tx


def _build_undulator_objects(geom, model, **kwargs):
    half_pole = _build_geom_obj(model.pole.type, name='Half Pole')
    geom.objects.append(half_pole)
    geom.objects.append(model.magnet)
    geom.objects.append(model.pole)
    g = _update_group(model.corePoleGroup, [model.magnet, model.pole], do_replace=True)
    geom.objects.append(g)
    geom.objects.append(model.terminationGroup)
    geom.objects.append(
        _update_group(
            model.corePoleGroup,
            [half_pole, g, model.terminationGroup],
            do_replace=True
        )
    )
    return _update_geom_from_undulator(geom, model, **kwargs)


def _build_freehand_objects(geom, model, **kwargs):
    return geom


def _build_field_axis(length, beam_axis):
    beam_dir = radia_util.AXIS_VECTORS[beam_axis]
    f = PKDict(
        begin=sirepo.util.to_comma_delimited_string((-length / 2) * beam_dir),
        end=sirepo.util.to_comma_delimited_string((length / 2) * beam_dir),
        name=f'{beam_axis} axis',
        numPoints=round(length / 2) + 1
    )
    _SIM_DATA.update_model_defaults(f, 'linePath')
    return f


# deep copy of an object, but with a new id
def _copy_geom_obj(o):
    import copy
    o_copy = copy.deepcopy(o)
    o_copy.id = str(uuid.uuid4())
    return o_copy


def _delim_string(val=None, default_val=None):
    d = default_val if default_val is not None else []
    return sirepo.util.to_comma_delimited_string(val if val is not None else d)


_FIELD_PT_BUILDERS = {
    'circle': _build_field_circle_pts,
    'fieldMap': _build_field_map_pts,
    'file': _build_field_file_pts,
    'line': _build_field_line_pts,
    'manual': _build_field_manual_pts,
}


def _field_lineout_plot(sim_id, name, f_type, f_path, beam_axis, v_axis, h_axis):
    v = _generate_field_data(sim_id, _get_g_id(), name, f_type, [f_path]).data[0].vectors
    pts = numpy.array(v.vertices).reshape(-1, 3)
    plots = []
    labels = {h_axis: 'Horizontal', v_axis: 'Vertical'}
    f = numpy.array(v.directions).reshape(-1, 3)
    m = numpy.array(v.magnitudes)

    for c in (h_axis, v_axis):
        plots.append(
            PKDict(
                points=(m * f[:, radia_util.AXES.index(c)]).tolist(),
                label=f'{labels[c]} ({c}) [{radia_util.FIELD_UNITS[f_type]}]',
                style='line'
            )
        )
    return template_common.parameter_plot(
        pts[:, radia_util.AXES.index(beam_axis)].tolist(),
        plots,
        PKDict(),
        PKDict(
            title=f'{f_type} on {f_path.name}',
            y_label=f_type,
            x_label=f'{beam_axis} [mm]',
            summaryData=PKDict(),
        ),
    )


def _find_by_id(arr, obj_id):
    return sirepo.util.find_obj(arr, 'id', obj_id)


def _find_by_name(arr, name):
    return sirepo.util.find_obj(arr, 'name', name)


def _fit_poles_in_c_bend(**kwargs):
    d = PKDict(kwargs)
    s = d.mag_sz * d.length_dir + \
              d.pole_width * d.width_dir + \
              d.mag_sz * d.height_dir / 2 - d.arm_height * d.height_dir - d.gap * d.height_dir / 2
    c = s * d.height_dir / 2 + d.gap * d.height_dir / 2
    return s, c


def _fit_poles_in_h_bend(**kwargs):
    d = PKDict(kwargs)
    s = d.mag_sz * d.length_dir + \
              d.pole_width * d.width_dir / 2 + \
              d.mag_sz * d.height_dir - d.arm_height * d.height_dir - d.gap * d.height_dir / 2
    c = s * d.height_dir / 2 + d.gap * d.height_dir / 2 + \
               s * d.length_dir / 2 + \
               s * d.width_dir / 2
    return s, c


def _generate_field_data(sim_id, g_id, name, field_type, field_paths):
    assert field_type in radia_util.FIELD_TYPES, 'field_type={}: invalid field type'.format(field_type)
    try:
        if field_type == radia_util.FIELD_TYPE_MAG_M:
            f = radia_util.get_magnetization(g_id)
        else:
            f = radia_util.get_field(g_id, field_type, _build_field_points(field_paths))
        return radia_util.vector_field_to_data(g_id, name, f, radia_util.FIELD_UNITS[field_type])
    except RuntimeError as e:
        _backend_alert(sim_id, g_id, e)


def _generate_field_integrals(sim_id, g_id, f_paths):
    l_paths = [fp for fp in f_paths if fp.type == 'line']
    if len(l_paths) == 0:
        # return something or server.py will raise an exception
        return PKDict(warning='No paths')
    try:
        res = PKDict()
        for p in l_paths:
            res[p.name] = PKDict()
            p1 = sirepo.util.split_comma_delimited_string(p.begin, float)
            p2 = sirepo.util.split_comma_delimited_string(p.end, float)
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
            g = _generate_field_data(
                sim_id, g_id, name, field_type, field_paths
            )
            _add_obj_lines(g, o)
            return g
    except RuntimeError as e:
        _backend_alert(sim_id, g_id, e)


def _generate_kick_map(g_id, model):
    km = radia_util.kick_map(
        g_id,
        sirepo.util.split_comma_delimited_string(model.begin, float),
        sirepo.util.split_comma_delimited_string(model.direction, float),
        int(model.numPeriods),
        float(model.periodLength),
        sirepo.util.split_comma_delimited_string(model.transverseDirection, float),
        float(model.transverseRange1),
        int(model.numTransPoints1),
        float(model.transverseRange2),
        int(model.numTransPoints2)
    )
    return PKDict(
        h=km[0],
        v=km[1],
        lmsqr=km[2],
        x=km[3],
        y=km[4]
    )


def _generate_obj_data(g_id, name):
    return radia_util.geom_to_data(g_id, name=name)


def _generate_parameters_file(data, is_parallel, for_export=False, run_dir=None):
    import jinja2

    report = data.get('report', '')
    rpt_out = f'{_REPORT_RES_MAP.get(report, report)}'
    res, v = template_common.generate_parameters_file(data)
    if rpt_out in _POST_SIM_REPORTS:
        return res

    g = data.models.geometryReport
    v.simId = data.models.simulation.simulationId

    v.doSolve = 'solver' in report or for_export
    v.doReset = 'reset' in report
    do_generate = _normalize_bool(g.get('doGenerate', True)) or v.doSolve or v.doReset
    if not do_generate:
        try:
            # use the previous results
            _SIM_DATA.sim_files_to_run_dir(data, run_dir, post_init=True)
        except sirepo.sim_data.SimDbFileNotFound:
            do_generate = True

    if not do_generate:
        return res

    # ensure old files are gone
    for f in _SIM_FILES:
        pkio.unchecked_remove(f)

    v.doReset = False
    v.isParallel = is_parallel

    v.dmpOutputFile = _DMP_FILE
    if 'dmpImportFile' in data.models.simulation:
        v.dmpImportFile = data.models.simulation.dmpImportFile if for_export else \
            simulation_db.simulation_lib_dir(SIM_TYPE).join(
                f'{SCHEMA.constants.radiaDmpFileType}.{data.models.simulation.dmpImportFile}'
            )
    v.isExample = data.models.simulation.get('isExample', False) and \
        data.models.simulation.name in radia_examples.EXAMPLES
    v.exampleName = data.models.simulation.get('exampleName', None)
    v.is_raw = v.exampleName in SCHEMA.constants.rawExamples
    v.magnetType = data.models.simulation.get('magnetType', 'freehand')
    dirs = _geom_directions(data.models.simulation.beamAxis, data.models.simulation.heightAxis)
    if not v.isExample and v.magnetType == 'freehand':
        _update_geom_from_freehand(g)
    if v.magnetType == 'undulator':
        v.undulatorType = data.models.simulation.undulatorType
        _update_geom_from_undulator(
            g,
            data.models[v.undulatorType],
            height_dir=dirs.height_dir,
            length_dir=dirs.length_dir,
            width_dir=dirs.width_dir,
        )
    if v.magnetType == 'dipole':
        v.dipoleType = data.models.simulation.dipoleType
        _update_geom_from_dipole(
            g,
            data.models[v.dipoleType],
            height_dir=dirs.height_dir,
            length_dir=dirs.length_dir,
            width_dir=dirs.width_dir,
        )
    v.objects = g.get('objects', [])
    _validate_objects(v.objects)

    for o in v.objects:
        if o.get('type'):
            o.super_classes = SCHEMA.model[o.type]._super
        # read in h-m curves if applicable
        o.h_m_curve = _read_h_m_file(o.materialFile) if \
            o.get('material', None) and o.material == 'custom' and \
            o.get('materialFile', None) and o.materialFile else None
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
        raise ValueError('Invalid view {} ({})'.format(v_type, VIEW_TYPES))
    v.viewType = v_type
    v.dataFile = _GEOM_FILE if for_export else f'{rpt_out}.h5'
    if v_type == SCHEMA.constants.viewTypeFields:
        f_type = disp.fieldType
        if f_type not in radia_util.FIELD_TYPES:
            raise ValueError(
                'Invalid field {} ({})'.format(f_type, radia_util.FIELD_TYPES)
            )
        v.fieldType = f_type
        v.fieldPaths = data.models.fieldPaths.get('paths', [])
        v.fieldPoints = _build_field_points(data.models.fieldPaths.get('paths', []))
    v.kickMap = data.models.get('kickMapReport')
    if 'solver' in report or for_export:
        v.doSolve = True
        s = data.models.solverAnimation
        v.solvePrec = s.precision
        v.solveMaxIter = s.maxIterations
        v.solveMethod = s.method
    if 'reset' in report:
        v.doReset = True
    v.h5FieldPath = _geom_h5_path(SCHEMA.constants.viewTypeFields, f_type)
    v.h5KickMapPath = _H5_PATH_KICK_MAP
    v.h5ObjPath = _geom_h5_path(SCHEMA.constants.viewTypeObjects)
    v.h5SolutionPath = _H5_PATH_SOLUTION
    v.h5IdMapPath = _H5_PATH_ID_MAP

    j_file = RADIA_EXPORT_FILE if for_export else f'{rpt_out}.py'
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        j_file,
        jinja_env=PKDict(loader=jinja2.PackageLoader('sirepo', 'template'))
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
    p = f'geometry/{view_type}'
    if field_type is not None:
        p += f'/{field_type}'
    return p


def _get_g_id():
    return radia_util.load_bin(pkio.read_binary(_DMP_FILE))


def _get_geom_data(
        sim_id,
        g_id,
        name,
        view_type,
        field_type,
        field_paths=None,
        geom_types=[SCHEMA.constants.geomTypeLines, SCHEMA.constants.geomTypePolys]
    ):
    assert view_type in VIEW_TYPES, 'view_type={}: invalid view type'.format(view_type)
    if view_type == SCHEMA.constants.viewTypeFields:
        res = _generate_field_data(
            sim_id, g_id, name, field_type, field_paths
        )
        res.data += _get_geom_data(
            sim_id,
            g_id,
            name,
            SCHEMA.constants.viewTypeObjects,
            None,
            geom_types=[SCHEMA.constants.geomTypeLines]
        ).data
        return res

    geom_types.extend(['center', 'name', 'size', 'id'])
    res = _read_or_generate(sim_id, g_id, name, view_type, None)
    rd = res.data if 'data' in res else []
    res.data = [{k: d[k] for k in d.keys() if k in geom_types} for d in rd]
    res.idMap = _read_id_map()
    res.solution = _read_solution()
    return res


def _get_sdds(cols, units):
    if _cfg.sdds is None:
        _cfg.sdds = sdds.SDDS(_SDDS_INDEX)
        # TODO(mvk): elegant cannot read these binary files; figure that out
        # _cfg.sdds = sd.SDDS_BINARY
        for i, n in enumerate(cols):
            # name, symbol, units, desc, format, type, len)
            _cfg.sdds.defineColumn(
                n, '', units[i], n, '', _cfg.sdds.SDDS_DOUBLE, 0
            )
    return _cfg.sdds


def _kick_map_plot(model):
    from sirepo import srschema
    g_id = _get_g_id()
    component = model.component
    km = _generate_kick_map(g_id, model)
    if not km:
        return None
    z = km[component]
    return PKDict(
        title=f'{srschema.get_enums(SCHEMA, "KickMapComponent")[component]} (T2m2)',
        x_range=[km.x[0], km.x[-1], len(z)],
        y_range=[km.y[0], km.y[-1], len(z[0])],
        x_label='x [mm]',
        y_label='y [mm]',
        z_matrix=z,
    )


def _next_axis(axis):
    return radia_util.AXES[(radia_util.AXES.index(axis) + 1) % len(radia_util.AXES)]


def _normalize_bool(x):
    bool_map = {'1': True, '0': False}
    return bool_map[x] if x in bool_map else x


def _orient_stemmed_points(o, points, plane_ctr):
    idx = [int(o.stemPosition), int(o.armPosition)]
    return [
        [2 * plane_ctr[i] * idx[i] + (-1)**idx[i] * v for (i, v) in enumerate(p)] \
        for p in points
    ]


def _parse_input_file_arg_str(s):
    d = PKDict()
    for kvp in s.split(SCHEMA.constants.inputFileArgDelims.list):
        if not kvp:
            continue
        kv = kvp.split(SCHEMA.constants.inputFileArgDelims.item)
        d[kv[0]] = kv[1]
    return d


def _prep_new_sim(data):
    data.models.geometryReport.name = data.models.simulation.name


def _read_h5_path(filename, h5path):
    try:
        with h5py.File(filename, 'r') as f:
            return template_common.h5_to_dict(f, path=h5path)
    except IOError as e:
        if pkio.exception_is_not_found(e):
            pkdlog('filename={} not found', filename)
            # need to generate file
            return None
    except template_common.NoH5PathError:
        # no such path in file
        pkdlog('h5Path={} not found in filename={}', h5path, filename)
        return None
    # propagate other errors


def _read_h_m_file(file_name):
    h_m_file = _SIM_DATA.lib_file_abspath(_SIM_DATA.lib_file_name_with_type(
        file_name,
        'h-m'
    ))
    lines = [r for r in sirepo.csv.open_csv(h_m_file)]
    f_lines = []
    for l in lines:
        f_lines.append([float(c.strip()) for c in l])
    return f_lines


def _read_data(view_type, field_type):
    res = _read_h5_path(_GEOM_FILE, _geom_h5_path(view_type, field_type))
    if res:
        res.idMap = _read_id_map()
        res.solution = _read_solution()
    return res


def _read_id_map():
    m = _read_h5_path(_GEOM_FILE, _H5_PATH_ID_MAP)
    return PKDict() if not m else PKDict(
        {k:(v if isinstance(v, int) else pkcompat.from_bytes(v)) for k, v in m.items()}
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
        h5_path=_geom_h5_path(view_type, field_type)
    )
    return _get_geom_data(sim_id, g_id, name, view_type, field_type, field_paths)


def _read_or_generate_kick_map(g_id, data):
    res = _read_kick_map()
    if res:
        return res
    return _generate_kick_map(g_id, data.model)


def _read_solution():
    s = _read_h5_path(
        _GEOM_FILE,
        _H5_PATH_SOLUTION,
    )
    if not s:
        return None
    return PKDict(
        steps=s[3],
        time=s[0],
        maxM=s[1],
        maxH=s[2]
    )


# mm -> m, rotate so the beam axis is aligned with z
def _rotate_fields(vectors, scipy_rotation, do_flatten):
    pts = 0.001 * _rotate_flat_vector_list(vectors.vertices, scipy_rotation)
    mags = numpy.array(vectors.magnitudes)
    dirs = _rotate_flat_vector_list(vectors.directions, scipy_rotation)
    if do_flatten:
        dirs = dirs.flatten()
        pts = pts.flatten()
    return pts, mags, dirs


def _rotate_flat_vector_list(vectors, scipy_rotation):
    return scipy_rotation.apply(numpy.reshape(vectors, (-1, 3)))


def _save_field_csv(field_type, vectors, scipy_rotation, path):
    # reserve first line for a header
    data = [f'x,y,z,{field_type}x,{field_type}y,{field_type}z']
    pts, mags, dirs = _rotate_fields(vectors, scipy_rotation, True)
    for i in range(len(mags)):
        j = 3 * i
        r = pts[j:j + 3]
        r = numpy.append(r, mags[i] * dirs[j:j + 3])
        data.append(','.join(map(str, r)))
    pkio.write_text(path, '\n'.join(data))
    return path


# zip file - data plus index.  This will likely be used to generate files for a range
# of gaps later
def _save_field_srw(field_type, gap, vectors, scipy_rotation, path):
    import zipfile
    # no whitespace in filenames
    base_name = re.sub(r'\s', '_', path.purebasename)
    data_path = path.dirpath().join(f'{base_name}_{gap}.dat')
    index_path = path.dirpath().join(f'{base_name}_sum.txt')
    pkio.unchecked_remove(path, data_path, index_path)

    data = ['#Bx [T], By [T], Bz [T] on 3D mesh: inmost loop vs X (horizontal transverse position), outmost loop vs Z (longitudinal position)']
    pts, mags, dirs = _rotate_fields(vectors, scipy_rotation, True)
    num_pts = len(pts) // 3
    dims = ['X', 'Y', 'Z']
    for j in range(len(dims)):
        data.append(f'#{pts[j]} #initial {dims[j]} position [m]')
        data.append(f'#{(pts[len(pts) - (len(dims) - j)] - pts[j]) / num_pts} #step of {dims[j]} [m]')
        data.append(f'#{num_pts if j == len(dims) - 1 else 1} #number of points vs {dims[j]}')
    for i in range(len(mags)):
        j = 3 * i
        data.append('\t'.join(map(str, mags[i] * dirs[j:j + 3])))
    pkio.write_text(data_path, '\n'.join(data))

    # index file
    data = [f'{gap}\tp1\t0\t{data_path.basename}\t1\t1']
    pkio.write_text(index_path, '\n'.join(data))

    files = [data_path, index_path]

    # zip file
    with zipfile.ZipFile(
        str(path),
        mode='w',
        compression=zipfile.ZIP_DEFLATED,
        allowZip64=True,
    ) as z:
        for f in files:
            z.write(str(f), f.basename)

    return path


def _save_fm_sdds(name, vectors, scipy_rotation, path):
    s = _get_sdds(_FIELD_MAP_COLS, _FIELD_MAP_UNITS)
    s.setDescription(f'Field Map for {name}', 'x(m), y(m), z(m), Bx(T), By(T), Bz(T)')
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


def _save_kick_map_sdds(name, x_vals, y_vals, h_vals, v_vals, path):
    s = _get_sdds(_KICK_MAP_COLS, _KICK_MAP_UNITS)
    s.setDescription(f'Kick Map for {name}', 'x(m), y(m), h(T2m2), v(T2m2)')
    col_data = []
    x = []
    y = []
    h = []
    v = []
    #TODO: better way to do this...
    for i in range(len(x_vals)):
        for j in range(len(x_vals)):
            x.append(0.001 * x_vals[j])
    for i in range(len(y_vals)):
        for j in range(len(y_vals)):
            y.append(0.001 * y_vals[i])
    for i in range(len(x_vals)):
        for j in range(len(y_vals)):
            h.append(h_vals[i][j])
            v.append(v_vals[i][j])
    col_data.append([x])
    col_data.append([y])
    col_data.append([h])
    col_data.append([v])
    for i, n in enumerate(_KICK_MAP_COLS):
        s.setColumnValueLists(n, col_data[i])
    s.save(str(path))
    return path


def _undulator_termination_name(index, term_type):
    return f'termination.{term_type}.{index}'


def _update_cee(o, **kwargs):
    return _update_cee_points(
        _update_geom_obj(o, **kwargs)
    )


def _update_cee_points(o):
    o.points = _get_cee_points(o, _get_stemmed_info(o))
    return o


def _get_cee_points(o, stemmed_info):
    p = stemmed_info.points
    sy2 = p.sy1 + o.armHeight
    return _orient_stemmed_points(
        o,
        [
            [p.ax1, p.ay1], [p.ax2, p.ay1], [p.ax2, p.ay2],
            [p.sx2, p.ay2], [p.sx2, sy2], [p.ax2, sy2], [p.ax2, p.sy1], [p.sx1, p.sy1],
            [p.ax1, p.ay1]
        ],
        stemmed_info.plane_ctr
    )


def _update_cuboid(o, **kwargs):
    return _update_geom_obj(o, **kwargs)


def _update_ell(o, **kwargs):
    return _update_ell_points(
        _update_geom_obj(o, **kwargs)
    )


def _update_ell_points(o):
    o.points = _get_ell_points(o, _get_stemmed_info(o))
    return o


def _get_ell_points(o, stemmed_info):
    p = stemmed_info.points
    return _orient_stemmed_points(
        o,
        [
            [p.ax1, p.ay1], [p.ax2, p.ay1], [p.ax2, p.ay2],
            [p.sx2, p.ay2], [p.sx2, p.sy1], [p.sx1, p.sy1],
            [p.ax1, p.ay1]
        ],
        stemmed_info.plane_ctr
    )


# For consistency, always set the width and height axes of the extruded shape in
# permutation order based on the extrusion axis:
#   x -> (y, z), y -> (z, x), z -> (x, y)
def _update_extruded(o):
    o.widthAxis = _next_axis(o.extrusionAxis)
    o.heightAxis = _next_axis(o.widthAxis)

    # Radia's extrusion routine seems to involve rotations, one result being that
    # segmentation in the extrusion direction must be along 'x' regardless of the
    # actual direction
    o.segments = sirepo.util.to_comma_delimited_string(
        _AXES_UNIT + radia_util.AXIS_VECTORS.x * (o.extrusionAxisSegments - 1)
    )
    return o


def _update_dipole_basic(model, **kwargs):
    d = PKDict(kwargs)
    pole_sz = sirepo.util.split_comma_delimited_string(d.pole.size, float)
    return _update_geom_obj(
        d.pole,
        size=pole_sz,
        center=pole_sz * d.height_dir / 2 + model.gap * d.height_dir / 2,
        transforms=[_build_symm_xform(d.height_dir, 'parallel')]
    )


def _update_dipole_c(model, **kwargs):
    d = PKDict(kwargs)
    mag_sz = numpy.array(sirepo.util.split_comma_delimited_string(d.magnet.size, float))
    pole_sz, pole_ctr = _fit_poles_in_c_bend(
        arm_height=model.magnet.armHeight,
        gap=model.gap,
        mag_sz=mag_sz,
        pole_width=model.poleWidth,
        **kwargs
    )
    mag_ctr = mag_sz * d.width_dir / 2 - pole_sz * d.width_dir / 2
    _update_geom_obj(
        d.pole,
        center=pole_ctr,
        size=pole_sz,
        transforms=[_build_symm_xform(d.height_dir, 'parallel')]
    )
    _update_geom_obj(d.magnet, center=mag_ctr)
    _update_geom_obj(
        d.coil,
        center=mag_ctr + mag_sz * d.width_dir / 2 - model.magnet.stemWidth * d.width_dir / 2
    )
    return d.mag_coil_group


def _update_dipole_h(model, **kwargs):
    d = PKDict(kwargs)
    # magnetSize is for the entire magnet - split it here so we can apply symmetries
    mag_sz = numpy.array(
        sirepo.util.split_comma_delimited_string(model.magnetSize, float)) / 2
    pole_sz, pole_ctr = _fit_poles_in_h_bend(
        arm_height=model.magnet.armHeight,
        gap=model.gap,
        mag_sz=mag_sz,
        pole_width=model.poleWidth,
        **kwargs
    )
    _update_geom_obj(d.pole, center=pole_ctr, size=pole_sz)
    _update_geom_obj(
        d.magnet,
        center=mag_sz / 2 - mag_sz * d.length_dir / 2
    )
    # length and width symmetries
    d.core_pole_group.transforms = [
        _build_symm_xform(d.length_dir, 'perpendicular'),
        _build_symm_xform(d.width_dir, 'perpendicular')
    ]
    # height symmetry
    d.mag_coil_group.transforms = [
        _build_symm_xform(d.height_dir, 'parallel')
    ]
    return d.mag_coil_group


def _update_geom_from_dipole(geom, model, **kwargs):

    assert model.dipoleType in [x[0] for x in SCHEMA.enum.DipoleType]
    _update_geom_objects(geom.objects)

    pole = _find_by_id(geom.objects, model.pole.id)

    if model.dipoleType == 'dipoleBasic':
        return _update_dipole_basic(
            model,
            pole=pole,
            **kwargs
        )

    magnet = _find_by_id(geom.objects, model.magnet.id)
    coil = _find_by_id(geom.objects, model.coil.id)
    mag_coil_group = _find_by_id(geom.objects, model.magnetCoilGroup.id)

    if model.dipoleType == 'dipoleC':
        return _update_dipole_c(
            model,
            pole=pole,
            magnet=magnet,
            coil=coil,
            mag_coil_group=mag_coil_group,
            **kwargs
        )
    if model.dipoleType == 'dipoleH':
        return _update_dipole_h(
            model,
            pole=pole,
            magnet=magnet,
            coil=coil,
            mag_coil_group=mag_coil_group,
            core_pole_group=_find_by_id(geom.objects, model.corePoleGroup.id),
            **kwargs
        )

    return mag_coil_group


def _update_geom_from_freehand(geom, **kwargs):
    _update_geom_objects(geom.objects, **kwargs)


def _update_geom_from_undulator(geom, model, **kwargs):

    assert model.undulatorType in [x[0] for x in SCHEMA.enum.UndulatorType]
    _update_geom_objects(geom.objects)


    magnet = _find_by_id(geom.objects, model.magnet.id)
    mag_coil_group = _find_by_id(geom.objects, model.magnetCoilGroup.id)


    if model.undulatorType == 'unudulatorHybrid':
        pole = _find_by_id(geom.objects, model.pole.id)
        return _update_undulator_hybrid(
            model,
            pole=pole,
            magnet=magnet,
            mag_coil_group=mag_coil_group,
            **kwargs
        )

    dir_matrix = numpy.array([dirs.width_dir, dirs.height_dir, dirs.length_dir])

    pole_x = sirepo.util.split_comma_delimited_string(und.poleCrossSection, float)
    mag_x = sirepo.util.split_comma_delimited_string(und.magnetCrossSection, float)

    # pole and magnet dimensions, including direction
    pole_dim = PKDict(
        width=dirs.width_dir * pole_x[0],
        height=dirs.height_dir * pole_x[1],
        length=dirs.length_dir * und.poleLength,
    )
    magnet_dim = PKDict(
        width=dirs.width_dir * mag_x[0],
        height=dirs.height_dir * mag_x[1],
        length=dirs.length_dir * (und.periodLength / 2 - pole_dim.length),
    )

    # convenient constants
    gap_half_height = dirs.height_dir * und.gap / 2
    gap_offset = dirs.height_dir * und.gapOffset

    # put the magnetization and segmentation in the correct order below
    obj_props = PKDict(
        pole=PKDict(
            arm_height=und.poleArmHeight,
            arm_pos=und.poleArmPosition,
            color=und.poleColor,
            dim=pole_dim,
            dim_half=PKDict({k:v / 2 for k, v in pole_dim.items()}),
            material=und.poleMaterial,
            mat_file=und.poleMaterialFile,
            mag=dir_matrix.dot(
                sirepo.util.split_comma_delimited_string(und.poleMagnetization, float)
            ),
            obj_type=und.poleObjType,
            rem_mag=und.poleRemanentMag,
            segs=dir_matrix.dot(
                sirepo.util.split_comma_delimited_string(und.poleSegments, int)
            ),
            stem_width=und.poleStemWidth,
            stem_pos=und.poleStemPosition,
        ),
        magnet=PKDict(
            arm_height=und.magnetArmHeight,
            arm_pos=und.magnetArmPosition,
            color=und.magnetColor,
            dim=magnet_dim,
            dim_half=PKDict({k: v / 2 for k, v in magnet_dim.items()}),
            material=und.magnetMaterial,
            mat_file=und.magnetMaterialFile,
            mag=dir_matrix.dot(
                sirepo.util.split_comma_delimited_string(und.magnetMagnetization, float)
            ),
            obj_type=und.magnetObjType,
            rem_mag=und.magnetRemanentMag,
            segs=dir_matrix.dot(
                sirepo.util.split_comma_delimited_string(und.magnetSegments, int)
            ),
            stem_width=und.magnetStemWidth,
            stem_pos=und.magnetStemPosition,
        )
    )
    for k in obj_props.keys():
        obj_props[k].transverse_ctr = obj_props[k].dim_half.width / 2 - \
            (obj_props[k].dim_half.height + gap_half_height)
    obj_props.magnet.transverse_ctr -= gap_offset

    half_pole = _find_by_name(geom.objects, 'Half Pole')
    props = obj_props.pole
    pos = props.dim_half.length / 2
    half_pole = _update_geom_obj(
        half_pole,
        center=props.transverse_ctr + pos,
        color=props.color,
        magnetization=props.mag,
        material=props.material,
        materialFile=props.mat_file,
        remanentMag=props.rem_mag,
        size=props.dim_half.width + props.dim.height + props.dim_half.length,
    )
    if props.obj_type == 'ell':
        half_pole = _update_ell(
            half_pole,
            armHeight=props.arm_height,
            armPosition=props.arm_pos,
            stemWidth=props.stem_width,
            stemPosition=props.stem_pos
        )
    else:
        half_pole = _update_cuboid(
            half_pole,
            segments=props.segs,
        )

    pos += (obj_props.pole.dim_half.length / 2 + obj_props.magnet.dim_half.length)
    magnet_block = _find_by_name(geom.objects, 'Magnet Block')
    props = obj_props.magnet
    magnet_block = _update_geom_obj(
        magnet_block,
        center=props.transverse_ctr + pos,
        color=props.color,
        magnetization=props.mag,
        material=props.material,
        materialFile=props.mat_file,
        remanentMag=props.rem_mag,
        size=props.dim_half.width + props.dim.height + props.dim.length,
    )
    if props.obj_type == 'ell':
        magnet_block = _update_ell(
            magnet_block,
            armHeight=props.arm_height,
            armPosition=props.arm_pos,
            stemWidth=props.stem_width,
            stemPosition=props.stem_pos
        )
    else:
        magnet_block = _update_cuboid(
            magnet_block,
            segments=props.segs
        )
    und.magnetBaseObjectId = magnet_block.id
    obj_props.magnet.bevels = magnet_block.get('bevels', [])

    pos += (obj_props.pole.dim_half.length + obj_props.magnet.dim_half.length)
    pole = _find_by_name(geom.objects, 'Pole')
    props = obj_props.pole
    pole = _update_geom_obj(
        pole,
        center=props.transverse_ctr + pos,
        color=props.color,
        magnetization=props.mag,
        material=props.material,
        materialFile=props.mat_file,
        remanentMag=props.rem_mag,
        size=props.dim_half.width + props.dim.height + props.dim.length,
    )
    if props.obj_type == 'ell':
        pole = _update_ell(
            pole,
            armHeight=props.arm_height,
            armPosition=props.arm_pos,
            stemWidth=props.stem_width,
            stemPosition=props.stem_pos
        )
    else:
        pole = _update_cuboid(
            pole,
            segments=props.segs,
        )
    und.poleBaseObjectId = pole.id
    obj_props.pole.bevels = pole.get('bevels', [])
    half_pole.bevels = obj_props.pole.bevels.copy()

    mag_pole_grp = _find_by_name(geom.objects, 'Magnet-Pole Pair')
    mag_pole_grp.transforms = [] if und.numPeriods < 2 else \
        [_build_clone_xform(
            und.numPeriods - 1,
            True,
            [_build_translate_clone(dirs.length_dir * und.periodLength / 2)]
        )]

    pos = obj_props.pole.dim_half.length + \
        dirs.length_dir * (und.numPeriods * und.periodLength / 2)

    oct_grp = _find_by_name(geom.objects, 'Octant')

    # rebuild the termination group
    old_terms = []
    for i, o in enumerate(geom.objects):
        old_terms.extend([_undulator_termination_name(i, n[0]) for n in SCHEMA.enum.TerminationType])
    geom.objects[:] = [o for o in geom.objects if o.name not in old_terms]
    terms = []
    num_term_mags = 0
    for i, t in enumerate(und.terminations):
        l = t.length * dirs.length_dir
        pos += (t.airGap + l / 2) * dirs.length_dir
        props = obj_props[t.type]
        o = _update_geom_obj(
            _build_geom_obj(props.obj_type, name=_undulator_termination_name(i, t.type), color=props.color),
            center=props.transverse_ctr + pos,
            material=props.material,
            materialFile=props.mat_file,
            magnetization=_ZERO if t.type == 'pole' else (-1) ** (
                        und.numPeriods + num_term_mags) * props.mag,
            remanentMag=props.rem_mag,
            size=props.dim_half.width + props.dim.height + l,
        )
        if props.obj_type == 'ell':
            o = _update_ell(
                o,
                armHeight=props.arm_height,
                armPosition=props.arm_pos,
                stemWidth=props.stem_width,
                stemPosition=props.stem_pos
            )
        else:
            o = _update_cuboid(o, segments=props.segs)
        o.bevels = props.bevels
        terms.append(o)
        pos += l / 2
        if t.type == 'magnet':
            num_term_mags += 1
    geom.objects.extend(terms)
    g = _find_by_name(geom.objects, 'Termination')
    if not g:
        g = _build_group(terms, name='Termination')
        geom.objects.append(g)
    else:
        _update_group(g, terms, do_replace=True)
    _update_group(oct_grp, [g])

    oct_grp.transforms = [
        _build_symm_xform(dirs.width_dir, 'perpendicular'),
        _build_symm_xform(dirs.height_dir, 'parallel'),
        _build_symm_xform(dirs.length_dir, 'perpendicular'),
    ]
    return oct_grp

def _update_undulator_hybrid(model, **kwargs):


def _update_geom_objects(objects, **kwargs):
    g = '_get_'
    for o in objects:
        _update_geom_obj(o, **kwargs)
        if 'type' not in o:
            continue
        s = SCHEMA.model[o.type]._super
        if 'extrudedPoly' in s:
            _update_extruded(o)
        if 'stemmed' in s:
            o.points = pkinspect.module_functions(g)[f'{g}{o.type}_points'](o, _get_stemmed_info(o))


def _update_geom_obj(o, delim_fields=None, **kwargs):
    d = PKDict(
        center=[0.0, 0.0, 0.0],
        magnetization=[0.0, 0.0, 0.0],
        segments=[1, 1, 1],
        size=[1.0, 1.0, 1.0],
    )
    if delim_fields is not None:
        d.update(delim_fields)
    for k in d:
        v = kwargs.get(k)
        if k in o and v is None:
            continue
        o[k] = _delim_string(val=v, default_val=d[k])
        # remove the key from kwargs so it doesn't conflict with the update
        if v is not None:
            del kwargs[k]
    o.update(kwargs)
    return o


def _update_jay(o, **kwargs):
    return _update_jay_points(
        _update_geom_obj(o, **kwargs)
    )


def _update_jay_points(o):
    o.points = _get_jay_points(o, _get_stemmed_info(o))
    return o


def _get_jay_points(o, stemmed_info):
    p = stemmed_info.points
    jx1 = stemmed_info.plane_ctr[0] + stemmed_info.plane_size[0] / 2 - o.hookWidth
    jy1 = p.ay2 - o.hookHeight

    return _orient_stemmed_points(
        o,
        [
            [p.ax1, p.ay1], [p.ax2, p.ay1], [p.ax2, jy1], [jx1, jy1], [jx1, p.ay2],
            [p.sx2, p.ay2], [p.sx2, p.sy1], [p.sx1, p.sy1],
            [p.ax1, p.ay1]
        ],
        stemmed_info.plane_ctr
    )


def _update_racetrack(o, **kwargs):
    return _update_geom_obj(o, **kwargs)


def _get_stemmed_info(o):
    w, h = radia_util.AXIS_VECTORS[o.widthAxis], radia_util.AXIS_VECTORS[o.heightAxis]
    c = sirepo.util.split_comma_delimited_string(o.center, float)
    s = sirepo.util.split_comma_delimited_string(o.size, float)

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
    km.direction = sirepo.util.to_comma_delimited_string(radia_util.AXIS_VECTORS[beam_axis])
    km.transverseDirection = sirepo.util.to_comma_delimited_string(
        radia_util.AXIS_VECTORS[SCHEMA.constants.heightAxisMap[beam_axis]]
    )
    km.transverseRange1 = und.gap
    km.numPeriods = und.numPeriods
    km.periodLength = und.periodLength


def _validate_objects(objects):
    import numpy.linalg
    for o in objects:
        if 'material' in o and o.material in SCHEMA.constants.anisotropicMaterials:
            if numpy.linalg.norm(sirepo.util.split_comma_delimited_string(o.magnetization, float)) == 0:
                raise ValueError(
                    'name={}, : material={}: anisotropic material requires non-0 magnetization'.format(
                        o.name, o.material
                    )
                )


_H5_PATH_ID_MAP = _geom_h5_path('idMap')
_H5_PATH_KICK_MAP = _geom_h5_path('kickMap')
_H5_PATH_SOLUTION = _geom_h5_path('solution')
