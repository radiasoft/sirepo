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

mgr = radia_tk.RadiaGeomMgr()


def extract_report_data(run_dir, sim_in):
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
    res, v = template_common.generate_parameters_file(data)
    #pkdp('GEN PARAMS {} V {}', data, v)
    v['geomFile'] = GEOM_FILE
    if 'geometry' in report:
        g = data.models.geometry
        g_id = mgr.get_geom(g.name)
        if g_id is None:
            pkdp('NO GEOM {}, BUILDING', g.name)
            g_id = _build_geom(data)
            mgr.add_geom(g.name, g_id)
        if 'doSolve' in g and g.doSolve:
            s = data.models.solver
            mgr.solve_geom(g.name, s.precision, s.maxIterations, s.method)
        v['geomName'] = g.name
        v['geomId'] = g_id
        v['geomData'] = mgr.geom_to_data(g.name)

    # add parameters (???)
    return template_common.render_jinja(
        SIM_TYPE,
        v,
        GEOM_PYTHON_FILE,
    )
