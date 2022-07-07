# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.srw.py`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import requests
import sirepo.crystal

def _skip():
    try:
        requests.get(sirepo.crystal.X0H_SERVER, timeout=2)
        return False
    except requests.exceptions.ConnectTimeout:
        return True
    except Exception as e:
        raise AssertionError(
            'exception={} trying to reach uri={}'.format(e, sirepo.crystal.X0H_SERVER),
        )


# skips test_srw_calc_bragg_angle too, when the server is unavailable.
pytestmark = pytest.mark.skipif(_skip(), reason='Unable to reach ' + sirepo.crystal.X0H_SERVER)


def test_srw_calc_bragg_angle():
    from sirepo import crystal
    for case in (
            ((3.135531576941939, 20368, 1), (0.06087205076590731, 0.09722123437454372, 5.570366408713557)),
            ((3.1355, 20368, 1), (0.06087205076590731, 0.09722221656509854, 5.570422684087026)),
    ):
        angle_data = crystal.calc_bragg_angle(
            d=case[0][0],
            energy_eV=case[0][1],
            n=case[0][2],
        )
        assert angle_data['lamda'] == case[1][0]
        assert angle_data['bragg_angle'] == case[1][1]
        assert angle_data['bragg_angle_deg'] == case[1][2]


def test_srw_get_crystal_parameters():
    return
    from sirepo import crystal
    expected = (
        (5.4309, 3.135531576941939, 3.135531576941939, 3.1355, -2.3353e-06, 8.6843e-09, 1.2299e-06, 6.0601e-09, 5.5704),
        (5.4309, 3.135531576941939, 3.135531576941939, 3.1355, -6.0335e-06, 5.7615e-08, 3.1821e-06, 4.0182e-08, 8.9561),
    )
    for case in (
            (('Silicon', 20368, 1, 1, 1), expected[0]),
            (('Silicon', 20368, '1', '1', '1'), expected[0]),
            (('Silicon', '20368', 1, 1, 1), expected[0]),
            (('Silicon', 12700, 1, 1, 1), expected[1]),
    ):
        crystal_parameters = crystal.get_crystal_parameters(
            material=case[0][0],
            energy_eV=case[0][1],
            h=case[0][2],
            k=case[0][3],
            l=case[0][4],
        )
        assert crystal_parameters['a1'] == case[1][0]
        assert crystal_parameters['d'] == case[1][1]
        assert crystal_parameters['d_calculated'] == case[1][2]
        assert crystal_parameters['d_server'] == case[1][3]
        assert crystal_parameters['xr0'] == case[1][4]
        assert crystal_parameters['xi0'] == case[1][5]
        assert crystal_parameters['xrh'] == case[1][6]
        assert crystal_parameters['xih'] == case[1][7]
        assert crystal_parameters['bragg_angle_deg'] == case[1][8]


def test_srw_get_crystal_parameters_str():
    from sirepo import crystal
    with pytest.raises(AssertionError):
        _ = crystal.get_crystal_parameters(
            material='Si',
            energy_eV='20368',
            h=1,
            k=1,
            l=1,
        )
