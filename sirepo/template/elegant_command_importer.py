# -*- coding: utf-8 -*-
u"""elegant lattice parser.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
from sirepo.template import elegant_command_parser
from sirepo.template import elegant_common
from sirepo.template import elegant_lattice_importer
import re
import sirepo.sim_data


_SIM_DATA, SIM_TYPE, _SCHEMA = sirepo.sim_data.template_globals('elegant')


def _init_types():
    res = PKDict()
    for name in _SCHEMA['model']:
        if name.startswith('command_'):
            name = re.sub(r'^command_', '', name)
            res[name] = True
    return res


_ELEGANT_TYPES = _init_types()


def import_file(text):
    commands = elegant_command_parser.parse_file(text)
    if not len(commands):
        raise IOError('no commands found in file')
    _verify_lattice_name(commands)
    # iterate commands, validate values and set defaults from schema
    for cmd in commands:
        cmd_type = cmd['_type']
        if not cmd_type in _ELEGANT_TYPES:
            raise IOError('unknown command: {}'.format(cmd_type))
        elegant_lattice_importer.validate_fields(cmd, PKDict())
    data = simulation_db.default_data(SIM_TYPE)
    #TODO(pjm) javascript needs to set bunch, bunchSource, bunchFile values from commands
    data.models.commands = commands
    return data


def _verify_lattice_name(commands):
    for cmd in commands:
        if cmd['_type'] == 'run_setup' and 'lattice' in cmd:
            return cmd['lattice']
    raise IOError('missing run_setup lattice field')
