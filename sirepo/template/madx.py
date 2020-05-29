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
from sirepo.template.template_common import ParticleEnergy
from sirepo.template.lattice import LatticeUtil
import math
import numpy as np
import re
import sirepo.sim_data


_FILE_TYPES = ['ele', 'lte', 'madx']

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

_METHODS = template_common.RPN_METHODS.extend([])


class MadxElementIterator(lattice.ElementIterator):
    def is_ignore_field(self, field):
        return field == 'name'


def get_application_data(data, **kwargs):
    if 'method' not in data:
        raise RuntimeError('no application data method')
    if data.method not in _METHODS:
        raise RuntimeError('unknown application data method: {}'.format(data.method))
    #if data.method in template_common.RPN_METHODS:
    #    return template_common.get_rpn_data(data, _SCHEMA, _MADX_CONSTANTS)
    cv = code_variable.CodeVar(
        data.variables,
        code_variable.PurePythonEval(_MADX_CONSTANTS),
        case_insensitive=True,
    )
    if data.method == 'rpn_value':
        # accept array of values enclosed in curly braces
        if re.search(r'^\{.*\}$', data.value):
            data.result = ''
            return data
        v, err = cv.eval_var(data.value)
        if err:
            data.error = err
        else:
            data.result = v
        return data
    if data.method == 'recompute_rpn_cache_values':
        cv(data.variables).recompute_cache(data.cache)
        return data
    if data.method == 'validate_rpn_delete':
        model_data = simulation_db.read_json(
            simulation_db.sim_data_file(data.simulationType, data.simulationId))
        data.error = cv(data.variables).validate_var_delete(
            data.name,
            model_data,
            _SCHEMA
        )
        return data


def import_file(req, test_data=None, **kwargs):
    ft = '|'.join(_FILE_TYPES)
    if not re.search(r'\.({})$'.format(ft), req.filename, re.IGNORECASE):
        raise IOError('invalid file extension, expecting one of {}'.format(_FILE_TYPES))
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
        #madx = madx_parser.parse_file(text, downcase_variables=True)
        #data = madx_converter.from_madx(
        #    SIM_TYPE,
        #    madx_parser.parse_file(text, downcase_variables=True)
        #)
        #mm = madx_parser.parse_file(text, downcase_variables=True)
        #pkdp('MADX {} VS DATA {}', mm, data)
        madx_converter.fixup_madx(madx_parser.parse_file(text, downcase_variables=True))
    else:
        raise IOError('invalid file extension, expecting .ele or .lte')
    data.models.simulation.name = re.sub(
        r'\.({})$'.format(ft),
        '',
        req.filename,
        flags=re.IGNORECASE
    )
    if input_data and not test_data:
        simulation_db.delete_simulation(
            SIM_TYPE,
            input_data.models.simulation.simulationId
        )
    return data


def madx_code_var(variables):
    return _code_var(variables)


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def _code_var(variables):
    return code_variable.CodeVar(
        variables,
        code_variable.PurePythonEval(_MADX_CONSTANTS),
        case_insensitive=True,
    )


def _fixup_madx(madx, data):
    cv = madx_code_var(madx.models.rpnVariables)
    assert LatticeUtil.has_command(madx, 'beam'), \
        'MAD-X file missing BEAM command'
    beam = LatticeUtil.find_first_command(madx, 'beam')
    if beam.energy == 1 and (beam.pc != 0 or beam.gamma != 0 or beam.beta != 0 or beam.brho != 0):
        # unset the default mad-x value if other energy fields are set
        beam.energy = 0
    particle = beam.particle.lower() or 'other'
    LatticeUtil.find_first_command(data, 'beam').particle = particle.upper()
    energy = ParticleEnergy.compute_energy('madx', particle, beam.copy())
    LatticeUtil.find_first_command(data, 'beam').pc = energy.pc
    LatticeUtil.find_first_command(data, 'track').line = data.models.simulation.visualizationBeamlineId
    for el in data.models.elements:
        if el.type == 'SBEND' or el.type == 'RBEND':
            # mad-x is GeV (total energy), designenergy is MeV (kinetic energy)
            el.designenergy = round(
                (energy.energy - ParticleEnergy.PARTICLE[particle].mass) * 1e3,
                6,
            )
            # this is different than the opal default of "2 * sin(angle / 2) / length"
            # but matches elegant and synergia
            el.k0 = cv.eval_var_with_assert(el.angle) / cv.eval_var_with_assert(el.l)
            el.gap = 2 * cv.eval_var_with_assert(el.hgap)


def _format_field_value(state, model, field, el_type):
    value = model[field]
    return [field, value]


def _generate_lattice(util):
    filename_map = PKDict()
    return util.render_lattice_and_beamline(
        lattice.LatticeIterator(filename_map, _format_field_value),
        want_semicolon=True)


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    util = LatticeUtil(data, _SCHEMA)
    code_var = _code_var(data.models.rpnVariables)
    v.lattice = _generate_lattice(util)
    v.variables = _generate_variables(code_var, data)
    if data.models.simulation.visualizationBeamlineId:
        v.useBeamline = util.id_map[data.models.simulation.visualizationBeamlineId].name
    beam = util.find_first_command(data, 'beam')
    if beam:
        v.beamParticle = beam.particle
        v.beamPC = beam.pc
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
