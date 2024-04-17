"""Test sequential reports

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_controls(fc):
    _r(
        fc,
        "Sample MAD-X beamline",
        "initialMonitorPositionsReport",
    )


def test_elegant(fc):
    _r(
        fc,
        "Compact Storage Ring",
        "twissReport",
    )


def test_madx(fc):
    _r(
        fc,
        "FODO PTC",
        "bunchReport1",
    )


def test_activait(fc):
    _r(
        fc,
        "2019 World Happiness",
        "fileColumnReport1",
    )


def test_opal(fc):
    _r(
        fc,
        "Slit-1",
        "bunchReport1",
    )


def test_radia(fc):
    _r(
        fc,
        "Parameterized C-Bend Dipole",
        "geometryReport",
    )


def test_shadow(fc):
    _r(
        fc,
        "Diffraction Profile",
        "beamStatisticsReport",
    )


def test_srw(fc):
    _r(
        fc,
        "Young's Double Slit Experiment",
        "initialIntensityReport",
    )


def test_srw_brightness(fc):
    _r(
        fc,
        "Young's Double Slit Experiment",
        "brillianceReport",
    )


def test_warppba(fc):
    _r(
        fc,
        "Laser Pulse",
        "laserPreviewReport",
    )


def test_zgoubi(fc):
    _r(
        fc,
        "Los Alamos Proton Storage Ring",
        "twissReport",
    )


def _r(fc, sim_name, analysis_model):
    from pykern.pkdebug import pkdp, pkdlog
    from sirepo import srunit
    from pykern import pkunit
    import re
    import time

    data = fc.sr_sim_data(sim_name)
    r = fc.sr_run_sim(data, analysis_model)
    pkunit.pkeq("completed", r.state)
