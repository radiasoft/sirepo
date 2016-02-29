# -*- coding: utf-8 -*-
u"""Templates are used to configure codes

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import importlib

from pykern.pkdebug import pkdc, pkdp

def import_module(simulation_type):
    """Load the simulation_type module

    Args:
        simulation_type (str): base name of the module, e.g. srw

    Returns:
        module: simulation type module instance
    """
    return importlib.import_module('.' + simulation_type, __name__)
