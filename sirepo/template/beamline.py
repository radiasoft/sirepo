# -*- coding: utf-8 -*-
u"""Beamline utilities.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import re

class ModelIterator(object):
    """Base class for model iterators with stubbed out methods.
    When iterate_models() is called, the iterator calls are made:

        it.start(model)
        foreach field in model:
            it.field(model, field_schema, field)
        it.end(model)
    """

    def end(self, model):
        pass

    def field(self, model, field_schema, field):
        pass

    def start(self, model):
        pass


class ElementIterator(ModelIterator):
    """Iterate all fields, adding any set to non-default values to the results.
    """
    def __init__(self, filename_map, beamline_map, formatter):
        self.result = []
        self.filename_map = filename_map
        self.beamline_map = beamline_map
        self.formatter = formatter

    def end(self, model):
        self.result.append([model, self.fields])

    def field(self, model, field_schema, field):
        self.field_index += 1
        if self.is_ignore_field(field) or self.__is_default(model, field_schema, field):
            return
        self.fields.append(
            self.formatter(self, model, field_schema[1], field, model[field]))

    def is_ignore_field(self, field):
        return False

    def start(self, model):
        self.field_index = 0
        self.fields = []

    def __is_default(self, model, field_schema, field):
        if len(field_schema) < 3:
            return True
        default_value = field_schema[2]
        value = model[field]
        if value is not None and default_value is not None:
            return str(value) == str(default_value)
        return True


class InputFileIterator(ModelIterator):
    """Iterate and extract all InputFile filenames.
    """
    def __init__(self, sim_data):
        self.result = []
        self.sim_data = sim_data

    def field(self, model, field_schema, field):
        if model[field] and field_schema[1].startswith('InputFile'):
             self.result.append(self.sim_data.lib_file_name(model_name_for_data(model), field, model[field]))


class LatticeIterator(ElementIterator):
    """Iterate all lattice elements/fields which are not set to the default value.
    """
    def is_ignore_field(self, field):
        return field in ['name', 'type', '_id'] or re.search('(X|Y|File)$', field)

    def start(self, model):
        super(LatticeIterator, self).start(model)
        self.beamline_map[model._id] = model.name


def build_beamline_name_map(data):
    """Returns a map of beamlines, (beamline.id => beamline.name).
    """
    res = PKDict()
    for bl in data.models.beamlines:
        res[bl.id] = bl.name
    return res


def is_command(model):
    """Is the model a command or a lattice element?
    """
    return '_type' in model


def iterate_models(schema, data, model_iterator, name=None):
    """Iterate the models in the named container.
    By default the commands and elements containers are iterated.
    """
    names = (name, ) if name else ('commands', 'elements')
    for name in names:
        for m in data.models[name]:
            model_schema = schema.model[model_name_for_data(m)]
            model_iterator.start(m)
            for k in sorted(m):
                if k in model_schema:
                    model_iterator.field(m, model_schema[k], k)
            model_iterator.end(m)
    return model_iterator


def model_name_for_data(model):
    """Returns the model's schema name.
    """
    return 'command_{}'.format(model._type) if is_command(model) else model.type


def render_beamline(beamlines, beamline_map, quote_name=False, want_semicolon=False):
    """Render the beamlines list in precedence order.
    """
    ordered_beamlines = []
    for id in beamlines:
        _add_beamlines(beamlines[id], beamlines, ordered_beamlines)
    res = ''
    for bl in ordered_beamlines:
        if len(bl['items']):
            name = bl.name.upper()
            if quote_name:
                name = '"{}"'.format(name)
            res += '{}: LINE=('.format(name)
            for id in bl['items']:
                sign = ''
                if id < 0:
                    sign = '-'
                    id = abs(id)
                res += '{},'.format(sign + beamline_map[id].upper())
            res = res[:-1]
            res += ')'
            if want_semicolon:
                res += ';'
            res += '\n'
    return res


def render_lattice(items, quote_name=False, want_semicolon=False):
    """Render lattice elements.
    """
    res = ''
    for el in items:
        name = el[0].name.upper()
        if quote_name:
            name = '"{}"'.format(name)
        res += '{}: {},'.format(name, el[0].type)
        for f in el[1]:
            res += '{}={},'.format(f[0], f[1])
        res = res[:-1]
        if want_semicolon:
            res += ';'
        res += '\n'
    return res


def sort_elements_and_beamlines(data):
    m = data.models
    m.elements = sorted(m.elements, key=lambda e: (e.type, e.name.lower()))
    m.beamlines = sorted(m.beamlines, key=lambda e: e.name.lower())


def _add_beamlines(beamline, beamlines, ordered_beamlines):
    if beamline in ordered_beamlines:
        return
    for id in beamline['items']:
        id = abs(id)
        if id in beamlines:
            _add_beamlines(beamlines[id], beamlines, ordered_beamlines)
    ordered_beamlines.append(beamline)
