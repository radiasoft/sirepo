# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.importer`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkunit
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
import pytest

pytest.importorskip('sdds')

def test_rpn():
    # postfix
    assert _rpn_value({
        'value': '1 2 +',
    })['result'] == 3.0
    # infix
    assert _rpn_value({
        'value': '1 + 2',
    })['result'] == 3.0
    # rpndef variable
    assert _rpn_value({
        'value': 'pi',
    })['result'] == 3.14159265358979
    # mix of infix and postfix with variables
    assert _rpn_value({
        'value': 'vlong',
        'variables': [
            PKDict({
                'name': 'pi16',
                'value': 'pi 16 /',
            }),
            PKDict({
                'name': 'vlong',
                'value': '((pi32 + 1) * (pi16 + 1)) / 2 + vsum',
            }),
            PKDict({
                'name': 'pi32',
                'value': 'pi / 32',
            }),
            PKDict({
                'name': 'vsum',
                'value': 'pi16 + pi32',
            }),
        ],
    })['result'] == 0.951424752459004
    # error
    assert _rpn_value({
        'value': 'badvalue',
    })['error'] == 'invalid'


def _rpn_value(v):
    from sirepo.template import elegant
    v = PKDict(v)
    v.method = 'rpn_value'
    if 'variables' not in v:
        v.variables = []
    return elegant.get_application_data(v)
