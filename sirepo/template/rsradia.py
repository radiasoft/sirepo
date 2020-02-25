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


_GEOM_DIR = 'geometry'
_GEOM_FILE = 'geom.h5'
_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

GEOM_PYTHON_FILE = 'geom.py'
MPI_SUMMARY_FILE = 'mpi-info.json'
VIEW_TYPE_OBJ = 'objects'
VIEW_TYPE_FIELD = 'fields'
VIEW_TYPES = [VIEW_TYPE_OBJ, VIEW_TYPE_FIELD]

mgr = radia_tk.RadiaGeomMgr()

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
    # change to do calcs here?  Does not seem to be a place for jinja, which appears
    # stateless
    if 'geometry' in sim_in.report:
        #simulation_db.write_result(simulation_db.read_json(GEOM_FILE), run_dir=run_dir)
        with h5py.File(_geom_file(), 'r') as hf:
        #with h5py.File(str(_SIM_DATA.lib_file_abspath(_SIM_DATA.GEOM_FILE)), 'r') as hf:
            g = template_common.h5_to_dict(hf, path='geometry')
            simulation_db.write_result(g, run_dir=run_dir)
        return
    simulation_db.write_result(PKDict(), run_dir=run_dir)


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


def _generate_parameters_file(data):
    report = data.get('report', '')
    pkdp('RPT {}', report)
    res, v = template_common.generate_parameters_file(data)
    g = data.models.geometry
    #g_id = _build_geom(data)
    v['dataFile'] = _geom_file()
    if 'geometry' in report:
        disp = data.models.magnetDisplay
        v_type = disp.viewType
        if v_type not in VIEW_TYPES:
            raise ValueError('Invalid view {} ({})'.format(v_type, VIEW_TYPES))

        g_id = mgr.get_geom(g.name)
        if g_id is None:
            pkdp('NO GEOM {}, BUILDING', g.name)
            g_id = _build_geom(data)
            mgr.add_geom(g.name, g_id)
        v['geomName'] = g.name
        v['geomId'] = g_id

        if v_type == VIEW_TYPE_OBJ:
            v['geomData'] = mgr.geom_to_data(g.name)
            #v['geomData'] = radia_tk.geom_id_to_data(g_id, name=g.name)
        elif v_type == VIEW_TYPE_FIELD:
            f_type = disp.fieldType
            if f_type not in radia_tk.FIELD_TYPES:
                raise ValueError(
                    'Invalid field {} ({})'.format(f_type, radia_tk.FIELD_TYPES)
                )
            if True:  #f_type == radia_tk.FIELD_TYPE_MAG_M:
                f = mgr.get_magnetization(g.name)
                #f = radia_tk.get_magnetization(g_id)
            #elif f_type in radia_tk.POINT_FIELD_TYPES:
            #    solve_res = mgr.get_field(
            #        g.name,
            #        f_type,
            #        get_field_points()
            #    )
            v['geomData'] = mgr.vector_field_to_data(
                g.name,
                f,
                radia_tk.FIELD_UNITS[f_type]
            )
    if 'solver' in report:
        s = data.models.solver
        res = mgr.solve_geom(g.name, s.precision, s.maxIterations, s.method)
        #res = radia_tk.solve(g_id, s.precision, s.maxIterations, s.method)
        pkdp('SOLVE RES {}', res)
        v['geomData'] = mgr.geom_to_data(g.name)
        #v['geomData'] = radia_tk.geom_to_data(g_id, name=g.name)
    if 'reset' in report:
        res = mgr.reset_geom(g.name) #radia_tk.reset()
        pkdp('RESET RES {}', res)
        data.report = 'geometry'
        return _generate_parameters_file(data)

    # add parameters (???)
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        GEOM_PYTHON_FILE,
    )


def _geom_file():
    return '../' + _GEOM_DIR + '/' + _GEOM_FILE
