"""Common pkcli operations

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def import_module(type_or_data):
    """Load the simulation_type pkcli module

    Args:
        type_or_data (str or dict): simulation type or description
    Returns:
        module: simulation type module instance
    """
    from sirepo import util

    return util.import_submodule("pkcli", type_or_data)
