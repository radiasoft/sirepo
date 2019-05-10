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
import os
import py.path
import signal
import sirepo.template.webcon as template
import socket
import subprocess
import time

_camonitor_proc = None

_SCHEMA = simulation_db.get_schema(template.SIM_TYPE)


def run(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        if 'analysisReport' in data.report:
            res = template.get_analysis_report(py.path.local(cfg_dir), data)
        elif 'fftReport' in data.report:
            res = template.get_fft(py.path.local(cfg_dir), data)
        else:
            assert False, 'unknown report: {}'.format(data.report)
        simulation_db.write_result(res)


def run_background(cfg_dir):
    with pkio.save_chdir(cfg_dir):
        data = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        res = {}
        if data.report == 'epicsServerAnimation':
            epicsSettings = data.models.epicsServerAnimation
            if epicsSettings.serverType == 'local':
                server_address = _run_epics(data)
            else:
                assert epicsSettings.serverAddress, 'missing remote server address'
                server_address = epicsSettings.serverAddress
            _run_epics_monitor(server_address)
            if epicsSettings.serverType == 'local':
                _run_simulation_loop(server_address)
            else:
                res['error'] = _run_forever(server_address)
        simulation_db.write_result(res)


def _find_free_port():
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()


def _run_epics(data):
    host, port = _find_free_port()
    server_address = '{}:{}'.format(host, port)
    _subprocess(server_address, 'beam_line_example epics-boot.cmd > epics.log')
    #pkdp('running epics server: {}', server_address)
    return server_address


def _run_epics_monitor(server_address):
    global _camonitor_proc
    #TODO(pjm): dev restarts when code changes doesn't terminate camonitor
    #TODO(pjm): process management
    signal.signal(signal.SIGTERM, _terminate_subprocesses)
    _camonitor_proc = _subprocess(server_address, 'exec camonitor ' + ' '.join(template.BPM_FIELDS) + ' > ' + template.BPM_LOGFILE)


def _run_forever(server_address):
    while (True):
        # runs subprocesses until terminated
        time.sleep(10)
        # ensure commands can be run against the server (waits up to 10 seconds for connection)
        if template.run_epics_command(server_address, ['caget', '-w', '10', template.BPM_FIELDS[0]]) is None:
            return 'Failed to connect to EPICS server'


def _run_simulation_loop(server_address):
    os.environ['EPICS_CA_AUTO_ADDR_LIST'] = 'NO'
    os.environ['EPICS_CA_ADDR_LIST'] = server_address
    exec(pkio.read_text(template_common.PARAMETERS_PYTHON_FILE), locals(), locals())
    while True:
        update_epics_currents(server_address)
        run_simulation()
        update_epics_positions()
        time.sleep(0.5)


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
