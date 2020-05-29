# -*- coding: utf-8 -*-
u"""Lattice utilities.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template.line_parser import LineParser
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
            if value == default_value:
                return True
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


class LatticeParser(object):
    def __init__(self, sim_data):
        self.sim_data = sim_data
        self.schema = sim_data.schema()

    def parse_file(self, lattice_text):
        from sirepo import simulation_db
        self.data = simulation_db.default_data(self.sim_data.sim_type())
        self.parser = LineParser(100)
        self.data.models.rpnVariables = {}
        self.data.models.sequences = []
        # None | sequence | track | match | edit
        self.container = None
        self.elements_by_name = PKDict()
        lines = lattice_text.replace('\r', '').split('\n')
        self.__parse_lines(lines)
        return self.data

    def _code_variables_to_float(self, code_var):
        for v in self.data.models.rpnVariables:
            if not code_var.is_var_value(v.value):
                v.value = float(v.value)
        for container in ('elements', 'commands'):
            for el in self.data.models[container]:
                model_name = LatticeUtil.model_name_for_data(el)
                for f in self.schema.model[model_name]:
                    if f in el and self.schema.model[model_name][f][1] == 'RPNValue':
                        if not code_var.is_var_value(el[f]):
                            el[f] = float(el[f])

    def _compute_drifts(self, code_var):
        drifts = PKDict()
        for el in self.data.models.elements:
            if el.type == 'DRIFT':
                length = self._format_length(self._eval_var(code_var, el.l))
                if length not in drifts:
                    drifts[length] = el._id
        return drifts

    def _downcase_variables(self, code_var):
        for v in self.data.models.rpnVariables:
            v.name = v.name.lower()
        for container in ('elements', 'commands'):
            for el in self.data.models[container]:
                model_name = LatticeUtil.model_name_for_data(el)
                for f in self.schema.model[model_name]:
                    if f in el and self.schema.model[model_name][f][1] == 'RPNValue':
                        if code_var.is_var_value(el[f]):
                            el[f] = el[f].lower()

    def _eval_var(self, code_var, value):
        return code_var.eval_var_with_assert(value)

    def _format_length(self, length):
        res = '{:.8E}'.format(length)
        res = re.sub(r'(\.\d+?)(0+)E', r'\1e', res)
        res = re.sub(r'e\+00$', '', res)
        return res

    def _get_drift(self, drifts, length, allow_negative_drift=False):
        if length == 0:
            return None
        if length < 0 and not allow_negative_drift:
            pkdlog('warning: negative drift: {}', length)
            return None
        length = self._format_length(length)
        if length not in drifts:
            name = 'D{}'.format(length)
            name = re.sub(r'\+', '', name)
            name = re.sub(r'e?-', 'R', name)
            drift = PKDict(
                _id=self.parser.next_id(),
                l=float(length),
                name=name,
                type='DRIFT',
            )
            self.sim_data.update_model_defaults(drift, 'DRIFT')
            self.data.models.elements.append(drift)
            drifts[length] = drift._id
        return drifts[length]

    def _set_default_beamline(self, cmd_type, field1, field2=None):
        name = None
        for cmd in self.data.models.commands:
            if cmd._type == cmd_type:
                name = None
                if field1 in cmd:
                    name = cmd.get(field1)
                elif field2 and field2 in cmd:
                    name = cmd.get(field2)
                if name and name.upper() in self.elements_by_name:
                    name = name.upper()
                    break
                name = None
        beamline_id = None
        if name:
            beamline_id = self.elements_by_name[name].id
        elif len(self.data.models.beamlines):
            beamline_id = self.data.models.beamlines[-1].id
        self.data.models.simulation.activeBeamlineId = \
            self.data.models.simulation.visualizationBeamlineId = beamline_id

    def __parse_beamline(self, label, values):
        assert label
        values[-1] = re.sub(r'\s*\)$', '', values[-1])
        values[0] = re.sub(r'^.*?=\s*\(\s*', '', values[0])
        res = PKDict(
            name=label,
            id=self.parser.next_id(),
            items=[],
        )
        for v in values:
            v = self.__remove_quotes(v)
            count = 1
            m = re.match(r'^(\d+)\s*\*\s*([\w.]+)$', v)
            if m:
                count = int(m.group(1))
                v = m.group(2)
            reverse = False
            if v[0] == '-':
                reverse = True
                v = v[1:]
            el = self.elements_by_name[v.upper()]
            assert el, 'line: {} element not found: {}'.format(label, v)
            el_id = el._id if '_id' in el else el.id
            for _ in range(count):
                res['items'].append(-el_id if reverse else el_id)
        assert label.upper() not in self.elements_by_name
        self.elements_by_name[label.upper()] = res
        self.data.models.beamlines.append(res)

    def __parse_element(self, cmd, label, values):
        res = self.__parse_fields(values, PKDict(
            name=label,
            _id=self.parser.next_id(),
        ))
        res.type = cmd
        if self.container:
            assert 'at' in res, 'sequence element missing "at": {}'.format(values)
            at = res.at
            del res['at']
            if cmd not in self.schema.model:
                parent = self.elements_by_name[cmd]
                assert parent
                assert len(res) >= 3
                if len(res) == 3:
                    self.container['items'].append([parent._id, at])
                    return
            assert label, 'unlabeled element: {}'.format(values)
            self.container['items'].append([res._id, at])
        assert 'at' not in res
        # copy in superclass values
        while cmd not in self.schema.model:
            parent = self.elements_by_name[cmd]
            assert parent and parent.type
            res = PKDict(list(parent.items()) + list(res.items()))
            res.type = parent.type
            cmd = parent.type
        self.sim_data.update_model_defaults(res, res.type)
        self.data.models.elements.append(res)
        if not label:
            label = values[0].upper()
            assert label in self.elements_by_name, 'no element for label: {}: {}'.format(label, values)
            self.elements_by_name[label].update(res)
        elif label.upper() in self.elements_by_name:
            pkdlog('duplicate label: {}', values)
        else:
            self.elements_by_name[label.upper()] = res
        return res

    def __parse_fields(self, values, res):
        #TODO(pjm): only add fields which are in the schema
        for value in values[1:]:
            m = re.match(r'^\s*([\w.]+)\s*:?=\s*(.+?)\s*$', value)
            if m:
                f, v = m.group(1, 2)
                assert f not in res, 'field already defined: {}, values: {}'.format(f, values)
                res[f.lower()] = self.__remove_quotes(v)
                continue
            m = re.match(r'^\s*(!)?\s*([\w.]+)\s*$', value)
            assert m, 'failed to parse field assignment: {}'.format(value)
            v, f = m.group(1, 2)
            res[f.lower()] = '0' if v else '1'
        return res

    def __parse_lines(self, lines):
        prev_line = ''
        in_comment = False
        for line in lines:
            self.parser.increment_line_number()
            line = re.sub(r'\&\s*$', '', line)
            # strip comments
            line = line.strip()
            line = re.sub(r'(.*?)(!|//).*$', r'\1', line)
            line = re.sub(r'\/\*.*?\*\/', '', line)
            # special case, some commands often missing a comma
            line = re.sub(r'^\s*(title|exec|call)\s+([^,])', r'\1, \2', line, flags=re.IGNORECASE)
            if in_comment and re.search(r'^.*\*\/', line):
                line = re.sub(r'^.*\*\/', '', line)
                in_comment = False
            if re.search(r'\/\*.*$', line):
                line = re.sub(r'\/\*.*$', '', line)
                in_comment = True
            if not line or in_comment:
                continue
            assert not re.search(r'^\s*(if|while)\s*\(', line, re.IGNORECASE), \
                'Remove conditional if() or while() statements from input file before import'
            while ';' in line:
                m = re.match(r'^(.*?);(.*)$', line)
                assert m, 'parse ; failed: {}'.format(line)
                item = (prev_line + ' ' + m.group(1)).strip()
                self.__parse_values(self.__split_values(item))
                line = m.group(2)
                prev_line = ''
            prev_line += line
        self.data.models['rpnVariables'] = [
            PKDict(name=k, value=v) for k, v in self.data.models.rpnVariables.items()
        ]

    def __parse_statement(self, cmd, label, values):
        if cmd.upper() in self.schema.model or cmd.upper() in self.elements_by_name:
            self.__parse_element(cmd.upper(), label, values)
            return
        cmd = cmd.lower()
        if self.container and cmd == 'end{}'.format(self.container.type):
            assert len(values) == 1, 'invalid end{}: {}'.format(self.container, values)
            self.container = None
            return
        if cmd  in ('sequence', 'track'):
            self.container = PKDict(
                name=label,
                type=cmd,
                _id=self.parser.next_id(),
            )
            self.__parse_fields(values, self.container)
            self.container['items'] = []
            if cmd == 'sequence':
                self.data.models.sequences.append(self.container)
                return
        if 'command_{}'.format(cmd) in self.schema.model:
            res = PKDict(
                _type=cmd,
                _id=self.parser.next_id(),
                name=label,
            )
            self.__parse_fields(values, res)
            self.sim_data.update_model_defaults(res, LatticeUtil.model_name_for_data(res))
            self.data.models.commands.append(res)
        elif cmd == 'line':
            self.__parse_beamline(label, values)
        elif cmd == 'title':
            if len(values) > 1:
                self.data.models.simulation.name = values[1]
        elif cmd not in self.ignore_commands:
            assert cmd != 'call', '"CALL" statement not supported, combine subfiles into one input file before import'
            if re.search(r'^ptc_', cmd):
                pass
            else:
                pkdlog('unknown cmd: {}', values)

    def __parse_values(self, values):
        if not len(values):
            return
        if len(values) == 1 and '=' in values[0] and not re.search(r'\Wline\s*=\s*\(', values[0].lower()):
            # a variable assignment
            m = re.match(r'.*?([\w.\']+)\s*:?=\s*(.*)$', values[0])
            assert m, 'invalid variable assignment: {}'.format(values)
            name = m.group(1)
            v = m.group(2)
            if name not in self.data.models.rpnVariables:
                self.data.models.rpnVariables[name] = v
            return
        if ':' in values[0]:
            m = re.match(r'([\w.#"]+)\s*:\s*([\w.]+)', values[0])
            assert m, 'label match failed: {}'.format(values[0])
            label, cmd = m.group(1, 2)
            label = self.__remove_quotes(label)
        else:
            label, cmd = None, values[0]
        self.__parse_statement(cmd, label, values)

    def __remove_quotes(self, value):
        return re.sub(r'[\'"](.*)[\'"]', r'\1', value)

    def __split_values(self, item):
        # split items into values by commas
        values = []
        while item and len(item):
            item = item.strip()
            m = re.match(
                r'^\s*((?:[\w.\']+\s*:?=\s*)?(?:(?:".*?")|(?:\'.*?\')|(?:\{.*?\})|(?:\w+\(.*?\))))(?:,(.*))?$',
                item)
            if m:
                values.append(m.group(1))
                assert item != m.group(2)
                item = m.group(2)
                continue
            m = re.match(r'^\s*(.+?)(?:,(.*))?$', item)
            if m:
                values.append(m.group(1).strip())
                assert item != m.group(2)
                item = m.group(2)
                continue
            assert False, 'line parse failed: {}'.format(item)
        return values


class LatticeUtil(object):
    """Utility class for generating lattice elements, beamlines and commands.
    """
    def __init__(self, data, schema):
        self.data = data
        self.schema = schema
        self.id_map, self.max_id = self.__build_id_map(data)

    @classmethod
    def find_first_command(cls, data, command_type):
        for m in data.models.commands:
            if m._type == command_type:
                return m
        return None

    @classmethod
    def has_command(cls, data, command_type):
        for cmd in data.models.commands:
            if cmd._type == command_type:
                return True
        return False


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
            name = el[0].name.upper()
            if quote_name:
                name = '"{}"'.format(name)
            res += '{}: {},'.format(name, self.type_for_data(el[0]))
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

    @classmethod
    def type_for_data(cls, model):
        return model['_type' if cls.is_command(model) else 'type']

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
                #TODO(pjm): some old elegant sims have overlap in element and command ids
                if cmd._id not in res:
                    res[cmd._id] = cmd
        max_id = max(res.keys()) if len(res) else 0
        return res, max_id

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
