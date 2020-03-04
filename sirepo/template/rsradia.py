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
    if 'geometry' in sim_in.report:
        with h5py.File(_geom_file(), 'r') as hf:
            g = template_common.h5_to_dict(hf, path='geometry')
            simulation_db.write_result(g, run_dir=run_dir)
        return
    simulation_db.write_result(PKDict(), run_dir=run_dir)


def get_application_data(data, **kwargs):
    if 'method' in data and data.method == 'get_geom':
        geom_file = simulation_db.simulation_dir(SIM_TYPE, data.simulationId) \
            .join('geometry').join(_GEOM_FILE)
        try:
            with h5py.File(geom_file, 'r') as hf:
                return template_common.h5_to_dict(hf, path='geometry')
        except IOError:
            return {}
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


def _generate_parameters_file(data):
    report = data.get('report', '')
    pkdp('RPT {}', report)
    res, v = template_common.generate_parameters_file(data)
    g = data.models.geometry

    v['dataFile'] = _geom_file()
    v['isExample'] = data.models.simulation.isExample
    v['geomName'] = g.name
    disp = data.models.magnetDisplay
    v_type = disp.viewType
    if v_type not in VIEW_TYPES:
        raise ValueError('Invalid view {} ({})'.format(v_type, VIEW_TYPES))
    v['viewType'] = v_type
    if v_type == VIEW_TYPE_FIELD:
        f_type = disp.fieldType
        if f_type not in radia_tk.FIELD_TYPES:
            raise ValueError(
                'Invalid field {} ({})'.format(f_type, radia_tk.FIELD_TYPES)
            )
        v['fieldType'] = f_type
    if 'solver' in report:
        v['doSolve'] = True
        s = data.models.solver
        v['solvePrec'] = s.precision
        v['solveMaxIter'] = s.maxIterations
        v['solveMethod'] = s.method
    if 'reset' in report:
        res = mgr.reset_geom(g.name) #radia_tk.reset()
        pkdp('RESET RES {}', res)
        data.report = 'geometry'
        return _generate_parameters_file(data)

    return template_common.render_jinja(
        SIM_TYPE,
        v,
        GEOM_PYTHON_FILE,
    )


def _geom_file():
    return '../' + _GEOM_DIR + '/' + _GEOM_FILE
