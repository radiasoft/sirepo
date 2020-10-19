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
            'x': 123,
            'y': 246,
            'x + x': 246,
            'y * -20': -4920,
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
