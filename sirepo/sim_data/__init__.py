# -*- coding: utf-8 -*-
u"""Type-based simulation operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkcollections
import importlib

def get_class(type_or_data):
    """Simulation data class

    Args:
        type_or_data (str or dict): simulation type or description
    Returns:
        type: simulation data operation class
    """
    if isinstance(type_or_data, dict):
        type_or_data = type_or_data['simulationType']
    return importlib.import_module('.' + type_or_data, __name__).SimData


class SimDataBase(object):

    @classmethod
    def model_defaults(cls, name, schema):
        """Returns a set of default model values from the schema."""
        res = pkcollections.Dict()
        for f in schema.model[name]:
            field_info = schema.model[name][f]
            if len(field_info) >= 3 and field_info[2] is not None:
                res[f] = field_info[2]
        return res

    @classmethod
    def organize_example(cls, data):
        if 'isExample' in data.models.simulation and data.models.simulation.isExample:
            if data.models.simulation.folder == '/':
                data.models.simulation.folder = '/Examples'


    @classmethod
    def update_model_defaults(cls, model, name, schema, dynamic=None):
        defaults = cls.model_defaults(name, schema)
        if dynamic is not None:
            defaults.update(dynamic)
        for f in defaults:
            if f not in model:
                model[f] = defaults[f]
