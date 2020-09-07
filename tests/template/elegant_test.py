# -*- coding: utf-8 -*-
u"""Test for sirepo.template.elegant

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import pytest

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


def test_file_iterator():
    from sirepo.template import lattice
    from sirepo.template.lattice import LatticeUtil
    from pykern.pkunit import pkeq
    data = _find_example('bunchComp - fourDipoleCSR')
    v = LatticeUtil(data, _elegant()._SCHEMA).iterate_models(
        lattice.InputFileIterator(_elegant()._SIM_DATA)).result
    pkeq(v, ['WAKE-inputfile.knsl45.liwake.sdds'])


def _elegant():
    global elegant
    if not elegant:
        import sirepo.template
        elegant = sirepo.template.import_module('elegant')
    return elegant


def _expr(expr, expect, variables=None):
    from pykern.pkunit import pkok, pkfail
    res = _elegant().get_application_data(PKDict(
        method='rpn_value',
        value=expr,
        variables=variables or {},
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


def _find_example(name):
    from sirepo import simulation_db
    for ex in simulation_db.examples(_elegant().SIM_TYPE):
        if ex.models.simulation.name == name:
            return simulation_db.fixup_old_data(ex)[0]
    assert False, 'no example named: {}'.format(name)
