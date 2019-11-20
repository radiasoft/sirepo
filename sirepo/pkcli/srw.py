# -*- coding: utf-8 -*-
"""Wrapper to run SRW from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc
from sirepo import mpi
from sirepo import simulation_db
from sirepo.template import template_common
from sirepo.template.srw import extract_report_data, get_filename_for_model
import copy
import numpy as np


def create_predefined():
    from sirepo.template import srw_common
    import sirepo.sim_data
    import srwl_uti_src
    import pykern.pkjson

    sim_data = sirepo.sim_data.get_class('srw')
    beams = []
    for beam in srwl_uti_src.srwl_uti_src_e_beam_predef():
        info = beam[1]
        # _Iavg, _e, _sig_e, _emit_x, _beta_x, _alpha_x, _eta_x, _eta_x_pr, _emit_y, _beta_y, _alpha_y
        beams.append(
            srw_common.process_beam_parameters(PKDict(
                name=beam[0],
                current=info[0],
                energy=info[1],
                rmsSpread=info[2],
                horizontalEmittance=sim_data.srw_format_float(info[3] * 1e9),
                horizontalBeta=info[4],
                horizontalAlpha=info[5],
                horizontalDispersion=info[6],
                horizontalDispersionDerivative=info[7],
                verticalEmittance=sim_data.srw_format_float(info[8] * 1e9),
                verticalBeta=info[9],
                verticalAlpha=info[10],
                verticalDispersion=0,
                verticalDispersionDerivative=0,
                energyDeviation=0,
                horizontalPosition=0,
                verticalPosition=0,
                drift=0.0,
                isReadOnly=True,
            )),
        )

    def f(file_type):
        return sim_data.srw_files_for_type(
            file_type,
            lambda f: PKDict(fileName=f.basename),
            dir_path=sim_data.resource_dir(),
        )

    p = sim_data.resource_path(srw_common.PREDEFINED_JSON)
    pykern.pkjson.dump_pretty(
        PKDict(
            beams=beams,
            magnetic_measurements=f('undulatorTable'),
            mirrors=f('mirror'),
            sample_images=f('sample'),
        ),
        filename=p,
    )
    return 'Created {}'.format(p)


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
    srwl_bl.SRWLBeamline(_name=v.name, _mag_approx=mag).calc_all(v, op)

main()
'''.format(**p)
        mpi.run_script(script)
        simulation_db.write_result({})

def _run_srw():
    #TODO(pjm): need to properly escape data values, untrusted from client
    sim_in = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    locals()['main']()
    # special case for importing python code
    r = sim_in.report
    if r == 'backgroundImport':
        sim_id = sim_in['models']['simulation']['simulationId']
        parsed_data['models']['simulation']['simulationId'] = sim_id
        #TODO(pjm): assumes the parent directory contains the simulation data,
        # can't call simulation_db.save_simulation_json() because user isn't set for pkcli commands
        simulation_db.write_json('../{}'.format(simulation_db.SIMULATION_DATA_FILE), parsed_data)
        simulation_db.write_result({
            'simulationId': sim_id,
        })
    else:
        simulation_db.write_result(
            extract_report_data(
                get_filename_for_model(r),
                sim_in,
            ),
        )


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
