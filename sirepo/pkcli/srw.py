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
from sirepo.template.srw import extract_report_data
import os
import re
import srwl_bl
import srwlib


def python_to_json(run_dir='.', in_py='in.py', out_json='out.json'):
    """Run importer in run_dir trying to import py_file

    Args:
        run_dir (str): clean directory except for in_py
        in_py (str): name of the python file in run_dir
        out_json (str): valid json matching SRW schema
    """
    import sirepo.importer
    with pkio.save_chdir(run_dir):
        out = sirepo.importer.python_to_json(in_py)
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
            p['particles_per_slave'] = 1
        p['slaves'] = mpi.cfg.slaves
        script += '''
import srwl_bl
v = srwl_bl.srwl_uti_parse_options(varParam, use_sys_argv=False)
source_type, mag = srwl_bl.setup_source(v)
v.wm_nm = {total_particles}
v.wm_na = {particles_per_slave}
# Number of "iterations" per save is best set to num processes
v.wm_ns = {slaves}
op = set_optics()
srwl_bl.SRWLBeamline(_name=v.name).calc_all(v, op)
'''.format(**p)
        mpi.run_script(script)


def _mirror_plot(model_data):
    mirror = model_data['models']['mirrorReport']
    element = srwlib.srwl_opt_setup_surf_height_1d(
        srwlib.srwl_uti_read_data_cols(mirror['heightProfileFile'], "\t", 0, 1),
        _dim=mirror['orientation'],
        _ang=float(mirror['grazingAngle']) / 1e3,
        _amp_coef=float(mirror['heightAmplification']))
        #_size_x=float(mirror['horizontalTransverseSize']) / 1e3,
        #_size_y=float(mirror['verticalTransverseSize']) / 1e3)
    transmission_data = element.get_data(3, 3)
    srwlib.srwl_uti_save_intens_ascii(
        transmission_data, element.mesh, 'res_mirror.dat', 0,
        ['', 'Horizontal Position', 'Vertical Position', 'Optical Path Difference'], _arUnits=['', 'm', 'm', ''])
    return 'res_mirror.dat'


def _process_output(filename, model_data):
    info = extract_report_data(filename, model_data)
    simulation_db.write_json(template_common.OUTPUT_BASE_NAME, info)


def _run_srw():
    run_dir = os.getcwd()
    data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
    #TODO(pjm): need to properly escape data values, untrusted from client
    # This defines the varParam variable and set_optics() function:
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    v = srwl_bl.srwl_uti_parse_options(varParam, use_sys_argv=False)
    source_type, mag = srwl_bl.setup_source(v)
    op = None
    if data['report'] == 'intensityReport':
        v.ss = True
        outfile = v.ss_fn
    elif data['report'] == 'fluxReport':
        v.sm = True
        outfile = v.sm_fn
    elif data['report'] == 'powerDensityReport':
        v.pw = True
        outfile = v.pw_fn
    elif data['report'] == 'initialIntensityReport' or data['report'] == 'sourceIntensityReport':
        v.si = True
        outfile = v.si_fn
    elif data['report'] == 'mirrorReport':
        _process_output(_mirror_plot(data), data)
        return
    elif re.search('^watchpointReport', data['report']):
        op = set_optics()
        v.ws = True
        outfile = v.ws_fni
    else:
        raise Exception('unknown report: {}'.format(data['report']))
    if isinstance(mag, srwlib.SRWLGsnBm):
        mag = None
    srwl_bl.SRWLBeamline(_name=v.name, _mag_approx=mag).calc_all(v, op)
    _process_output(outfile, data)


def _cfg_int(lower, upper):
    def wrapper(value):
        v = int(value)
        assert lower <= v <= upper, \
            'value must be from {} to {}'.format(lower, upper)
        return v
    return wrapper


cfg = pkconfig.init(
    particles_per_slave=(5, int, 'particles for each core to process'),
    total_particles=(50000, int, 'total number of particles to process'),
)
