# -*- coding: utf-8 -*-
u"""List of features available

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp
from pykern import pkconfig
from pykern import pkcollections
import copy

#: Codes on test and prod
_NON_DEV_CODES = ('srw', 'warppba', 'elegant', 'shadow', 'hellweg', 'warpvnd', 'rs4pi', 'jspec', 'synergia')

_DEV_CODES = ('myapp', )

#: All possible codes
_ALL_CODES = _NON_DEV_CODES + _DEV_CODES


#: Configuration
cfg = None

def for_sim_type(sim_type):
    """Get cfg for simulation type

    Args:
        sim_type (str): srw, warppba, etc.

    Returns:
        dict: application specific config
    """
    if sim_type not in cfg:
        return {}
    return pkcollections.map_to_dict(cfg[sim_type])


@pkconfig.parse_none
def _cfg_api_modules(value):
    if isinstance(value, (tuple, list)):
        return tuple(value)
    if not value:
        return tuple()
    return tuple(value.split(':'))


@pkconfig.parse_none
def _cfg_sim_types(value):
    if not value:
        return _codes()
    user_specified_codes = tuple(value.split(':'))
    for c in user_specified_codes:
        assert c in _codes(), \
            '{}: invalid sim_type, must be one of/combination of: {}'.format(c, _codes())
    return user_specified_codes


def _codes(want_all=pkconfig.channel_in('dev')):
    return _ALL_CODES if want_all else _NON_DEV_CODES


cfg = pkconfig.init(
    api_modules=(None, _cfg_api_modules, 'optional api modules, e.g. bluesky'),
    #TODO(robnagler) make sim_type config
    rs4pi_dose_calc=(False, bool, 'run the real dose calculator'),
    sim_types=(None, _cfg_sim_types, 'simulation types (codes) to be imported'),
    srw=dict(
        mask_in_toolbar=(pkconfig.channel_in_internal_test(), bool, 'Show the mask element in toolbar'),
    ),
    warpvnd=dict(
        allow_3d_mode=(pkconfig.channel_in_internal_test(), bool, 'Include 3D features in the Warp VND UI'),
        display_test_boxes=(pkconfig.channel_in_internal_test(), bool, 'Display test boxes to visualize 3D -> 2D projections'),
    ),
)
