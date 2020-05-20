# -*- coding: utf-8 -*-
u"""List of features available

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
# defer all imports so *_CODES is available to testing functions


#: Codes on beta and prod
NON_ALPHA_CODES = frozenset((
    'elegant',
    'jspec',
    'opal',
    'shadow',
    'srw',
    'synergia',
    'warppba',
    'warpvnd',
    'webcon',
    'zgoubi',
))

#: Codes on dev and alpha
ALPHA_CODES = frozenset((
    'flash',
    'radia',
    'madx',
    'myapp',
    'rcscon',
    'rs4pi',
))

#: All possible codes
ALL_CODES = NON_ALPHA_CODES.union(ALPHA_CODES)


_DEFAULT_PROPRIETARY_CODES = ('flash',)


#: Configuration
_cfg = None


def cfg():
    """global configuration

    Returns:
        dict: configurated features
    """
    global _cfg
    return _cfg or _init()


def for_sim_type(sim_type):
    """Get cfg for simulation type

    Args:
        sim_type (str): srw, warppba, etc.

    Returns:
        dict: application specific config
    """
    import pykern.pkcollections

    c = cfg()
    if sim_type not in c:
        return pykern.pkcollections.PKDict()
    return pykern.pkcollections.PKDict(
        pykern.pkcollections.map_items(c[sim_type]),
    )


def _init():
    from pykern import pkconfig
    global _cfg

    @pkconfig.parse_none
    def _cfg_sim_types(value):
        res = pkconfig.parse_set(value)
        if not res:
            return tuple(_codes())
        for c in res:
            assert c in _codes(), \
                'invalid sim_type={}, expected one of={}'.format(c, _codes())
        if 'jspec' in res:
            res = set(res)
            res.add('elegant')
        return tuple(res)

    def _codes():
        return ALL_CODES if pkconfig.channel_in_internal_test() \
            else NON_ALPHA_CODES

    _cfg = pkconfig.init(
        api_modules=((), set, 'optional api modules, e.g. status'),
        jspec=dict(
            derbenevskrinsky_force_formula=(pkconfig.channel_in_internal_test(), bool, 'Include Derbenev-Skrinsky force forumla'),
        ),
        proprietary_sim_types=(_DEFAULT_PROPRIETARY_CODES, set, 'codes that require authorization'),
        #TODO(robnagler) make sim_type config
        rs4pi_dose_calc=(False, bool, 'run the real dose calculator'),
        sim_types=(None, _cfg_sim_types, 'simulation types (codes) to be imported'),
        srw=dict(
            mask_in_toolbar=(pkconfig.channel_in_internal_test(), bool, 'Show the mask element in toolbar'),
            beamline3d=(pkconfig.channel_in_internal_test(), bool, 'Show 3D beamline plot'),
        ),
        warpvnd=dict(
            allow_3d_mode=(True, bool, 'Include 3D features in the Warp VND UI'),
            display_test_boxes=(pkconfig.channel_in_internal_test(), bool, 'Display test boxes to visualize 3D -> 2D projections'),
        ),
    )
    return _cfg
