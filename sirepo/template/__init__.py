# -*- coding: utf-8 -*-
"""Templates are used to configure codes

:copyright: Copyright (c) 2016-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import sirepo.util


def assert_sim_type(*args, **kwargs):
    """DEPRECATED"""
    return sirepo.util.assert_sim_type(*args, **kwargs)


def import_module(type_or_data):
    """Load the simulation_type module

    Args:
        type_or_data (str or dict): simulation type or description
    Returns:
        module: simulation type module instance
    """
    return sirepo.util.import_submodule("template", type_or_data)


def is_sim_type(*args, **kwargs):
    """DEPRECATED"""
    return sirepo.util.is_sim_type(*args, **kwargs)


def run_epilogue(sim_type):
    # POSIT: only called from a parameters.py run by server and
    # cwd is the run_dir
    return getattr(import_module(sim_type), "run_epilogue")()
