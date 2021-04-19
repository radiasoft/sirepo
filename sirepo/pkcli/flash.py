# -*- coding: utf-8 -*-
"""Wrapper to run FLASH from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjson
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import flash_parser
from sirepo.template import template_common
import os
import re
import sirepo.sim_data
import sirepo.template.flash as template

_SIM_DATA = sirepo.sim_data.get_class('flash')


def run_background(cfg_dir):
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if data.report == 'setupAnimation':
        return
    mpi.run_program([pkio.py_path(cfg_dir).join(
        _SIM_DATA.flash_exe_basename(simulation_db.read_json(
            template_common.INPUT_BASE_NAME,
        )),
    )])


def units(src_path):
    res = []
    p = pkio.py_path(src_path).join('source')
    for d, _, _ in os.walk(p):
        m = re.search(
            r'^(?:{})(.*\/[A-Z0-9][A-Za-z0-9-_\.]+$)'.format(re.escape(str(p))),
            d,
        )
        if m:
            s = m.group(1)[1:]
            res.append([s, s])
    res.sort()
    pkjson.dump_pretty(res, filename='res.json')


def config_to_schema(path):
    """Convert a Config file to JSON in Sirepo schema format

    Args:
      path (str): path to Config file to parse
    """
    return flash_parser.ConfigParser().parse(pkio.read_text(path))


def par_to_schema(sim_path, par_path):
    """Update a simulation from parsed flash.par values.
    """
    return flash_parser.ParameterParser().parse(
        pkjson.load_any(pkio.read_text(sim_path)),
        pkio.read_text(par_path),
    )


def update_sim_from_config(sim_path, config_path):
    data = pkjson.load_any(pkio.read_text(sim_path))
    data.models.setupConfigDirectives = config_to_schema(config_path)
    pkjson.dump_pretty(data, sim_path)


def update_sim_from_par(sim_path, par_path):
    data = pkjson.load_any(pkio.read_text(sim_path))
    parser = flash_parser.ParameterParser()
    values = parser.parse(data, pkio.read_text(par_path))
    # reset all model fields to default and override with new par values
    for (m, fields) in parser.schema.model.items():
        for f in fields:
            if f in values:
                data.models[m][f] = values[f]
            else:
                data.models[m][f] = fields[f][2]
    pkjson.dump_pretty(data, sim_path)
