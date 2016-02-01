# -*- coding: utf-8 -*-
"""Wrapper to run SRW from the command line.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp, pkdc

import json
import os
import re
import signal
import srwl_bl
import srwlib
import subprocess
import sys
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkio
from sirepo.template.srw import extract_report_data

def run(cfg_dir):
    """Run srw in ``cfg_dir``

    The files in ``cfg_dir`` must be configured properly.

    Args:
        cfg_dir (str): directory to run srw in
    """
    with pkio.save_chdir(cfg_dir):
        _run_srw()


def run_background(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        fn = 'run_background.py'
        cmd = [sys.executable or 'python', fn]
        script = pkio.read_text('srw_parameters.py')
        p = dict(pkcollections.map_items(cfg))
        if cfg.slave_processes > 1:
            cmd[0:0] = [
                'mpiexec',
                '-n',
                # SRW includes a master process so 2 really needs 3 processes
                str(cfg.slave_processes + 1),
            ]
            script += '''
from mpi4py import MPI
if MPI.COMM_WORLD.Get_rank():
    import signal
    signal.signal(signal.SIGTERM, lambda x, y: MPI.COMM_WORLD.Abort(1))
'''
        else:
            # In interactive (dev) mode, output as frequently as possible
            p['particles_per_slave'] = 1
        script += '''
import srwl_bl
v = srwl_bl.srwl_uti_parse_options(get_srw_params())
source_type, mag = setup_source(v)
v.wm = True
v.wm_nm = {total_particles}
v.wm_na = {particles_per_slave}
# Number of "iterations" per save is best set to num processes
v.wm_ns = {slave_processes}
op = get_beamline_optics()
bl = srwl_bl.SRWLBeamline(_name=v.name)
#TODO(pjm): hack in the mag_approx - not allow in constructor for Gaussian Beams
if mag:
    bl.mag_approx = mag
bl.calc_all(v, op)
'''.format(**p)
        pkio.write_text(fn, script)
        try:
            p = subprocess.Popen(
                cmd,
                stdin=open(os.devnull),
                stdout=open('run_background.out', 'w'),
                stderr=subprocess.STDOUT,
            )
            signal.signal(signal.SIGTERM, lambda x, y: p.terminate())
            rc = p.wait()
            if rc != 0:
                p = None
                raise RuntimeError('child terminated: retcode={}'.format(rc))
        finally:
            if not p is None:
                p.terminate()


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
    with open('out.json', 'w') as outfile:
        json.dump(info, outfile)


def _run_srw():
    run_dir = os.getcwd()
    with open('in.json') as f:
        data = json.load(f)
    #TODO(pjm): need to properly escape data values, untrusted from client
    # this defines the get_srw_params() and get_beamline_optics() functions
    exec(pkio.read_text('srw_parameters.py'), locals(), locals())
    v = srwl_bl.srwl_uti_parse_options(get_srw_params())
    source_type, mag = setup_source(v)
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
        op = get_beamline_optics()
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
    slave_processes=(1, int, 'cores to use for run_background slaves'),
    particles_per_slave=(5, int, 'particles for each core to process'),
    total_particles=(50000, int, 'total number of particles to process'),
)
