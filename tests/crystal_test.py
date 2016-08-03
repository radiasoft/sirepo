# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.srw.py`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import pytest

pytest.importorskip('srwl_bl')


def test_get_crystal_parameters():
    from sirepo import crystal
    for case in (
            (('Silicon', 20368, 1, 1, 1), (3.135531576941939, -2.3353e-06, 8.6843e-09, 1.2299e-06, 6.0601e-09)),
            (('Silicon', 20368, '1', '1', '1'), (None, None, None, None, None)),
            (('Silicon', 12700, 1, 1, 1), (3.135531576941939, -6.0335e-06, 5.7615e-08, 3.1821e-06, 4.0182e-08)),
    ):
        d, xr0, xi0, xrh, xih = crystal.get_crystal_parameters(
            material=case[0][0],
            energy_eV=case[0][1],
            h=case[0][2],
            k=case[0][3],
            l=case[0][4],
        )
        assert d == case[1][0]
        assert xr0 == case[1][1]
        assert xi0 == case[1][2]
        assert xrh == case[1][3]
        assert xih == case[1][4]


def test_get_crystal_parameters_str():
    from sirepo import crystal
    case = (('Silicon', '20368', 1, 1, 1), (3.135531576941939, -2.3353e-06, 8.6843e-09, 1.2299e-06, 6.0601e-09))
    with pytest.raises(TypeError):
        d, xr0, xi0, xrh, xih = crystal.get_crystal_parameters(
            material=case[0][0],
            energy_eV=case[0][1],
            h=case[0][2],
            k=case[0][3],
            l=case[0][4],
        )
