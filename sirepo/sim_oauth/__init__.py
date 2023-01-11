# -*- coding: utf-8 -*-
"""Type agnostic OAuth operations

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import sirepo.util


def import_module(type_or_data):
    """Load the simulation_type module

    Args:
        type_or_data (str or dict): simulation type or description
    Returns:
        module: simulation type module instance
    """
    return sirepo.util.import_submodule("sim_oauth", type_or_data)
