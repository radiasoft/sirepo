# -*- coding: utf-8 -*-
u"""Radia execution template.

All Radia calls have to be done from here, NOT in jinja files, because otherwise the
Radia "instance" goes away and references no longer have any meaning.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import division
from pykern import pkcollections
from pykern.pkcollections import PKDict
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from scipy.spatial.transform import Rotation
from sirepo import simulation_db
from sirepo.template import template_common
from sirepo.template import radia_tk
from sirepo.template import radia_examples
import h5py
import math
import numpy
import re
import sdds
import sirepo.csv
import sirepo.sim_data
import sirepo.util
import time
import uuid

_BEAM_AXIS_ROTATIONS = PKDict(
    x=Rotation.from_matrix([[0, 0, 1], [0, 1, 0], [-1, 0, 0]]),
    y=Rotation.from_matrix([[1, 0, 0], [0, 0, -1], [0, 1, 0]]),
    z=Rotation.from_matrix([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
)

_BEAM_AXIS_VECTORS = PKDict(
    x=[1, 0, 0],
    y=[0, 1, 0],
    z=[0, 0, 1]
)

_GAP_AXIS_MAP = PKDict(
    x='z',
    y='z',
    z='y'
)

_DMP_FILE = 'geometry.dat'

# Note that these column names and units are required by elegant
_FIELD_MAP_COLS = ['x', 'y', 'z', 'Bx', 'By', 'Bz']
_FIELD_MAP_UNITS = ['m', 'm', 'm', 'T', 'T', 'T']
_KICK_MAP_COLS = ['x', 'y', 'xpFactor', 'ypFactor']
_KICK_MAP_UNITS = ['m', 'm', '(T*m)$a2$n', '(T*m)$a2$n']
_FIELDS_FILE = 'fields.h5'
_GEOM_DIR = 'geometry'
_GEOM_FILE = 'geometry.h5'
_KICK_FILE = 'kickMap.h5'
_KICK_SDDS_FILE = 'kickMap.sdds'
_KICK_TEXT_FILE = 'kickMap.txt'
_METHODS = ['get_field', 'get_field_integrals', 'get_geom', 'get_kick_map', 'save_field']
_SIM_REPORTS = ['geometry', 'reset', 'solver']
_REPORTS = ['geometry', 'kickMap', 'reset', 'solver']
_REPORT_RES_MAP = PKDict(
    reset='geometry',
    solver='geometry',
)
_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()
_SDDS_INDEX = 0

_ZERO = [0, 0, 0]

GEOM_PYTHON_FILE = 'geometry.py'
KICK_PYTHON_FILE = 'kickMap.py'
RADIA_EXPORT_FILE = 'radia_export.py'
MPI_SUMMARY_FILE = 'mpi-info.json'
VIEW_TYPES = [_SCHEMA.constants.viewTypeObjects, _SCHEMA.constants.viewTypeFields]

# cfg contains sdds instance
_cfg = PKDict(sdds=None)


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    if is_running:
        #data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        res.percentComplete = 0.0  #_compute_percent_complete(data, last_element)
        return res
    return PKDict(
        percentComplete=100,
        frameCount=1,
        solution=_read_solution(data.simulationId),  #output_info,
    )


def create_archive(sim):
    if sim.filename.endswith('dat'):
        return sirepo.http_reply.gen_file_as_attachment(
            _dmp_file(sim.id),
            content_type='application/octet-stream',
            filename=sim.filename,
        )
    return False


def extract_report_data(run_dir, sim_in):
    assert sim_in.report in _REPORTS, 'unknown report: {}'.format(sim_in.report)
    if 'reset' in sim_in.report:
        template_common.write_sequential_result({}, run_dir=run_dir)
    if 'geometry' in sim_in.report:
        v_type = sim_in.models.magnetDisplay.viewType
        f_type = sim_in.models.magnetDisplay.fieldType if v_type ==\
            _SCHEMA.constants.viewTypeFields else None
        template_common.write_sequential_result(
            _read_data(sim_in.simulationId, v_type, f_type),
            run_dir=run_dir,
        )
    if 'kickMap' in sim_in.report:
        template_common.write_sequential_result(
            _kick_map_plot(sim_in.simulationId, sim_in.models.kickMap),
            run_dir=run_dir,
        )


# if the file exists but the data we seek does not, have Radia generate it here.  We
# should only have to blow away the file after a solve or geometry change
def get_application_data(data, **kwargs):
    if 'method' not in data:
        raise RuntimeError('no application data method')
    if data.method not in _SCHEMA.constants.getDataMethods:
        raise RuntimeError('unknown application data method: {}'.format(data.method))

    g_id = -1
    sim_id = data.simulationId
    try:
        g_id = _get_g_id(sim_id)
    except IOError as e:
        if pkio.exception_is_not_found(e):
            # No Radia dump file
            return PKDict(warning='No Radia dump')
        # propagate other errors
    id_map = _read_id_map(sim_id)
    if data.method == 'get_field':
        f_type = data.get('fieldType')
        res = _generate_field_data(
            g_id, data.name, f_type, data.get('fieldPaths', None)
        )
        res.solution = _read_solution(sim_id)
        res.idMap = id_map
        tmp_f_type = data.fieldType
        data.fieldType = None
        data.geomTypes = [_SCHEMA.constants.geomTypeLines]
        data.method = 'get_geom'
        data.viewType = _SCHEMA.constants.viewTypeObjects
        new_res = get_application_data(data)
        res.data += new_res.data
        data.fieldType = tmp_f_type
        return res

    if data.method == 'get_field_integrals':
        return _generate_field_integrals(g_id, data.fieldPaths)
    if data.method == 'get_kick_map':
        return _read_or_generate_kick_map(g_id, data)
    if data.method == 'get_geom':
        g_types = data.get(
            'geomTypes',
            [_SCHEMA.constants.geomTypeLines, _SCHEMA.constants.geomTypePolys]
        )
        g_types.extend(['center', 'name', 'size', 'id'])
        res = _read_or_generate(g_id, data)
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
                _BEAM_AXIS_ROTATIONS[data.beamAxis],
                file_path
            )
        elif data.exportType == 'csv':
            return _save_field_csv(
                data.fieldType,
                vectors,
                _BEAM_AXIS_ROTATIONS[data.beamAxis],
                file_path
            )
        elif data.exportType == 'SRW':
            return _save_field_srw(
                data.fieldType,
                data.gap,
                vectors,
                _BEAM_AXIS_ROTATIONS[data.beamAxis],
                file_path
            )
        return res


def get_data_file(run_dir, model, frame, options=None, **kwargs):
    assert model in _REPORTS, f'unknown report: {model}'
    name = simulation_db.read_json(
        run_dir.join(template_common.INPUT_BASE_NAME)
    ).models.simulation.name
    if model == 'kickMap':
        sfx = (options.suffix or 'sdds') if options and 'suffix' in options else 'sdds'
        sim_id = simulation_db.sid_from_compute_file(
            pkio.py_path(f'{run_dir}/{_KICK_FILE}')
        )
        km_dict = _read_kick_map(sim_id)
        f = f'{model}.{sfx}'
        if sfx == 'sdds':
            _save_kick_map_sdds(name, km_dict.x, km_dict.y, km_dict.h, km_dict.v, f)
        if sfx == 'txt':
            pkio.write_text(f'{run_dir}/{f}', km_dict.txt)
        return f


def new_simulation(data, new_simulation_data):
    data.models.simulation.beamAxis = new_simulation_data.beamAxis
    data.models.simulation.enableKickMaps = new_simulation_data.enableKickMaps
    data.models.geometry.name = new_simulation_data.name
    data.models.geometry.id = str(uuid.uuid4())
    if new_simulation_data.get('dmpImportFile', None):
        data.models.simulation.dmpImportFile = new_simulation_data.dmpImportFile
    beam_axis = new_simulation_data.beamAxis
    if new_simulation_data.get('magnetType', 'freehand') == 'undulator':
        _build_undulator(data.models.geometry, beam_axis)
        data.models.simulation.enableKickMaps = '1'
        _update_kickmap(data.models.kickMap, data.models.hybridUndulator, beam_axis)


def python_source_for_model(data):
    return _generate_parameters_file(data, True)


def write_parameters(data, run_dir, is_parallel):
    sim_id = data.simulationId
    if data.report in _SIM_REPORTS:
        # remove centrailzed geom files
        pkio.unchecked_remove(
            _geom_file(sim_id),
            #_get_res_file(sim_id, _GEOM_FILE, run_dir=_SIM_DATA.compute_model('solver')),
            _get_res_file(sim_id, _GEOM_FILE),
            #_dmp_file(sim_id)
        )
    if data.report == 'kickMap':
        #pkio.unchecked_remove(_get_res_file(sim_id, _KICK_FILE, run_dir='kickMap'))
        pkio.unchecked_remove(_get_res_file(sim_id, _KICK_FILE))
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data, False),
    )


def _add_obj_lines(field_data, obj):
    for d in obj.data:
        field_data.data.append(PKDict(lines=d.lines))


def _build_clone_xform(num_copies, alt_fields, transforms):
    tx = _build_geom_obj('cloneTransform')
    tx.numCopies = num_copies
    tx.alternateFields = alt_fields
    tx.transforms = transforms
    return tx


def _build_cuboid(
        center=None, size=None, segments=None, material=None, matFile=None,
        magnetization=None, rem_mag=None, name=None, color=None
    ):
    return _update_cuboid(
        _build_geom_obj('box', obj_name=name),
        center or [0.0, 0.0, 0.0],
        size or [1.0, 1.0, 1.0],
        segments or [1, 1, 1],
        material,
        matFile,
        magnetization or [0.0, 0.0, 0.0],
        rem_mag or 0.0,
        color
    )


# have to include points for file type?
def _build_field_file_pts(f_path):
    pts_file = _SIM_DATA.lib_file_abspath(_SIM_DATA.lib_file_name_with_type(
        f_path.fileName,
        _SCHEMA.constants.pathPtsFileType
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


def _build_geom_obj(model_name, obj_name=None, obj_color=None):
    o_id = str(uuid.uuid4())
    o = PKDict(
        name=obj_name if obj_name else f'{model_name}.{o_id}',
        model=model_name,
        id=o_id,
        color=obj_color,
    )
    _SIM_DATA.update_model_defaults(o, model_name)
    return o


def _build_group(members, name=None):
    g = _build_geom_obj('geomGroup', obj_name=name)
    return _update_group(g, members, do_replace=True)


def _build_symm_xform(plane, point, type):
    tx = _build_geom_obj('symmetryTransform')
    tx.symmetryPlane = ','.join([str(x) for x in plane])
    tx.symmetryPoint = ','.join([str(x) for x in point])
    tx.symmetryType = type
    return tx


def _build_translate_clone(dist):
    tx = _build_geom_obj('translateClone')
    tx.distance = ','.join([str(x) for x in dist])
    return tx


def _build_undulator(geom, beam_axis):

    # arrange objects
    geom.objects = []
    half_pole = _build_cuboid(name='Half Pole')
    geom.objects.append(half_pole)
    magnet_block = _build_cuboid(name='Magnet Block')
    geom.objects.append(magnet_block)
    pole = _build_cuboid(name='Pole')
    geom.objects.append(pole)
    mag_pole_grp = _build_group([magnet_block, pole], name='Magnet-Pole Pair')
    geom.objects.append(mag_pole_grp)
    magnet_cap = _build_cuboid(name='End Block')
    geom.objects.append(magnet_cap)
    oct_grp = _build_group([half_pole, mag_pole_grp, magnet_cap], name='Octant')
    geom.objects.append(oct_grp)

    return _update_geom_from_undulator(
        geom,
        _build_geom_obj('hybridUndulator', obj_name=geom.name),
        beam_axis
    )


# deep copy of an object, but with a new id
def _copy_geom_obj(o):
    import copy
    o_copy = copy.deepcopy(o)
    o_copy.id = str(uuid.uuid4())
    return o_copy


_FIELD_PT_BUILDERS = {
    'circle': _build_field_circle_pts,
    'fieldMap': _build_field_map_pts,
    'file': _build_field_file_pts,
    'line': _build_field_line_pts,
    'manual': _build_field_manual_pts,
}


def _dmp_file(sim_id):
    return _get_res_file(sim_id, _DMP_FILE)
    #return _get_lib_file(sim_id, _DMP_FILE)


def _fields_file(sim_id):
    return _get_res_file(sim_id, _FIELDS_FILE)
    #return _get_lib_file(sim_id, _FIELDS_FILE)


def _find_obj_by_name(obj_arr, obj_name):
    a = [o for o in obj_arr if o.name == obj_name]
    return a[0] if a else None


def _generate_field_data(g_id, name, field_type, field_paths):
    if field_type == radia_tk.FIELD_TYPE_MAG_M:
        f = radia_tk.get_magnetization(g_id)
    elif field_type in radia_tk.POINT_FIELD_TYPES:
        f = radia_tk.get_field(g_id, field_type, _build_field_points(field_paths))
    return radia_tk.vector_field_to_data(g_id, name, f, radia_tk.FIELD_UNITS[field_type])


def _generate_field_integrals(g_id, f_paths):
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
            for i_type in radia_tk.INTEGRABLE_FIELD_TYPES:
                res[p.name][i_type] = radia_tk.field_integral(g_id, i_type, p1, p2)
        return res
    except RuntimeError as e:
        pkdc('Radia error {}', e.message)
        return PKDict(error=e.message)


def _generate_data(g_id, in_data, add_lines=True):
    try:
        o = _generate_obj_data(g_id, in_data.name)
        if in_data.viewType == _SCHEMA.constants.viewTypeObjects:
            return o
        elif in_data.viewType == _SCHEMA.constants.viewTypeFields:
            g = _generate_field_data(
                g_id, in_data.name, in_data.fieldType, in_data.get('fieldPaths', None)
            )
            if add_lines:
                _add_obj_lines(g, o)
            return g
    except RuntimeError as e:
        pkdc('Radia error {}', e.message)
        return PKDict(error=e.message)


def _generate_kick_map(g_id, model):
    km = radia_tk.kick_map(
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
    return radia_tk.geom_to_data(g_id, name=name)


def _generate_parameters_file(data, for_export):
    import jinja2

    report = data.get('report', '')
    rpt_out = f'{_REPORT_RES_MAP.get(report, report)}'
    res, v = template_common.generate_parameters_file(data)
    sim_id = data.get('simulationId', data.models.simulation.simulationId)
    g = data.models.geometry

    v.dmpOutputFile = _DMP_FILE if for_export else _dmp_file(sim_id)
    if 'dmpImportFile' in data.models.simulation:
        v.dmpImportFile = data.models.simulation.dmpImportFile if for_export else \
            simulation_db.simulation_lib_dir(SIM_TYPE).join(
                f'{_SCHEMA.constants.radiaDmpFileType}.{data.models.simulation.dmpImportFile}'
            )
    v.isExample = data.models.simulation.get('isExample', False)
    v.magnetType = data.models.simulation.get('magnetType', 'freehand')
    if v.magnetType == 'undulator':
        _update_geom_from_undulator(g, data.models.hybridUndulator, data.models.simulation.beamAxis)
    v.objects = g.get('objects', [])
    _validate_objects(v.objects)
    # read in h-m curves if applicable
    for o in v.objects:
        o.h_m_curve = _read_h_m_file(o.materialFile) if \
            o.get('material', None) and o.material == 'custom' and \
            o.get('materialFile', None) and o.materialFile else None
    v.geomName = g.name
    #v.geomId = g.id
    disp = data.models.magnetDisplay
    v_type = disp.viewType

    # for rendering conveneince
    v.VIEW_TYPE_OBJ = _SCHEMA.constants.viewTypeObjects
    v.VIEW_TYPE_FIELD = _SCHEMA.constants.viewTypeFields
    v.FIELD_TYPE_MAG_M = radia_tk.FIELD_TYPE_MAG_M
    v.POINT_FIELD_TYPES = radia_tk.POINT_FIELD_TYPES
    v.INTEGRABLE_FIELD_TYPES = radia_tk.INTEGRABLE_FIELD_TYPES

    f_type = None
    if v_type not in VIEW_TYPES:
        raise ValueError('Invalid view {} ({})'.format(v_type, VIEW_TYPES))
    v.viewType = v_type
    v.dataFile = _GEOM_FILE if for_export else _get_res_file(sim_id, f'{rpt_out}.h5')
    #v.dataFile = _GEOM_FILE if for_export else f'{rpt_out}.h5'
    if v_type == _SCHEMA.constants.viewTypeFields:
        f_type = disp.fieldType
        if f_type not in radia_tk.FIELD_TYPES:
            raise ValueError(
                'Invalid field {} ({})'.format(f_type, radia_tk.FIELD_TYPES)
            )
        v.fieldType = f_type
        v.fieldPaths = data.models.fieldPaths.get('paths', [])
        v.fieldPoints = _build_field_points(data.models.fieldPaths.get('paths', []))
    v.kickMap = data.models.get('kickMap', None)
    if 'solver' in report or for_export:
        v.doSolve = True
        v.gId = _get_g_id(sim_id)
        s = data.models.solver
        v.solvePrec = s.precision
        v.solveMaxIter = s.maxIterations
        v.solveMethod = s.method
    if 'reset' in report:
        radia_tk.reset()
        data.report = 'geometry'
        return _generate_parameters_file(data, False)
    v.h5FieldPath = _geom_h5_path(_SCHEMA.constants.viewTypeFields, f_type)
    v.h5KickMapPath = _H5_PATH_KICK_MAP
    v.h5ObjPath = _geom_h5_path(_SCHEMA.constants.viewTypeObjects)
    v.h5SolutionPath = _H5_PATH_SOLUTION

    j_file = RADIA_EXPORT_FILE if for_export else f'{rpt_out}.py'
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        j_file,
        jinja_env=PKDict(loader=jinja2.PackageLoader('sirepo', 'template'))
    )


def _geom_file(sim_id):
    return _get_res_file(sim_id, _GEOM_FILE)


def _geom_h5_path(view_type, field_type=None):
    p = f'geometry/{view_type}'
    if field_type is not None:
        p += f'/{field_type}'
    return p


def _get_g_id(sim_id):
    with open(str(_dmp_file(sim_id)), 'rb') as f:
        return radia_tk.load_bin(f.read())


def _get_res_file(sim_id, filename, run_dir=_GEOM_DIR):
    return simulation_db.simulation_dir(SIM_TYPE, sim_id) \
        .join(run_dir).join(filename)


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


def _kick_map_plot(sim_id, model):
    from sirepo import srschema
    g_id = _get_g_id(sim_id)
    component = model.component
    km = _generate_kick_map(g_id, model)
    if not km:
        return None
    z = km[component]
    return PKDict(
        title=f'{srschema.get_enums(_SCHEMA, "KickMapComponent")[component]} (T2m2)',
        x_range=[km.x[0], km.x[-1], len(z)],
        y_range=[km.y[0], km.y[-1], len(z[0])],
        x_label='x [mm]',
        y_label='y [mm]',
        z_matrix=z,
    )


def _read_h5_path(sim_id, run_dir, filename, h5path):
    try:
        with h5py.File(_get_res_file(sim_id, filename), 'r') as hf:
            return template_common.h5_to_dict(hf, path=h5path)
        #with h5py.File(_get_res_file(sim_id, filename, run_dir=run_dir), 'r') as hf:
        #    return template_common.h5_to_dict(hf, path=h5path)
    except IOError as e:
        if pkio.exception_is_not_found(e):
            pkdc(f'{filename} not found in {run_dir}')
            # need to generate file
            return None
    except KeyError:
        # no such path in file
        pkdc(f'path {h5path} not found in {run_dir}/{filename}')
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


def _read_data(sim_id, view_type, field_type):
    res = _read_h5_path(sim_id, _GEOM_DIR, _GEOM_FILE, _geom_h5_path(view_type, field_type))
    if res:
        res.idMap = _read_id_map(sim_id)
        res.solution = _read_solution(sim_id)
    return res


def _read_id_map(sim_id):
    return _read_h5_path(sim_id, _GEOM_DIR, _GEOM_FILE, 'idMap')


def _read_kick_map(sim_id):
    return _read_h5_path(sim_id, 'kickMap', _KICK_FILE, _H5_PATH_KICK_MAP)


def _read_or_generate(g_id, data):
    f_type = data.get('fieldType', None)
    res = _read_data(data.simulationId, data.viewType, f_type)
    if res:
        return res
    # No such file or path, so generate the data and write to the existing file
    with h5py.File(_geom_file(data.simulationId), 'a') as hf:
        template_common.dict_to_h5(
            _generate_data(g_id, data, add_lines=False),
            hf,
            path=_geom_h5_path(data.viewType, f_type)
        )
    return get_application_data(data)


def _read_or_generate_kick_map(g_id, data):
    res = _read_kick_map(data.simulationId)
    if res:
        return res
    return _generate_kick_map(g_id, data.model)


def _read_solution(sim_id):
    s = _read_h5_path(
        sim_id,
        _SIM_DATA.compute_model('solver'),
        _GEOM_FILE,
        _H5_PATH_SOLUTION
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


def _validate_objects(objects):
    from numpy import linalg
    for o in objects:
        if 'material' in o and o.material in _SCHEMA.constants.anisotropicMaterials:
            if numpy.linalg.norm(sirepo.util.split_comma_delimited_string(o.magnetization, float)) == 0:
                raise ValueError(
                    f'{o.name}: anisotropic material {o.material} requires non-0 magnetization'
                )


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


def _update_cuboid(b, center, size, segments, material, mat_file, magnetization, rem_mag, color):
    b.center = ','.join([str(x) for x in center])
    b.color = color
    b.magnetization = ','.join([str(x) for x in magnetization])
    b.remanentMag = rem_mag
    b.material = material
    b.materialFile = mat_file
    b.size = ','.join([str(x) for x in size])
    b.division = ','.join([str(x) for x in segments])
    return b


def _update_geom_from_undulator(geom, und, beam_axis):

    # "Length" is along the beam axis; "Height" is along the gap axis; "Width" is
    # along the remaining axis
    beam_dir = numpy.array(_BEAM_AXIS_VECTORS[beam_axis])
    # assign a valid gap direction if the user provided an invalid one
    if und.gapAxis == beam_axis:
        und.gapAxis = _GAP_AXIS_MAP[beam_axis]
    gap_dir = numpy.array(_BEAM_AXIS_VECTORS[und.gapAxis])

    # we don't care about the direction of the cross product
    width_dir = abs(numpy.cross(beam_dir, gap_dir))

    dir_matrix = numpy.array([width_dir, gap_dir, beam_dir])

    pole_x = sirepo.util.split_comma_delimited_string(und.poleCrossSection, float)
    mag_x = sirepo.util.split_comma_delimited_string(und.magnetCrossSection, float)

    # put the magnetization and segmentation in the correct order
    pole_mag = dir_matrix.dot(
        sirepo.util.split_comma_delimited_string(und.poleMagnetization, float)
    )
    mag_mag = dir_matrix.dot(
        sirepo.util.split_comma_delimited_string(und.magnetMagnetization, float)
    )
    pole_segs = dir_matrix.dot(
        sirepo.util.split_comma_delimited_string(und.poleDivision, int)
    )
    mag_segs = dir_matrix.dot(
        sirepo.util.split_comma_delimited_string(und.magnetDivision, int)
    )

    # pole and magnet dimensions, including direction
    pole_dim = PKDict(
        width=width_dir * pole_x[0],
        height=gap_dir * pole_x[1],
        length=beam_dir * und.poleLength,
    )
    magnet_dim = PKDict(
        width=width_dir * mag_x[0],
        height=gap_dir * mag_x[1],
        length=beam_dir * (und.periodLength / 2 - pole_dim.length),
    )

    # convenient constants
    pole_dim_half = PKDict({k:v / 2 for k, v in pole_dim.items()})
    magnet_dim_half = PKDict({k: v / 2 for k, v in magnet_dim.items()})
    gap_half_height = gap_dir * und.gap / 2
    gap_offset = gap_dir * und.gapOffset

    pole_transverse_ctr = pole_dim_half.width / 2 - \
                          (pole_dim_half.height + gap_half_height)
    magnet_transverse_ctr = magnet_dim_half.width / 2 - \
                            (gap_offset + magnet_dim_half.height + gap_half_height)

    pos = pole_dim_half.length / 2
    half_pole = _update_cuboid(
        _find_obj_by_name(geom.objects, 'Half Pole'),
        pole_transverse_ctr + pos,
        pole_dim_half.width + pole_dim.height + pole_dim_half.length,
        pole_segs,
        und.poleMaterial,
        und.poleMaterialFile,
        pole_mag,
        und.poleRemanentMag,
        und.poleColor
    )

    pos += (pole_dim_half.length / 2 + magnet_dim_half.length)
    magnet_block = _update_cuboid(
        _find_obj_by_name(geom.objects, 'Magnet Block'),
        magnet_transverse_ctr + pos,
        magnet_dim_half.width + magnet_dim.height + magnet_dim.length,
        mag_segs,
        und.magnetMaterial,
        und.magnetMaterialFile,
        mag_mag,
        und.magnetRemanentMag,
        und.magnetColor
    )

    pos += (pole_dim_half.length + magnet_dim_half.length)
    pole = _update_cuboid(
        _find_obj_by_name(geom.objects, 'Pole'),
        pole_transverse_ctr + pos,
        pole_dim_half.width + pole_dim.height + pole_dim.length,
        pole_segs,
        und.poleMaterial,
        und.poleMaterialFile,
        pole_mag,
        und.poleRemanentMag,
        und.poleColor
    )

    mag_pole_grp = _find_obj_by_name(geom.objects, 'Magnet-Pole Pair')
    mag_pole_grp.transforms = [] if und.numPeriods < 2 else \
        [_build_clone_xform(
            und.numPeriods - 1,
            True,
            [_build_translate_clone(beam_dir * und.periodLength / 2)]
        )]

    pos = pole_dim_half.length + \
          magnet_dim_half.length / 2 + \
          beam_dir * und.numPeriods * und.periodLength / 2
    magnet_cap = _update_cuboid(
        _find_obj_by_name(geom.objects, 'End Block'),
        magnet_transverse_ctr + pos,
        magnet_dim_half.width + magnet_dim.height + magnet_dim_half.length,
        mag_segs,
        und.magnetMaterial,
        und.magnetMaterialFile,
        (-1) ** und.numPeriods * mag_mag,
        und.magnetRemanentMag,
        und.magnetColor
    )

    oct_grp = _find_obj_by_name(geom.objects, 'Octant')
    oct_grp.transforms = [
        _build_symm_xform(width_dir, _ZERO, 'perpendicular'),
        _build_symm_xform(gap_dir, _ZERO, 'parallel'),
        _build_symm_xform(beam_dir, _ZERO, 'perpendicular'),
    ]
    return oct_grp


def _update_group(g, members, do_replace=False):
    if do_replace:
        g.members = []
    for m in members:
        m.groupId = g.id
        g.members.append(m.id)
    return g


def _update_kickmap(km, und, beam_axis):
    km.direction = ','.join([str(x) for x in _BEAM_AXIS_VECTORS[beam_axis]])
    km.transverseDirection = ','.join(
        [str(x) for x in _BEAM_AXIS_VECTORS[_GAP_AXIS_MAP[beam_axis]]])
    km.transverseRange1 = und.gap
    km.numPeriods = und.numPeriods
    km.periodLength = und.periodLength


_H5_PATH_KICK_MAP = _geom_h5_path('kickMap')
_H5_PATH_SOLUTION = _geom_h5_path('solution')
