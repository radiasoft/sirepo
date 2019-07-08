# -*- coding: utf-8 -*-
"""Wrapper to run webcon from the command line.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import contextlib
import numpy as np
import os
import py.path
import scipy.optimize
import signal
import sirepo.template.webcon as template
import socket
import subprocess
import time

_camonitor_proc = None

_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)


class AbortOptimizationException(Exception):
    pass


def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        if 'analysisReport' in data.report:
            res = template.get_analysis_report(py.path.local(cfg_dir), data)
        elif 'fftReport' in data.report:
            res = template.get_fft(py.path.local(cfg_dir), data)
        elif 'correctorSettingReport' in data.report:
            res = template.get_settings_report(py.path.local(cfg_dir), data)
        elif 'beamPositionReport' in data.report:
            res = template.get_beam_pos_report(py.path.local(cfg_dir), data)
        elif 'watchpointReport' in data.report:
            res = template.get_centroid_report(py.path.local(cfg_dir), data)
        else:
            assert False, 'unknown report: {}'.format(data.report)
        simulation_db.write_result(res)


def run_background(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        res = {}
        if data.report == 'epicsServerAnimation':
            epics_settings = data.models.epicsServerAnimation
            if epics_settings.serverType == 'local':
                server_address = _run_epics(data)
                epics_settings.serverAddress = server_address
            else:
                assert epics_settings.serverAddress, 'missing remote server address'
                server_address = epics_settings.serverAddress
            _run_epics_monitor(server_address)
            if epics_settings.serverType == 'local':
                res['error'] = _run_simulation_loop(server_address)
            else:
                res['error'] = _run_forever(server_address)
        else:
            assert False, 'unknown report: {}'.format(data.report)
        simulation_db.write_result(res)


def _check_beam_steering(is_steering):
    # use a steering file (possibly written across NFS) to start/abort steering
    steering = None
    if os.path.exists(template.STEERING_FILE):
        steering = simulation_db.read_json(template.STEERING_FILE)
        os.remove(template.STEERING_FILE)
        is_steering = steering.useSteering == '1'
    return is_steering, steering


def _cost_function(values, server_address, periodic_callback):
    is_steering, steering = _check_beam_steering(True)
    if not is_steering:
        raise AbortOptimizationException()
    template.write_epics_values(server_address, template.CURRENT_FIELDS, values)
    # periodic_callback() either waits for the remote EPICS or runs a local sim which populates local EPICS
    periodic_callback(server_address)
    readings = template.read_epics_values(server_address, template.BPM_FIELDS)
    #cost = np.sum((np.array(readings) * 1000.) ** 2)
    cost = np.sum((np.array(
        [readings[4] - readings[6], readings[5] - readings[7], readings[6], readings[7]]
    ) * 1000.) ** 2)
    return cost


def _find_free_port():
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()


def _optimize_nelder_mead(server_address, periodic_callback):
    opt = scipy.optimize.minimize(
        _cost_function,
        np.zeros(len(template.CURRENT_FIELDS)),
        method='Nelder-Mead',
        options={
            'maxiter': 500,
            'maxfev': 500,
        },
        tol=1e-4,
        args=(server_address, periodic_callback,),
    )
    pkdlog('optimization results: {}', opt)
    res = {
        'message': opt.message,
        'success': opt.success,
    }
    if 'x' in opt and len(opt.x) == len(template.CURRENT_FIELDS):
        res['result'] = opt.x
    return res


def _optimize_polyfit(server_address, periodic_callback):
    settings_0 = np.zeros(len(template.CURRENT_FIELDS))
    sets = np.identity(len(settings_0))
    M = np.zeros(sets.shape)
    sets_a = np.linspace(-5, 5, 5) * 0.01
    readings = np.zeros([len(settings_0), 5])
    for i in range(0, len(settings_0)):
        for j in range(0, len(sets_a)):
            is_steering, steering = _check_beam_steering(True)
            if not is_steering:
                raise AbortOptimizationException()
            setting_test = sets[i,:] * sets_a[j]
            template.write_epics_values(server_address, template.CURRENT_FIELDS, setting_test)
            periodic_callback(server_address)
            readings[:,j] = template.read_epics_values(server_address, template.BPM_FIELDS)
        for k in range(0, len(settings_0)):
            M[i,k] = np.polyfit(sets_a, readings[k,:], 1)[0]
    # inverse response matrix
    MI = np.linalg.pinv(M.T)
    # reset the beam-line
    template.write_epics_values(server_address, template.CURRENT_FIELDS, settings_0)
    periodic_callback(server_address)
    readings_1 = np.asarray(template.read_epics_values(server_address, template.BPM_FIELDS))
    # create settings to cancel out offsets
    new_sets = np.dot(MI, -readings_1)
    return {
        'message': '',
        'success': True,
        'result': new_sets,
    }


def _ping_epics(server_address):
    return template.read_epics_values(server_address, [template.BPM_FIELDS[0]]) is not None


def _run_beam_steering(server_address, steering, periodic_callback):
    method = steering.steeringMethod
    try:
        if method == 'nmead':
            res = _optimize_nelder_mead(server_address, periodic_callback)
        elif method == 'polyfit':
            res = _optimize_polyfit(server_address, periodic_callback)
        if 'result' in res:
            template.write_epics_values(server_address, template.CURRENT_FIELDS, res['result'])
        simulation_db.write_json(template.OPTIMIZER_RESULT_FILE, {
            'message': res['message'],
            'success': res['success'],
        })
    except AbortOptimizationException as e:
        pass


def _run_epics(data):
    host, port = _find_free_port()
    server_address = '{}:{}'.format(host, port)
    #TODO(pjm): process management
    _subprocess(server_address, 'softIoc epics-boot.cmd > epics.log')
    return server_address


def _run_epics_monitor(server_address):
    global _camonitor_proc
    #TODO(pjm): dev restarts when code changes doesn't terminate camonitor
    #TODO(pjm): process management
    signal.signal(signal.SIGTERM, _terminate_subprocesses)
    _camonitor_proc = _subprocess(
        server_address,
        'exec camonitor ' + ' '.join(template.BPM_FIELDS + template.CURRENT_FIELDS)
        + ' > ' + template.MONITOR_LOGFILE)


def _run_forever(server_address):
    _wait_for_beam_steering(server_address, _wait_for_remote_epics)


def _run_simulation_loop(server_address):
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    return _wait_for_beam_steering(server_address, update_and_run_simulation)


def _subprocess(server_address, cmd):
    #TODO(pjm): need better process management, remove shell=True
    return subprocess.Popen(
        cmd,
        shell=True,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=template.epics_env(server_address),
    )


def _terminate_subprocesses(*args):
    global _camonitor_proc
    if _camonitor_proc:
        _camonitor_proc.terminate()


def _wait_for_beam_steering(server_address, periodic_callback):
    is_steering = False
    if not _ping_epics(server_address):
        return 'Failed connection to EPICS server'
    #TODO(pjm): don't run forever. Exit after a long period of no changes?
    while True:
        #TODO(pjm): add periodic _ping_epics()
        is_steering, steering = _check_beam_steering(is_steering)
        if is_steering:
            _run_beam_steering(server_address, steering, periodic_callback)
            is_steering = False
        else:
            error = periodic_callback(server_address)
            if error:
                return error


def _wait_for_remote_epics(server_address):
    time.sleep(2)
