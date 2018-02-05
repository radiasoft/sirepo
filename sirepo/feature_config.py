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
_ALL_CODES = ('srw', 'warppba', 'elegant', 'shadow', 'hellweg', 'warpvnd', 'rs4pi', 'jspec')
assert [] == [x for x in _ALL_CODES if len(x) >= 8], \
    'codes must be less than 8 characters (simulation_db._ID_LEN)'

#: Codes on test and prod
_NON_DEV_CODES = _ALL_CODES

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
        mask_in_toolbar=(pkconfig.channel_in_internal_test(), bool, 'Show the mask element in toolbar'),
        brilliance_report=(pkconfig.channel_in_internal_test(), bool, 'Show the Brilliance Report'),
    ),
    sim_types=(None, _cfg_sim_types, 'simulation types (codes) to be imported'),
    rs4pi_dose_calc=(False, bool, 'run the real dose calculator'),
)
