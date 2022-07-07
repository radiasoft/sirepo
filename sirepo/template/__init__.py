# -*- coding: utf-8 -*-
u"""Templates are used to configure codes

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdc, pkdp
from sirepo import feature_config
import sirepo.util


def assert_sim_type(sim_type):
    """Validate simulation type

    Args:
        sim_type (str): to check

    Returns:
        str: validated sim_type
    """
    assert is_sim_type(sim_type), 'invalid simulation type={}'.format(sim_type)
    return sim_type


def import_module(type_or_data):

    """Load the simulation_type module

    Args:
        type_or_data (str or dict): simulation type or description
    Returns:
        module: simulation type module instance
    """
    return sirepo.util.import_submodule('template', type_or_data)


def is_sim_type(sim_type):
    """Validate simulation type

    Args:
        sim_type (str): to check

    Returns:
        bool: true if is a sim_type
    """
    return sim_type in feature_config.cfg().sim_types


def run_epilogue(sim_type):
    # POSIT: only called from a parameters.py run by server and
    # cwd is the run_dir
    t = import_module(sim_type)
    return getattr(t, 'run_epilogue')()
