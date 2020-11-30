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

_BEAM_AXIS_ROTATIONS = PKDict(
    x=Rotation.from_matrix([[0, 0, 1], [0, 1, 0], [-1, 0, 0]]),
    y=Rotation.from_matrix([[1, 0, 0], [0, 0, -1], [0, 1, 0]]),
    z=Rotation.from_matrix([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
)

_DMP_FILE = 'geom.dat'
_FIELD_MAP_COLS = ['x', 'y', 'z', 'Bx', 'By', 'Bz']
_FIELD_MAP_UNITS = ['m', 'm', 'm', 'T', 'T', 'T']
_FIELDS_FILE = 'fields.h5'
_GEOM_DIR = 'geometry'
_GEOM_FILE = 'geom.h5'
_H5_PATH_KICK_MAP = 'kickMap'
_H5_PATH_SOLUTION = 'solution'
_KICK_FILE = 'kickMap.h5'
_METHODS = ['get_field', 'get_field_integrals', 'get_geom', 'get_kick_map', 'save_field']
_REPORTS = ['geometry', 'kickMapHoriz', 'reset']
_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()
_SDDS_INDEX = 0

GEOM_PYTHON_FILE = 'geom.py'
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
        if f_type in radia_tk.POINT_FIELD_TYPES:
            #TODO(mvk): won't work for subsets of available paths, figure that out
            pass
            #try:
            #    res = _read_data(sim_id, data.viewType, f_type)
            #except KeyError:
            #    res = None
            #if res:
            #    v = [d.vectors.vertices for d in res.data if _SCHEMA.constants.geomTypeVectors in d]
            #    old_pts = [p for a in v for p in a]
            #    new_pts = _build_field_points(data.fieldPaths)
            #    if len(old_pts) == len(new_pts) and numpy.allclose(new_pts, old_pts):
            #        return res
        #return _read_or_generate(g_id, data)
        res = _generate_field_data(
            g_id, data.name, f_type, data.get('fieldPaths', None)
        )
        res.solution = _read_solution(sim_id)
        res.idMap = id_map
        # moved addition of lines from client
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
        g_types.extend(['center', 'name', 'size'])
        res = _read_or_generate(g_id, data)
        rd = res.data if 'data' in res else []
        res.data = [{k: d[k] for k in d.keys() if k in g_types} for d in rd]
        res.idMap = id_map
        return res
    if data.method == 'save_field':
        data.method = 'get_field'
        res = get_application_data(data)
        file_path = simulation_db.simulation_lib_dir(SIM_TYPE).join(
            sim_id + '_' + res.name + '.' + data.fileType
        )
        # we save individual field paths, so there will be one item in the list
        vectors = res.data[0].vectors
        if data.fileType == 'sdds':
            return _save_fm_sdds(
                res.name,
                vectors,
                _BEAM_AXIS_ROTATIONS[data.beamAxis],
                file_path
            )
        elif data.fileType == 'csv':
            return _save_field_csv(
                data.fieldType,
                vectors,
                _BEAM_AXIS_ROTATIONS[data.beamAxis],
                file_path
            )
        return res


def new_simulation(data, new_simulation_data):
    data.models.simulation.beamAxis = new_simulation_data.beamAxis
    data.models.geometry.name = new_simulation_data.name
    if new_simulation_data.get('dmpImportFile', None):
        data.models.simulation.dmpImportFile = new_simulation_data.dmpImportFile



def python_source_for_model(data, model):
    return _generate_parameters_file(data, True)


def write_parameters(data, run_dir, is_parallel):
    # remove centrailzed geom files
    pkdp('DELETING GEOM AMD DUMP')
    pkio.unchecked_remove(_geom_file(data.simulationId), _dmp_file(data.simulationId))
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data, False),
    )


def _add_obj_lines(field_data, obj):
    for d in obj.data:
        field_data.data.append(PKDict(lines=d.lines))


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


_FIELD_PT_BUILDERS = {
    'circle': _build_field_circle_pts,
    'fieldMap': _build_field_map_pts,
    'file': _build_field_file_pts,
    'line': _build_field_line_pts,
    'manual': _build_field_manual_pts,
}


def _dmp_file(sim_id):
    return _get_res_file(sim_id, _DMP_FILE)


def _fields_file(sim_id):
    return _get_res_file(sim_id, _FIELDS_FILE)


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
    return radia_tk.geom_to_data(g_id, name=name, g_type=_SCHEMA.constants.viewTypeObjects)


def _generate_parameters_file(data, for_export):
    import jinja2

    report = data.get('report', '')
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
    v.objects = g.get('objects', [])
    # read in h-m curves if applicable
    for o in v.objects:
        o.h_m_curve = _read_h_m_file(o.materialFile) if \
            o.get('material', None) and o.material == 'custom' and \
            o.get('materialFile', None) and o.materialFile else None
    v.geomName = g.name
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
    v.dataFile = _GEOM_FILE if for_export else _geom_file(sim_id)
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

    j_file = RADIA_EXPORT_FILE if for_export else GEOM_PYTHON_FILE
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        j_file,
        jinja_env=PKDict(loader=jinja2.PackageLoader('sirepo', 'template'))
    )


