# -*- coding: utf-8 -*-
u"""Test for sirepo.template.elegant

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest

pytest.importorskip('sdds')

elegant = None

def test_get_application_data():
    _expr('1 1 +', 2.0)
    _expr('3 1 1 + *', 6.0)
    _expr('2.72 ln', 1)
    _expr('1 2 < ? 3 : 4 $', 3)
    _expr('3 2 pow', 9)
    _expr('3 1 +', 4)
    _expr('ln(2.72)', 1)
    _expr('1 2 < ? 3 : 4 $', 3)
    _expr('3 2 pow', 9)
    _expr('(1+1)*3', 6.0)
    _expr('sin(sqrt((1+1*2.0)*3)+.14)+13', 13)


def _expr(expr, expect, variables=None):
    from pykern.pkunit import pkok, pkfail
    global elegant

    if not elegant:
        import sirepo.template
        elegant = sirepo.template.import_module('elegant')
    res = elegant.get_application_data(dict(
        method='rpn_value',
        value=expr,
        variables=(variables or {}),
    ))
    if not 'result' in res:
        pkfail('{}: no result for {}', res, expr)
    delta = abs(float(expect) - float(res['result']))
    pkok(
        # Only needs to be very approximate
        delta < 0.01,
        '(expected) {} != {} (actual) expr={}',
        expect,
        float(res['result']),
        expr,
    )
