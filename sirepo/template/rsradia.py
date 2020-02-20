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
import sirepo.sim_data
import sirepo.util


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

GEOM_FILE = 'geom.json'
GEOM_PYTHON_FILE = 'geom.py'
VIEW_TYPE_OBJ = 'objects'
VIEW_TYPE_FIELD = 'fields'
VIEW_TYPES = [VIEW_TYPE_OBJ, VIEW_TYPE_FIELD]

mgr = radia_tk.RadiaGeomMgr()


def extract_report_data(run_dir, sim_in):
    # change to do calcs here?  Does not seem to be a place for jinja, which appears
    # stateless
    if 'geometry' in sim_in.report:
        simulation_db.write_result(simulation_db.read_json(GEOM_FILE), run_dir=run_dir)
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
    #pkdp('GEN PARAMS {} V {}', data, v)
    #pkdp('GEN PARAMS M {}', data.models)
    g = data.models.geometry
    if 'geometry' in report:
        disp = data.models.magnetDisplay
        v_type = disp.viewType
        if v_type not in VIEW_TYPES:
            raise ValueError('Invalid view {} ({})'.format(v_type, VIEW_TYPES))

        g_id = mgr.get_geom(g.name)
        if g_id is None:
            #pkdp('NO GEOM {}, BUILDING', g.name)
            g_id = _build_geom(data)
            mgr.add_geom(g.name, g_id)
        v['geomName'] = g.name
        v['geomId'] = g_id
        v['dataFile'] = GEOM_FILE

        if v_type == VIEW_TYPE_OBJ:
            v['geomData'] = mgr.geom_to_data(g.name)
        elif v_type == VIEW_TYPE_FIELD:
            f_type = disp.fieldType
            if f_type not in radia_tk.FIELD_TYPES:
                raise ValueError(
                    'Invalid field {} ({})'.format(f_type, radia_tk.FIELD_TYPES)
                )
            if True:  #f_type == radia_tk.FIELD_TYPE_MAG_M:
                f = mgr.get_magnetization(g.name)
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
        pkdp('SOLVE RES {}', res)
        v['geomData'] = mgr.geom_to_data(g.name)

    # add parameters (???)
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        GEOM_PYTHON_FILE,
    )
