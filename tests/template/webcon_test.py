# -*- coding: utf-8 -*-
u"""Test for sirepo.template.elegant

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest
import Equation as eq

pytest.importorskip('sdds')

elegant = None

def test_equations():
    eq1 = 'a * np.cos(b * x**2. + c) * np.exp(-x)'
    v1 = 'x'
    p1 = ['a', 'b', 'c']