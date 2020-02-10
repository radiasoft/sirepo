# -*- coding: utf-8 -*-
u"""Lattice utilities.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
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
    def __init__(self, filename_map, formatter):
        self.result = []
        self.filename_map = filename_map
        self.formatter = formatter

    def end(self, model):
        self.result.append([model, self.fields])

    def field(self, model, field_schema, field):
        self.field_index += 1
        if self.is_ignore_field(field) or self.__is_default(model, field_schema, field):
            return
        f = self.formatter(self, model, field, field_schema[1])
        if f:
            self.fields.append(f)

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
            self.result.append(self.sim_data.lib_file_name_with_model_field(
                LatticeUtil.model_name_for_data(model), field, model[field]))


class LatticeIterator(ElementIterator):
    """Iterate all lattice elements/fields which are not set to the default value.
    """
    def is_ignore_field(self, field):
        return field in ['name', 'type', '_id'] or re.search('(X|Y|File)$', field)


class LatticeUtil(object):
    """Utility class for generating lattice elements, beamlines and commands.
    """
    def __init__(self, data, schema):
        self.data = data
        self.schema = schema
        self.id_map = self.__build_id_map(data)

    @classmethod
    def is_command(cls, model):
        """Is the model a command or a lattice element?
        """
        return '_type' in model

    def iterate_models(self, iterator, name=None):
        """Iterate the models in the named container.
        By default the commands and elements containers are iterated.
        """
        iterator.id_map = self.id_map
        names = (name, ) if name else ('commands', 'elements')
        for name in names:
            for m in self.data.models[name]:
                model_schema = self.schema.model[LatticeUtil.model_name_for_data(m)]
                iterator.start(m)
                for k in sorted(m):
                    if k in model_schema:
                        iterator.field(m, model_schema[k], k)
                iterator.end(m)
        return iterator

    @classmethod
    def model_name_for_data(cls, model):
        """Returns the model's schema name.
        """
        return 'command_{}'.format(model._type) if cls.is_command(model) else model.type

    def render_lattice(self, fields, quote_name=False, want_semicolon=False):
        """Render lattice elements.
        """
        res = ''
        for el in fields:
            # el is [model, [[f, v], [f, v]...]]
            type_field = '_type' if LatticeUtil.is_command(el[0]) else 'type'
            name = el[0].name.upper()
            if quote_name:
                name = '"{}"'.format(name)
            res += '{}: {},'.format(name, el[0][type_field])
            for f in el[1]:
                res += '{}={},'.format(f[0], f[1])
            res = res[:-1]
            if want_semicolon:
                res += ';'
            res += '\n'
        return res

    def render_lattice_and_beamline(self, iterator, **kwargs):
        return self.render_lattice(
            self.iterate_models(iterator, 'elements').result, **kwargs) \
            + self.__render_beamline(**kwargs)

    def select_beamline(self):
        """Returns the beamline to use based for the selected report.
        """
        sim = self.data.models.simulation
        if self.data.get('report', '') == 'twissReport':
            beamline_id = sim.activeBeamlineId
        else:
            if 'visualizationBeamlineId' not in sim or not sim.visualizationBeamlineId:
                sim.visualizationBeamlineId = self.data.models.beamlines[0].id
            beamline_id = sim.visualizationBeamlineId
        return self.id_map[int(beamline_id)]

    def sort_elements_and_beamlines(self):
        """Sort elements and beamline models in place, by (type, name) and (name)
        """
        m = self.data.models
        m.elements = sorted(m.elements, key=lambda e: (e.type, e.name.lower()))
        m.beamlines = sorted(m.beamlines, key=lambda e: e.name.lower())

    @staticmethod
    def __add_beamlines(beamline, beamlines, ordered_beamlines):
        if beamline in ordered_beamlines:
            return
        for bid in beamline['items']:
            bid = abs(bid)
            if bid in beamlines and 'type' not in beamlines[bid]:
                LatticeUtil.__add_beamlines(beamlines[bid], beamlines, ordered_beamlines)
        ordered_beamlines.append(beamline)

    @staticmethod
    def __build_id_map(data):
        """Returns a map of beamlines and elements, (id => model).
        """
        res = {}
        for bl in data.models.beamlines:
            res[bl.id] = bl
        for el in data.models.elements:
            res[el._id] = el
        if 'commands' in data.models:
            for cmd in data.models.commands:
                res[cmd._id] = cmd
        return res

    def __render_beamline(self, quote_name=False, want_semicolon=False):
        """Render the beamlines list in precedence order.
        """
        ordered_beamlines = []
        for bid in sorted(self.id_map):
            model = self.id_map[bid]
            if 'type' not in model and not self.is_command(model):
                LatticeUtil.__add_beamlines(model, self.id_map, ordered_beamlines)
        res = ''
        for bl in ordered_beamlines:
            if bl['items']:
                name = bl.name.upper()
                if quote_name:
                    name = '"{}"'.format(name)
                res += '{}: LINE=('.format(name)
                for bid in bl['items']:
                    if bid < 0:
                        res += '-'
                    res += '{},'.format(self.id_map[abs(bid)].name.upper())
                res = res[:-1]
                res += ')'
                if want_semicolon:
                    res += ';'
                res += '\n'
        return res
