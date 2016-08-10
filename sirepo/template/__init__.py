# -*- coding: utf-8 -*-
u"""Templates are used to configure codes

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import importlib
from pykern.pkdebug import pkdc, pkdp


def import_module(type_or_data):
    """Load the simulation_type module

    Args:
        type_or_data (str or dict): simulation type or description
    Returns:
        module: simulation type module instance
    """
    if isinstance(type_or_data, dict):
        type_or_data = type_or_data['simulationType']
    return importlib.import_module('.' + type_or_data, __name__)
