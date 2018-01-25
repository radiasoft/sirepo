# -*- coding: utf-8 -*-
"""Wrapper to run SRW from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
from sirepo.template.srw import extract_report_data, get_filename_for_model
import numpy as np


def python_to_json(run_dir='.', in_py='in.py', out_json='out.json'):
    """Run importer in run_dir trying to import py_file

    Args:
        run_dir (str): clean directory except for in_py
        in_py (str): name of the python file in run_dir
        out_json (str): valid json matching SRW schema
    """
    from sirepo.template import srw_importer
    with pkio.save_chdir(run_dir):
        out = srw_importer.python_to_json(in_py)
        with open(out_json, 'w') as f:
            f.write(out)
    return 'Created: {}'.format(out_json)


def run(cfg_dir):
    """Run srw in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run srw in
    """
    with pkio.save_chdir(cfg_dir):
        _run_srw()


def run_background(cfg_dir):
    """Run srw with mpi in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run srw in
    """
    with pkio.save_chdir(cfg_dir):
        script = pkio.read_text(template_common.PARAMETERS_PYTHON_FILE)
        p = dict(pkcollections.map_items(cfg))
        if pkconfig.channel_in('dev'):
            p['particles_per_core'] = 5
        p['cores'] = mpi.cfg.cores
        script += '''
    v.wm_na = v.sm_na = {particles_per_core}
    # Number of "iterations" per save is best set to num processes
    v.wm_ns = v.sm_ns = {cores}
    srwl_bl.SRWLBeamline(_name=v.name).calc_all(v, op)

main()
'''.format(**p)
        mpi.run_script(script)
        simulation_db.write_result({})

def _run_srw():
    #TODO(pjm): need to properly escape data values, untrusted from client
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    main()
    simulation_db.write_result(extract_report_data(get_filename_for_model(data['report']), data))


def _cfg_int(lower, upper):
    def wrapper(value):
        v = int(value)
        assert lower <= v <= upper, \
            'value must be from {} to {}'.format(lower, upper)
        return v
    return wrapper


cfg = pkconfig.init(
    particles_per_core=(5, int, 'particles for each core to process'),
)
