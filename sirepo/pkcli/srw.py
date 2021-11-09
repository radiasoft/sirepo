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
import copy
import numpy as np
import sirepo.job
import sirepo.template.srw


def create_predefined(out_dir=None):
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
        return sim_data.srw_lib_file_paths_for_type(
            file_type,
            lambda f: PKDict(fileName=f.basename),
            want_user_lib_dir=False,
        )

    def p(out_dir):
        b = srw_common.PREDEFINED_JSON
        if out_dir:
            return pkio.py_path(out_dir).join(b)
        from sirepo.template import template_common
        # Assume a good location for PREDEFINED_JSON is the same dir
        # as PARAMETERS_PYTHON_FILE.jinja.
        return sim_data.resource_path(
            template_common.jinja_filename(
                template_common.PARAMETERS_PYTHON_FILE,
            ),
        ).dirpath(b)

    n = p(out_dir)
    pykern.pkjson.dump_pretty(
        PKDict(
            beams=beams,
            magnetic_measurements=f('undulatorTable'),
            mirrors=f('mirror'),
            sample_images=f('sample'),
        ),
        filename=n,
    )
    return 'Created {}'.format(n)


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
    sirepo.job.init()
    sim_in = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    r = template_common.exec_parameters()
    # special case for importing python code
    m = sim_in.report
    if m == 'backgroundImport':
        template_common.write_sequential_result(PKDict(
            {sirepo.template.srw.PARSED_DATA_ATTR: r.parsed_data}
        ))
    else:
        template_common.write_sequential_result(
            sirepo.template.srw.extract_report_data(sim_in),
        )


def run_background(cfg_dir):
    """Run srw with mpi in ``cfg_dir``

    Args:
        cfg_dir (str): directory to run srw in
    """
    sim_in = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    if sim_in.report == 'beamlineAnimation':
        template_common.exec_parameters()
    else:
        template_common.exec_parameters_with_mpi()
    if sim_in.report == 'coherentModesAnimation':
        # this sim creates _really_ large intermediate files which should get removed
        for p in pkio.sorted_glob('*_mi.h5'):
            p.remove()
