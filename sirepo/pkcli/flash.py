# -*- coding: utf-8 -*-
"""Wrapper to run FLASH from the command line.

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
import os
import re
import sirepo.sim_data
import sirepo.template.flash as template
import subprocess

_SIM_DATA = sirepo.sim_data.get_class('flash')

def run_background(cfg_dir):
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
    def _format_parameter(parts, model):
        model.name = p[1]
        model.type = parts[2]
        d = parts[3].strip('"')
        if model.type == 'REAL':
            d = float(d)
        elif model.type == 'INTEGER':
            d = int(d)
        elif model.type == 'BOOLEAN':
            d = '0' if d == 'FALSE' else '1'
        model.default = d
        return model

    def _format_particleprop(parts, model):
        model.name = p[1]
        model.type = p[2]
        return model

    def _format_particlemap(parts, model):
        model.partName = p[2]
        model.varType = p[4]
        model.varName = p[5]
        return model

    def _format_unit(parts, model):
        model.unit = parts[1]
        return model

    def _format_variable(parts, model):
        model.name=p[1]
        return model

    d = PKDict(
        PARAMETER=_format_parameter,
        PARTICLEPROP=_format_particleprop,
        PARTICLEMAP=_format_particlemap,
        REQUESTS=_format_unit,
        REQUIRES=_format_unit,
        VARIABLE=_format_variable,
    )

    res = []
    id = 1
    with open(path, 'rt') as f:
        for l in f:
            p = l.split()
            if not p or not p[0] in d:
                p and pkdlog('skipping line={}', l)
                continue
            m = PKDict(
                _id=id,
                _type=p[0],
            )
            id += 1
            res.append(d[m._type](p, m))
    return pkjson.dump_pretty(res)