def _geom_file(sim_id):
    return _get_res_file(sim_id, _GEOM_FILE)


def _geom_h5_path(view_type, field_type=None):
    p = 'geometry/' + view_type
    if field_type is not None:
        p += '/' + field_type
    return p


def _get_g_id(sim_id):
    with open(str(_dmp_file(sim_id)), 'rb') as f:
        return radia_tk.load_bin(f.read())


def _get_res_file(sim_id, filename):
    return simulation_db.simulation_dir(SIM_TYPE, sim_id) \
        .join(_GEOM_DIR).join(filename)


def _get_sdds():
    if _cfg.sdds is None:
        _cfg.sdds = sdds.SDDS(_SDDS_INDEX)
        # TODO(mvk): elegant cannot read these binary files; figure that out
        # _cfg.sdds = sd.SDDS_BINARY
        for i, n in enumerate(_FIELD_MAP_COLS):
            # name, symbol, units, desc, format, type, len)
            _cfg.sdds.defineColumn(
                n, '', _FIELD_MAP_UNITS[i], n, '', _cfg.sdds.SDDS_DOUBLE, 0
            )
    return _cfg.sdds


def _read_h5_path(sim_id, h5path):
    try:
        with h5py.File(_geom_file(sim_id), 'r') as hf:
            return template_common.h5_to_dict(hf, path=h5path)
    except IOError as e:
        if pkio.exception_is_not_found(e):
            # need to generate file
            return None
    except KeyError:
        # no such path in file
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
    res = _read_h5_path(sim_id, _geom_h5_path(view_type, field_type))
    if res:
        res.solution = _read_solution(sim_id)
    return res


def _read_id_map(sim_id):
    return _read_h5_path(sim_id, 'idMap')


#def _read_kick_map(sim_id):
#    return _read_h5_path(sim_id, _H5_PATH_KICK_MAP)


def _read_or_generate_kick_map(g_id, data):
    #res = None  #_read_kick_map(data.simulationId)
    #if res:
    #    return res
    return _generate_kick_map(g_id, data.model)
    #km = _generate_kick_map(g_id, data.model)
    #p = _geom_h5_path(_H5_PATH_KICK_MAP)
    #pkdp('GOT KM {} WRITE TO {}', km, _geom_h5_path(_H5_PATH_KICK_MAP))
    #with h5py.File(_geom_file(data.simulationId), 'a') as hf:
    #    template_common.dict_to_h5(
    #        km, #_generate_kick_map(g_id, data.model),
    #        hf,
    #        path=p
    #    )
    #return _read_kick_map(data.simulationId)


#def _kick_map_plot(sim_id, component):
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


def _read_solution(sim_id):
    s = _read_h5_path(sim_id, _H5_PATH_SOLUTION)
    if not s:
        return None
    return PKDict(
        steps=s[3],
        time=s[0],
        maxM=s[1],
        maxH=s[2]
    ) if s else s


def _rotate_flat_vector_list(vectors, scipy_rotation):
    return scipy_rotation.apply(numpy.reshape(vectors, (-1, 3)))


def _save_field_csv(field_type, vectors, scipy_rotation, path):
    # reserve first line for a header
    data = ['x,y,z,' + field_type + 'x,' + field_type + 'y,' + field_type + 'z']
    # mm -> m, rotate so the beam axis is aligned with z
    pts = 0.001 * _rotate_flat_vector_list(vectors.vertices, scipy_rotation).flatten()
    mags = numpy.array(vectors.magnitudes)
    dirs = _rotate_flat_vector_list(vectors.directions, scipy_rotation).flatten()
    for i in range(len(mags)):
        j = 3 * i
        r = pts[j:j + 3]
        r = numpy.append(r, mags[i] * dirs[j:j + 3])
        data.append(','.join(map(str, r)))
    pkio.write_text(path, '\n'.join(data))
    return path


def _save_fm_sdds(name, vectors, scipy_rotation, path):
    s = _get_sdds()
    s.setDescription('Field Map for ' + name, 'x(m), y(m), z(m), Bx(T), By(T), Bz(T)')
    # mm -> m
    pts = 0.001 * _rotate_flat_vector_list(vectors.vertices, scipy_rotation)
    ind = numpy.lexsort((pts[:, 0], pts[:, 1], pts[:, 2]))
    pts = pts[ind]
    mag = vectors.magnitudes
    dirs = _rotate_flat_vector_list(vectors.directions, scipy_rotation)
    v = [mag[j // 3] * d for (j, d) in enumerate(dirs)]
    fld = numpy.reshape(v, (-1, 3))[ind]
    # can we use tmp_dir before it gets deleted?
    # with simulation_db.tmp_dir(True) as out_dir:
    col_data = []
    for i in range(3):
        col_data.append([pts[:, i].tolist()])
    for i in range(3):
        col_data.append([fld[:, i].tolist()])
    for i, n in enumerate(_FIELD_MAP_COLS):
        s.setColumnValueLists(n, col_data[i])
    s.save(str(path))
    return path


_DATA_FILES = PKDict(
    geometry=_GEOM_FILE,
    kickMap=_KICK_FILE
)
_H5_PATH_KICK_MAP = _geom_h5_path('kickMap')
_H5_PATH_SOLUTION = _geom_h5_path('solution')
