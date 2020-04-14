# -*- coding: utf-8 -*-
u"""Radia execution template.

All Radia calls have to be done from here, NOT in jinja files, because otherwise the
Radia "instance" goes away and references no longer have any meaning.

:copyright: Copyright (c) 2017-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern.pkcollections import PKDict
from pykern import pkio
from pykern import pkjinja
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import template_common
from sirepo.template import radia_tk
from sirepo.template import radia_examples
import h5py
import math
import sirepo.sim_data
import sirepo.util
import time


_DMP_FILE = 'geom.dat'
_GEOM_DIR = 'geometry'
_GEOM_FILE = 'geom.h5'
_METHODS = ['get_field_integrals', 'get_geom']
_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

GEOM_PYTHON_FILE = 'geom.py'
MPI_SUMMARY_FILE = 'mpi-info.json'
VIEW_TYPE_OBJ = 'objects'
VIEW_TYPE_FIELD = 'fields'
VIEW_TYPES = [VIEW_TYPE_OBJ, VIEW_TYPE_FIELD]


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=100,
        frameCount=0,
        errors='',  #errors,
    )
    if is_running:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        res.percentComplete = 0.0  #_compute_percent_complete(data, last_element)
        return res
    #output_info = _output_info(run_dir)
    return PKDict(
        percentComplete=100,
        frameCount=1,
        outputInfo=[],  #output_info,
        lastUpdateTime=time.time(),  #output_info[0]['lastUpdateTime'],
        errors='',  #errors,
    )


def extract_report_data(run_dir, sim_in):
    if 'geometry' in sim_in.report:
        v_type = sim_in.models.magnetDisplay.viewType
        f_type = sim_in.models.magnetDisplay.fieldType if v_type == VIEW_TYPE_FIELD\
            else None
        with h5py.File(_geom_file(sim_in.simulationId), 'r') as hf:
            g = template_common.h5_to_dict(hf, path=_geom_h5_path(v_type, f_type))
            simulation_db.write_result(g, run_dir=run_dir)
        return
    simulation_db.write_result(PKDict(), run_dir=run_dir)


# if the file exists but the data we seek does not, have Radia generate it here.  We
# should only have to blow away the file after a solve (???)
def get_application_data(data, **kwargs):
    #pkdp('get_application_data from {}', data)
    if 'method' not in data:
        raise RuntimeError('no application data method')
    if data.method not in _METHODS:
        raise RuntimeError('unknown application data method: {}'.format(data.method))

    g_id = -1
    try:
        with open(str(_dmp_file(data.simulationId)), 'rb') as f:
            b = f.read()
            g_id = radia_tk.load_bin(b)
    except IOError:
        # No Radia dump file
        return {}
    if data.method == 'get_geom':
        f = _geom_file(data.simulationId)
        f_type = data.get('fieldType', None)
        #TODO(mvk): we always regenerate point field data - should do some kind
        # of hash comparison so we only regenerate when the evaluation points change
        if data.viewType == VIEW_TYPE_FIELD and f_type in radia_tk.POINT_FIELD_TYPES:
            return _generate_data(g_id, data)
        p = _geom_h5_path(data.viewType, f_type)
        try:
            with h5py.File(f, 'r') as hf:
                g = template_common.h5_to_dict(hf, path=p)
                if f_type:
                    o = template_common.h5_to_dict(hf, path=_geom_h5_path(VIEW_TYPE_OBJ))
                    for d in o.data:
                        g.data.append(PKDict(lines=d.lines))
                return g
        except IOError:
            # No geom file
            return {}
        except KeyError:
            # No such path, so generate the data and write to the existing file
            with h5py.File(f, 'a') as hf:
                template_common.dict_to_h5(
                    _generate_data(g_id, data, add_lines=False), hf, path=p
                )
            return get_application_data(data)
    if data.method == 'get_field_integrals':
        return _generate_field_integrals(g_id, data.fieldPaths)


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    # remove centrailzed geom files
    pkio.unchecked_remove(_geom_file(data.simulationId), _dmp_file(data.simulationId))
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
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
        if p.type == 'manual':
            res.extend([float(p.ptX), float(p.ptY), float(p.ptZ)])
        if p.type == 'line':
            res.extend(_build_field_line_pts(p))
        if p.type == 'circle':
            res.extend(_build_field_circle_pts(p))
        if p.type == 'file':
            res.extend(_build_field_file_pts(p))
    return res


def _build_field_line_pts(f_path):
    p1 = [float(f_path.beginX), float(f_path.beginY), float(f_path.beginZ)]
    p2 = [float(f_path.endX), float(f_path.endY), float(f_path.endZ)]
    res = p1
    r = range(len(p1))
    n = int(f_path.numPoints) - 1
    #pkdp('adding line p1 {} p2 {} N {} L {} R {}'.format(p1, p2, n + 1, len(p1), r))
    for i in range(1, n):
        res.extend(
            [p1[j] + i * (p2[j] - p1[j]) / n for j in r]
        )
    res.extend(p2)
    return res


def _build_field_circle_pts(f_path):
    ctr = [float(f_path.ctrX), float(f_path.ctrY), float(f_path.ctrZ)]
    r = float(f_path.radius)
    # theta is a rotation about the x-axis
    th = float(f_path.theta)
    # phi is a rotation about the z-axis
    phi = float(f_path.phi)
    n = int(f_path.numPoints)
    #pkdp('adding circle at {} rad {} th {} phi {} ({})'.format(ctr, r, th, phi, n))
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


def _build_geom(data):
    g_name = data.models.geometry.name
    if data.models.simulation.isExample:
        return radia_examples.build(g_name)
    else:
        #TODO(mvk): build from model data
        return -1


def _dmp_file(sim_id):
    return simulation_db.simulation_dir(SIM_TYPE, sim_id) \
        .join('geometry').join(_DMP_FILE)


def _generate_field_data(g_id, name, f_type, f_paths):
    if f_type == radia_tk.FIELD_TYPE_MAG_M:
        f = radia_tk.get_magnetization(g_id)
    elif f_type in radia_tk.POINT_FIELD_TYPES:
        f = radia_tk.get_field(g_id, f_type, _build_field_points(f_paths))
    return radia_tk.vector_field_to_data(g_id, name, f, radia_tk.FIELD_UNITS[f_type])


def _generate_field_integrals(g_id, f_paths):
    try:
        res = PKDict()
        for p in [fp for fp in f_paths if fp.type == 'line']:
            res[p.name] = PKDict()
            p1 = [float(p.beginX), float(p.beginY), float(p.beginZ)]
            p2 = [float(p.endX), float(p.endY), float(p.endZ)]
            for i_type in radia_tk.INTEGRABLE_FIELD_TYPES:
                res[p.name][i_type] = radia_tk.field_integral(g_id, i_type, p1, p2)
        return res
    except RuntimeError as e:
        pkdc('Radia error {}', e.message)
        return PKDict(error=e.message)


def _generate_data(g_id, in_data, add_lines=True):
    try:
        o = _generate_obj_data(g_id, in_data.name)
        if in_data.viewType == VIEW_TYPE_OBJ:
            return o
        elif in_data.viewType == VIEW_TYPE_FIELD:
            f_arr = _generate_field_data(
                g_id, in_data.name, in_data.fieldType, in_data.get('fieldPaths', None)
            )
            if add_lines:
                for d in o.data:
                    f_arr.data.append(PKDict(lines=d.lines))
            return f_arr
    except RuntimeError as e:
        pkdc('Radia error {}', e.message)
        return PKDict(error=e.message)


def _generate_obj_data(g_id, name):
    return radia_tk.geom_to_data(g_id, name=name)


def _generate_parameters_file(data):
    report = data.get('report', '')
    res, v = template_common.generate_parameters_file(data)
    g = data.models.geometry

    v['dmpFile'] = _dmp_file(data.simulationId)
    v['isExample'] = data.models.simulation.isExample
    v['geomName'] = g.name
    disp = data.models.magnetDisplay
    v_type = disp.viewType
    f_type = None
    if v_type not in VIEW_TYPES:
        raise ValueError('Invalid view {} ({})'.format(v_type, VIEW_TYPES))
    v['viewType'] = v_type
    v['dataFile'] = _geom_file(data.simulationId)
    if v_type == VIEW_TYPE_FIELD:
        f_type = disp.fieldType
        if f_type not in radia_tk.FIELD_TYPES:
            raise ValueError(
                'Invalid field {} ({})'.format(f_type, radia_tk.FIELD_TYPES)
            )
        v['fieldType'] = f_type
        v['fieldPoints'] = _build_field_points(data.models.fieldPaths.get('paths', []))
    if 'solver' in report:
        v['doSolve'] = True
        s = data.models.solver
        v['solvePrec'] = s.precision
        v['solveMaxIter'] = s.maxIterations
        v['solveMethod'] = s.method
    if 'reset' in report:
        radia_tk.reset()
        data.report = 'geometry'
        return _generate_parameters_file(data)
    v['h5ObjPath'] = _geom_h5_path(VIEW_TYPE_OBJ)
    v['h5FieldPath'] = _geom_h5_path(VIEW_TYPE_FIELD, f_type)

    return template_common.render_jinja(
        SIM_TYPE,
        v,
        GEOM_PYTHON_FILE,
    )


def _geom_file(sim_id):
    return simulation_db.simulation_dir(SIM_TYPE, sim_id) \
        .join(_GEOM_DIR).join(_GEOM_FILE)


def _geom_h5_path(v_type, f_type=None):
    p = 'geometry/' + v_type
    if f_type is not None:
        p += '/' + f_type
    return p


