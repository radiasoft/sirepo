# -*- coding: utf-8 -*-
"""elegant lattice parser.

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
from sirepo.template import lattice
import re
import sirepo.sim_data


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals("elegant")


p = lattice.LatticeParser.COMMAND_PREFIX
_TYPES = set([n[len(p) :] for n in SCHEMA["model"] if n.startswith(p)])
del p


def import_file(text, update_filenames=True):
    commands = elegant_command_parser.parse_file(text, update_filenames)
    if not commands:
        raise IOError("no commands found in file")
    _verify_lattice_name(commands)
    rpn_variables = PKDict()
    # iterate commands, validate values and set defaults from schema
    for cmd in commands:
        cmd_type = cmd["_type"]
        if not cmd_type in _TYPES:
            raise IOError("unknown command: {}".format(cmd_type))
        elegant_lattice_importer.validate_fields(
            cmd,
            PKDict(),
            update_filenames=update_filenames,
        )
        # convert macro variables into rpnVariables
        n = lattice.LatticeUtil.model_name_for_data(cmd)
        for field in cmd:
            el_schema = SCHEMA.model[n].get(field)
            if el_schema and el_schema[1] == "RPNValue":
                m = re.search(r"^<(\w+)>$", str(cmd[field]))
                if m:
                    cmd[field] = m.group(1)
                    rpn_variables[cmd[field]] = _SIM_DATA.model_defaults(n).get(
                        field, 0
                    )

    data = simulation_db.default_data(SIM_TYPE)
    # TODO(pjm) javascript needs to set bunch, bunchSource, bunchFile values from commands
    data.models.commands = commands
    data.models.rpnVariables = [
        PKDict(name=k, value=v) for k, v in rpn_variables.items()
    ]
    return data


def _verify_lattice_name(commands):
    for cmd in commands:
        if cmd["_type"] == "run_setup" and "lattice" in cmd:
            return cmd["lattice"]
    raise IOError("missing run_setup lattice field")
