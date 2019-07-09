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


#: Codes on beta and prod;'shadow' is unsupported on F29 for now
_NON_ALPHA_CODES = ('srw', 'warppba', 'elegant', 'warpvnd', 'rs4pi', 'jspec', 'synergia', 'zgoubi')

#: Codes on dev and alpha
_ALPHA_CODES = ('myapp', 'adm', 'flash', 'webcon')

#: All possible codes
_ALL_CODES = _NON_ALPHA_CODES + _ALPHA_CODES

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
def _cfg_sim_types(value):
    res = pkconfig.parse_tuple(value)
    if not res:
        return _codes()
    for c in res:
        assert c in _codes(), \
            'invalid sim_type={}, expected one of={}'.format(c, _codes())
    return res


def _codes(want_all=None):
    if want_all is None:
        want_all = pkconfig.channel_in_internal_test()
    return _ALL_CODES if want_all else _NON_ALPHA_CODES


cfg = pkconfig.init(
    api_modules=((), tuple, 'optional api modules, e.g. status'),
    runner_daemon=(False, bool, 'use the runner daemon'),
    #TODO(robnagler) make sim_type config
    rs4pi_dose_calc=(False, bool, 'run the real dose calculator'),
    sim_types=(None, _cfg_sim_types, 'simulation types (codes) to be imported'),
    srw=dict(
        mask_in_toolbar=(pkconfig.channel_in_internal_test(), bool, 'Show the mask element in toolbar'),
    ),
    warpvnd=dict(
        allow_3d_mode=(pkconfig.channel_in_internal_test() or pkconfig.channel_in('beta'), bool, 'Include 3D features in the Warp VND UI'),
        display_test_boxes=(pkconfig.channel_in_internal_test(), bool, 'Display test boxes to visualize 3D -> 2D projections'),
    ),
)
