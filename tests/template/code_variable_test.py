# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.template.code_variable.py`

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import pytest

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
        })
    )
