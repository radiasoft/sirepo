# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.controls`

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pkunit
from pykern.pkcollections import PKDict


def test_controls_monitor(fc):
    sim = fc.sr_sim_data('FODO with instruments')
    sim.models.controlSettings.operationMode = 'DeviceServer'
    sim.models.controlSettings.readOnly = '1'
    _run_test(sim, 'instrumentAnimation', 'device_server_monitor.txt')


def test_controls_opt1(fc):
    sim = fc.sr_sim_data('FODO with instruments')
    sim.models.optimizerSettings.method = 'nmead'
    _run_test(sim, 'instrumentAnimation', 'madx_nmead.txt')


def test_controls_opt2(fc):
    from sirepo.template import controls
    sim = fc.sr_sim_data('FODO with instruments')
    sim.models.optimizerSettings.method = 'polyfit'
    _run_test(sim, 'instrumentAnimation', 'madx_polyfit.txt')


def test_controls_opt3(fc):
    sim = fc.sr_sim_data('FODO with instruments')
    sim.models.optimizerSettings.method = 'nmead'
    sim.models.controlSettings.operationMode = 'DeviceServer'
    _run_test(sim, 'instrumentAnimation', 'device_server_nmead.txt')


def test_controls_opt3(fc):
    sim = fc.sr_sim_data('FODO with instruments')
    sim.models.optimizerSettings.method = 'polyfit'
    sim.models.controlSettings.operationMode = 'DeviceServer'
    _run_test(sim, 'instrumentAnimation', 'device_server_polyfit.txt')


def test_controls_position1(fc):
    sim = fc.sr_sim_data('FODO with instruments')
    sim.report = 'initialMonitorPositionsReport'
    _run_test(sim, 'initialMonitorPositionsReport', 'madx_position.txt')


def test_controls_position2(fc):
    sim = fc.sr_sim_data('FODO with instruments')
    sim.models.controlSettings.operationMode = 'DeviceServer'
    sim.models.initialMonitorPositionsReport.readOnly = '1'
    sim.report = 'initialMonitorPositionsReport'
    _run_test(sim, 'initialMonitorPositionsReport', 'device_server_position.txt')


def _run_test(sim, report, expect_file):
    from sirepo.template import controls
    pkunit.file_eq(
        pkunit.data_dir().join(expect_file),
        actual=controls.python_source_for_model(sim, report),
    )
