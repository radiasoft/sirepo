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
from sirepo.template import rsradia_examples
import h5py
import sirepo.sim_data
import sirepo.util
import time


_DMP_FILE = 'geom.dat'
_GEOM_DIR = 'geometry'
_GEOM_FILE = 'geom.h5'
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
    pkdp('sim_in {}', sim_in)
    if 'geometry' in sim_in.report:
        v_type = sim_in.models.magnetDisplay.viewType
        f_type = sim_in.models.magnetDisplay.fieldType if v_type == VIEW_TYPE_FIELD\
            else None
        #with h5py.File(_geom_file(sim_in.simulationId, v_type), 'r') as hf:
        with h5py.File(_geom_file(sim_in.simulationId), 'r') as hf:
            #g = template_common.h5_to_dict(hf, path='geometry')
            g = template_common.h5_to_dict(hf, path=_geom_h5_path(v_type, f_type))
            simulation_db.write_result(g, run_dir=run_dir)
        return
    simulation_db.write_result(PKDict(), run_dir=run_dir)


# if the file exists but the data we seek does not, have Radia generate it here.  We
# should only have to blow away the file after a solve (???)
def get_application_data(data, **kwargs):
    import binascii
    if 'method' in data and data.method == 'get_geom':
        g_id = -1
        try:
            with open(str(_dmp_file(data.simulationId)), 'rb') as f:
                b = f.read()
                #pkdp('GOT BIN {} FROM FILE', binascii.b2a_base64(b))
                g_id = radia_tk.load_bin(b)
                #f_arr = radia_tk.get_field(g_id, 'B', [0, 0, 0])
                #pkdp('GOT GID {} b {} FROM FILE', g_id, f_arr)
        except IOError as e:
            print('ERR {} FROM FILE'.format(e))
            pass
        g = {}
        f = _geom_file(data.simulationId)
        p = _geom_h5_path(data.viewType, data.get('fieldType', None))
        try:
            #with h5py.File(_geom_file(data.simulationId, data.viewType), 'r') as hf:
            with h5py.File(f, 'r') as hf:
                g = template_common.h5_to_dict(hf, path=p)
                return g
        except IOError:
            return {}
        except KeyError:
            if data.viewType == VIEW_TYPE_OBJ:
                g = _generate_obj_data(g_id, data.name)
            elif data.viewType == VIEW_TYPE_FIELD:
                g = _generate_field_data(
                    g_id, data.name, data.fieldType, data.fieldPoints
                )
            # write the new data to the existing file
            with h5py.File(f, 'a') as hf:
                template_common.dict_to_h5(g, hf, path=p)
            return g

    raise RuntimeError('unknown application data method: {}'.format(data['method']))


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _build_geom(data):
    g_name = data.models.geometry.name
    if data.models.simulation.isExample:
        return rsradia_examples.build(g_name)
    else:
        #TODO(mvk): build from model data
        return -1


def _dmp_file(sim_id):
    return simulation_db.simulation_dir(SIM_TYPE, sim_id) \
        .join('geometry').join(_DMP_FILE)


def _generate_field_data(g_id, name, f_type, f_pts):
    if f_type == radia_tk.FIELD_TYPE_MAG_M:
        f = radia_tk.get_magnetization(g_id)
    elif f_type in radia_tk.POINT_FIELD_TYPES:
        f = radia_tk.get_field(g_id, f_type, f_pts)
    return radia_tk.vector_field_to_data(g_id, name, f, radia_tk.FIELD_UNITS[f_type])


def _generate_obj_data(g_id, name):
    return radia_tk.geom_to_data(g_id, name=name)


def _generate_parameters_file(data):
    report = data.get('report', '')
    pkdp('RPT {}', report)
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
    #v['dataFile'] = _geom_file(data.simulationId, disp.viewType)
    v['dataFile'] = _geom_file(data.simulationId)
    if v_type == VIEW_TYPE_FIELD:
        f_type = disp.fieldType
        if f_type not in radia_tk.FIELD_TYPES:
            raise ValueError(
                'Invalid field {} ({})'.format(f_type, radia_tk.FIELD_TYPES)
            )
        v['fieldType'] = f_type
        v['fieldPoints'] = data.models.fieldPaths.fieldPoints
    if 'solver' in report:
        v['doSolve'] = True
        s = data.models.solver
        v['solvePrec'] = s.precision
        v['solveMaxIter'] = s.maxIterations
        v['solveMethod'] = s.method
    if 'reset' in report:
        res = radia_tk.reset()
        pkdp('RESET RES {}', res)
        data.report = 'geometry'
        return _generate_parameters_file(data)
    v['h5ObjPath'] = _geom_h5_path(VIEW_TYPE_OBJ)
    v['h5FieldPath'] = _geom_h5_path(VIEW_TYPE_FIELD, f_type)

    return template_common.render_jinja(
        SIM_TYPE,
        v,
        GEOM_PYTHON_FILE,
    )

#def _geom_file(sim_id, v_type):
def _geom_file(sim_id):
    return simulation_db.simulation_dir(SIM_TYPE, sim_id) \
        .join(_GEOM_DIR).join(_GEOM_FILE)
        #.join(_GEOM_DIR).join('geom_' + v_type + '.h5')


def _geom_h5_path(v_type, f_type=None):
    p = 'geometry/' + v_type
    if f_type is not None:
        p += '/' + f_type
    return p


