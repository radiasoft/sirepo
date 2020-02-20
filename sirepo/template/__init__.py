# -*- coding: utf-8 -*-
u"""Templates are used to configure codes

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import importlib
from pykern.pkdebug import pkdc, pkdp
from pykern import pkconfig
from sirepo import feature_config


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


def is_sim_type(sim_type):
    """Validate simulation type

    Args:
        sim_type (str): to check

    Returns:
        bool: true if is a sim_type
    """
    return sim_type in feature_config.cfg().sim_types


def assert_sim_type(sim_type):
    """Validate simulation type

    Args:
        sim_type (str): to check

    Returns:
        str: validated sim_type
    """
    assert is_sim_type(sim_type), 'invalid simulation type={}'.format(sim_type)
    return sim_type
