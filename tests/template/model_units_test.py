# -*- coding: utf-8 -*-
u"""Test sirepo.cookie

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import pytest


def test_model_units():
    from sirepo.template.template_common import ModelUnits
    import re

    def _xpas(value, is_native):
        cm_to_m = lambda v: ModelUnits.scale_value(v, 'cm_to_m', is_native)
        if is_native:
            if re.search(r'^#', str(value)):
                value = re.sub(r'^#', '', value)
                return map(cm_to_m, value.split('|'))
        else:
            if type(value) is list:
                return '#' + '|'.join(map(str, map(lambda v: int(cm_to_m(v)), value)))
        return cm_to_m(value)

    units = ModelUnits({
        'CHANGREF': {
            'XCE': 'cm_to_m',
            'YCE': 'cm_to_m',
            'ALE': 'deg_to_rad',
            'XPAS': _xpas,
        },
    })
    native_model = {
        'XCE': 2,
        'YCE': 0,
        'ALE': 8,
        'XPAS': '#20|20|20',
    }
    sirepo_model = units.scale_from_native('CHANGREF', native_model.copy())
    assert sirepo_model == {
        'XCE': 2e-2,
        'YCE': 0,
        'ALE': 0.13962634015954636,
        'XPAS': [2e-1, 2e-1, 2e-1],
    }

    assert native_model == units.scale_to_native('CHANGREF', sirepo_model.copy())

    assert units.scale_from_native('CHANGREF', {
        'XPAS': '20',
    })['XPAS'] == 0.2

    assert ModelUnits.scale_value(2, 'cm_to_m', True) == 2e-2
    assert ModelUnits.scale_value(0.02, 'cm_to_m', False) == 2
