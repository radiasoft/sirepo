# -*- coding: utf-8 -*-
u"""Templates are used to configure codes

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import importlib
from pykern.pkdebug import pkdc, pkdp
from pykern import pkconfig

#: valid simulations
# SIM_TYPES = ['srw', 'warp', 'elegant', 'shadow'] if pkconfig.channel_in('dev') else ['srw', 'warp', 'elegant']


def import_module(type_or_data):

    """Load the simulation_type module

    Args:
        type_or_data (str or dict): simulation type or description
    Returns:
        module: simulation type module instance
    """
    if isinstance(type_or_data, dict):
        type_or_data = type_or_data['simulationType']
    return importlib.import_module('.' + assert_sim_type(type_or_data), __name__)


def assert_sim_type(sim_type):
    """Validate simulation type

    Args:
        sim_type (str): to check

    Returns:
        str: sim_type
    """
    assert sim_type in SIM_TYPES, \
        '{}: invalid simulation type'
    return sim_type


def codes(is_dev_channel):
    return ('srw', 'warp', 'elegant', 'shadow') if is_dev_channel else ('srw', 'warp', 'elegant')


def _cfg_codes(value):
    if type(value) is tuple:
        return value
    return tuple(value.split(':'))


cfg = pkconfig.init(
    codes=(codes(pkconfig.channel_in('dev')), _cfg_codes, 'control which codes are loaded in the server'),
)
SIM_TYPES = cfg.codes
pkdp(SIM_TYPES)
