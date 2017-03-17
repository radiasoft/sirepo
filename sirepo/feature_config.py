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

#: All possible codes
_ALL_CODES = ('srw', 'warp', 'elegant', 'shadow')

#: Codes on test and prod
_NON_DEV_CODES = _ALL_CODES

#: Configuration
cfg = None

def for_sim_type(sim_type):
    """Get cfg for simulation type

    Args:
        sim_type (str): srw, warp, etc.

    Returns:
        dict: application specific config
    """
    if sim_type not in cfg:
        return {}
    return pkcollections.map_to_dict(cfg[sim_type])


@pkconfig.parse_none
def _cfg_bool(value):
    """Convert str to integer and then bool"""
    if isinstance(value, str):
        value = int(value)
    return bool(value)


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
    srw=dict(
        mask_in_toolbar=(pkconfig.channel_in_internal_test(), _cfg_bool, 'Show the mask element in toolbar'),
        sample_in_toolbar=(pkconfig.channel_in_internal_test(), _cfg_bool, 'Show the sample element in toolbar'),
    ),
    sim_types=(None, _cfg_sim_types, 'simulation types (codes) to be imported'),
)
