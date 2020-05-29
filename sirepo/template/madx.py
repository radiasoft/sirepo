# -*- coding: utf-8 -*-
u"""MAD-X execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcompat
from pykern import pkio
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import elegant_command_importer
from sirepo.template import elegant_lattice_importer
from sirepo.template import lattice
from sirepo.template import madx_converter, madx_parser
from sirepo.template import sdds_util
from sirepo.template import template_common
from sirepo.template.lattice import LatticeUtil
import copy
import math
import numpy as np
import pykern.pkinspect
import re
import sirepo.sim_data


# TODO(e-carlin): The madx convetion is name.madx for in
# and name.out for out. What do we want to do?
MADX_INPUT_FILENAME = 'madx.in'
MADX_OUTPUT_FILENAME = 'madx.out'
TWISS_OUTPUT_FILENAME = 'twiss.tfs'

_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals()

_PI = 4 * math.atan(1)
_MADX_CONSTANTS = PKDict(
    pi=_PI,
    twopi=_PI * 2.0,
    raddeg=180.0 / _PI,
    degrad=_PI / 180.0,
    e=math.exp(1),
    emass=0.510998928e-03,
    pmass=0.938272046e+00,
    nmass=0.931494061+00,
    mumass=0.1056583715,
    clight=299792458.0,
    qelect=1.602176565e-19,
    hbar=6.58211928e-25,
    erad=2.8179403267e-15,
)


class MadxElementIterator(lattice.ElementIterator):
    def is_ignore_field(self, field):
        return field == 'name'


def background_percent_complete(report, run_dir, is_running):
    # TODO(e-carlin): impl
    return PKDict(
        percentComplete=0,
        frameCount=0,
    )


def import_file(req, test_data=None, **kwargs):
    # input_data is passed by test cases only
    input_data = test_data
    text = pkcompat.from_bytes(req.file_stream.read())
    if 'simulationId' in req.req_data:
        input_data = simulation_db.read_simulation_json(SIM_TYPE, sid=req.req_data.simulationId)
    if re.search(r'\.ele$', req.filename, re.IGNORECASE):
        data = elegant_command_importer.import_file(text)
    elif re.search(r'\.lte$', req.filename, re.IGNORECASE):
        data = elegant_lattice_importer.import_file(text, input_data)
        if input_data:
            _map_commands_to_lattice(data)
    elif re.search(r'\.madx$', req.filename, re.IGNORECASE):
        data = madx_converter.from_madx(
            SIM_TYPE,
            madx_parser.parse_file(text, downcase_variables=True))
    else:
        raise IOError('invalid file extension, expecting .ele or .lte')
    data.models.simulation.name = re.sub(r'\.(lte|ele|madx)$', '', req.filename, flags=re.IGNORECASE)
    if input_data and not test_data:
        simulation_db.delete_simulation(SIM_TYPE, input_data.models.simulation.simulationId)
    return data


def madx_code_var(variables):
    return _code_var(variables)

def prepare_sequential_output_file(run_dir, data):
    r = data.report
    if r == 'twissReport':
        f = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
        if f.exists():
            f.remove()
            save_sequential_report_data(data, run_dir)

def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def save_sequential_report_data(data, run_dir):
    template_common.write_sequential_result(
        _extract_report_data(data, run_dir),
        run_dir=run_dir,
    )


def write_parameters(data, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    pkio.write_text(
        run_dir.join(MADX_INPUT_FILENAME),
        _generate_parameters_file(data),
    )


def _code_var(variables):
    return code_variable.CodeVar(
        variables,
        code_variable.PurePythonEval(_MADX_CONSTANTS),
        case_insensitive=True,
    )


def _extract_report_data(data, run_dir):
   return getattr(
       pykern.pkinspect.this_module(),
       '_extract_report_' + data.report,
   )(data, run_dir)


def _extract_report_twissReport(data, run_dir):
    t = madx_parser.parse_tfs_file(run_dir.join(TWISS_OUTPUT_FILENAME))
    m = data.models[data.report]
    plots = []
    for f in ('y1', 'y2', 'y3'):
        if m[f] == 'none':
            continue
        plots.append(
            PKDict(field=m[f], points=t[m[f]], label=f'{m[f]} [m]')
        )
    return template_common.parameter_plot(
        t.s,
        plots,
        m,
        PKDict(title=data.models.simulation.name, y_label='', x_label='s[m]')
    )


def _format_field_value(state, model, field, el_type):
    value = model[field]
    return [field, value]


def _generate_beam(beam):
    res = 'beam'
    for k in ('mass', 'charge', 'gamma', 'sigt'):
        if k in beam:
            res += f', {k}={beam[k]}'
    return res + ';'


def _generate_lattice(util):
    filename_map = PKDict()
    return util.render_lattice_and_beamline(
        lattice.LatticeIterator(filename_map, _format_field_value),
        want_semicolon=True)


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    util = LatticeUtil(data, _SCHEMA)
    code_var = _code_var(data.models.rpnVariables)
    v.twissOutputFilename = TWISS_OUTPUT_FILENAME
    v.lattice = _generate_lattice(util)
    v.variables = _generate_variables(code_var, data)
    if data.models.simulation.visualizationBeamlineId:
        v.useBeamline = util.id_map[data.models.simulation.visualizationBeamlineId].name

    beam = util.find_first_command(data, 'beam')
    if beam:
        v.beam = _generate_beam(beam)
    return template_common.render_jinja(SIM_TYPE, v, 'parameters.madx')


def _generate_variable(name, variables, visited):
    res = ''
    if name not in visited:
        res += 'REAL {} = {};\n'.format(name, variables[name])
        visited[name] = True
    return res


def _generate_variables(code_var, data):
    res = ''
    visited = PKDict()
    for name in sorted(code_var.variables):
        for dependency in code_var.get_expr_dependencies(code_var.postfix_variables[name]):
            res += _generate_variable(dependency, code_var.variables, visited)
        res += _generate_variable(name, code_var.variables, visited)
    return res
