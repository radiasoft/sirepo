# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.code_variable.py`

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import pytest

def test_cache():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq
    from sirepo.template.code_variable import CodeVar, PurePythonEval
    code_var = CodeVar(
        [
            PKDict(
                name='x',
                value='123',
            ),
            PKDict(
                name='y',
                value='x + x',
            ),
            PKDict(
                name='z',
                value='y * -20',
            ),
        ],
        PurePythonEval(),
    )
    pkeq(
        code_var.compute_cache(
            # data
            PKDict(
                models=PKDict(
                    beamlines=[],
                    elements=[
                        PKDict(
                            _id=1,
                            type='point',
                            p1='x + y',
                            p2=234,
                        ),
                    ],
                    commands=[],
                )
            ),
            # schema
            PKDict(
                model=PKDict(
                    point=PKDict(
                        p1=["P1", "RPNValue", 0],
                        p2=["P2", "RPNValue", 0],
                    )
                ),
            ),
        ),
        PKDict({
            'x + x': 246,
            'x + y': 369,
            'x': 123,
            'y * -20': -4920,
            'y': 246,
            'z': -4920,
        })
    )
    pkeq(
        code_var.get_expr_dependencies('x x * x +'),
        ['x'],
    )
    pkeq(
        code_var.get_expr_dependencies('y 2 pow'),
        ['x', 'y'],
    )


def test_case_insensitive():
    # tests case insensitive and attribute like variables
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq
    from sirepo.template.code_variable import CodeVar, PurePythonEval
    code_var = CodeVar(
        [
            PKDict(
                name='x.x7.x',
                value='123',
            ),
            PKDict(
                name='Y',
                value='x.X7.x + x.x7.x',
            ),
        ],
        PurePythonEval(),
        case_insensitive=True,
    )
    pkeq(
        code_var.compute_cache(
            PKDict(
                models=PKDict(
                    beamlines=[],
                    elements=[],
                    commands=[],
                )
            ),
            PKDict(),
        ),
        PKDict({
            'x.x7.x': 123,
            'y': 246,
            'x.x7.x + x.x7.x': 246,
        })
    )
    pkeq(
        code_var.get_expr_dependencies('Y y +'),
        ['x.x7.x', 'y'],
    )


def test_eval():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq
    from sirepo.template.code_variable import CodeVar, PurePythonEval
    code_var = CodeVar(
        [
            PKDict(
                name='gamma',
                value='(bend_energy * 1e-3 + EMASS) / EMASS',
            ),
            PKDict(
                name='bend_energy',
                value=6.50762633,
            ),
        ],
        PurePythonEval(PKDict(
            CLIGHT=299792458,
            EMASS=0.00051099892,
        )),
    )
    pkeq(0.9973461123895662, code_var.eval_var('sqrt(1 - (1/pow(gamma, 2)))')[0])
    pkeq('unknown token: abc', code_var.eval_var('abc + 123')[1])
    pkeq('division by zero', code_var.eval_var('100 / 0')[1])
    pkeq('1 1 gamma 2 pow / - sqrt', code_var.infix_to_postfix('sqrt(1 - (1/pow(gamma, 2)))'))
    pkeq(True, code_var.is_var_value('abc'))
    pkeq(False, code_var.is_var_value('-1.234e-6'))
    pkeq(False, code_var.is_var_value('0'))


def test_eval2():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq
    from sirepo.template.code_variable import CodeVar, PurePythonEval
    code_var = CodeVar(
        [PKDict(
            name=x[0],
            value=x[1]
        ) for x in (
            ['lcend0d5', '66.0000298158'],
            ['thd0', '0.0036745387'],
            ['lpld0d5', 'lcend0d5 / cos(thd0)'],
            ['lpld0q1', '1.2646485614'],
            ['lplq1q2', '1.6766315'],
            ['lplq2q3', '1.8607395'],
            ['lcor', '0.5'],
            ['lcq4', '0.5442755 - (lcor /2.0)'],
            ['lsxt', '0.75'],
            ['lqs', '0.50605 - (lsxt / 2.0)'],
            ['lqb', '1.1072776'],
            ['lsb', '(lqb - lqs) - lsxt'],
            ['lplq4q5', '6.0190255 - lcq4 - lqs - lsxt - lsb - lcor'],
            ['lq', '1.11'],
            ['lplq5q6', '14.8110470957 - lq'],
            ['lcq', '0.54525 - (lcor / 2.0)'],
            ['lplq5d5', '(lplq5q6 / 2.0) - lcq - lcor'],
            ['lpltemp', 'lpld0d5 - lpld0q1 - lplq1q2 - lplq2q3 - lplq4q5 - lplq5d5'],
            ['lq1', '1.44'],
            ['lq2', '3.391633'],
            ['lq3', '2.100484'],
            ['lq4', '1.811949'],
            ['lqb4', '1.1326896'],
            ['lsb4', 'lqb4 - lqs - lsxt'],
            ['lqs4', '0.5050755 - (lsxt / 2.0)'],
            ['lplq3q4', 'lpltemp - lq1 - lq2 - lq3 - lq4 - lq - lsb4 - lsb - lqs4 - lqs - lcq - lcq4 - (2.0 * (lsxt + lcor))'],
            ['lbfl3', '1.53902'],
            ['lbc3', '0.47142826 - (lcor / 2.0)'],
            ['lcq3a', '0.597968 - (lcor / 2.0)'],
            ['lbfl4', '0.61279'],
            ['l3space', 'lplq3q4 - lbfl3 - lbc3 - lcor - lcq3a - lbfl4'],
            ['lbsk12iy', '0.042545'],
            ['lbsk12ly', '0.048638'],
            ['lpolfll', '0.837184'],
            ['lpolflm', '0.508'],
            ['lpolfls', '0.760984'],
            ['lipmfls', '0.886116'],
            ['lipmfll', '0.282284'],
            ['lcpufl', '0.3937'],
            ['leldfl', '0.119634'],
            ['l3y12sum', 'lpolfll + lpolflm + lpolfls + lipmfls + lipmfll  + 2.0 * ((2.0 * lcpufl) + leldfl)'],
            ['l3y12l29', 'l3space - lbsk12iy - lbsk12ly - l3y12sum - 28.899634'],
        )],
        PurePythonEval(PKDict()),
    )
    pkeq(0.042466423001805254, code_var.eval_var('l3y12l29')[0])


def test_infix_to_postfix():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq
    from sirepo.template.code_variable import CodeVar, PurePythonEval
    code_var = CodeVar([], PurePythonEval(PKDict()))
    pkeq(code_var.infix_to_postfix('x + y * 2'), 'x y 2 * +')
    pkeq(code_var.infix_to_postfix('-(((x)))'), 'x chs')
    pkeq(code_var.infix_to_postfix('-(x + +x)'), 'x x + chs')
    # leave alone if already in postfix format
    pkeq(code_var.infix_to_postfix('x x + chs'), 'x x + chs')


def test_postfix_to_infix():
    from pykern.pkcollections import PKDict
    from pykern.pkunit import pkeq
    from sirepo.template.code_variable import PurePythonEval
    ppe = PurePythonEval()
    pkeq(ppe.postfix_to_infix('x y 2 * +'), 'x + (y * 2)')
    pkeq(ppe.postfix_to_infix('x x + chs'), '-(x + x)')
    pkeq(ppe.postfix_to_infix('30 360 / 2 * pi *'), '((30 / 360) * 2) * pi')
    # leave alone if already in infix format
    pkeq(ppe.postfix_to_infix('x + (y * 2)'), 'x + (y * 2)')
