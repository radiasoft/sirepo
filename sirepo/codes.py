# -*- coding: utf-8 -*-
u"""List of codes

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
# No sirepo imports so this can be used in test setup

#: Codes that depend on other codes. [x][0] depends on [x][1]
DEPENDENT_CODES = [
    ['jspec', 'elegant'],
    ['controls', 'madx'],
]

#: Codes on prod
PROD_FOSS_CODES = frozenset((
    'controls',
    'elegant',
    'jspec',
    'madx',
    'ml',
    'opal',
    'radia',
    'shadow',
    'srw',
    'synergia',
    'warppba',
    'warpvnd',
    'zgoubi',
))

#: Codes on dev, alpha, and beta
_NON_PROD_FOSS_CODES = frozenset((
    'irad',
    'myapp',
    'rcscon',
    'rs4pi',
    'silas',
))

#: All possible open source codes
FOSS_CODES = PROD_FOSS_CODES.union(_NON_PROD_FOSS_CODES)
