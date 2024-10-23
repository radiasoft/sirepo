# -*- coding: utf-8 -*-
"""Lattice utilities.

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
    """Iterate all fields, adding any set to non-default values to the results."""

    IS_DISABLED_FIELD = "isDisabled"

    def __init__(self, filename_map, formatter):
        self.result = []
        self.filename_map = filename_map
        self.formatter = formatter

    def end(self, model):
        self.result.append([model, self.fields])

    def field(self, model, field_schema, field):
        if field == self.IS_DISABLED_FIELD or field == "_super":
            return
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
        from sirepo.template.code_variable import CodeVar

        if len(field_schema) < 3:
            return True
        default_value = field_schema[2]
        value = model[field]
        if value is not None and default_value is not None:
            if value == default_value:
                return True
            if field_schema[1] == "RPNValue":
                if value and not CodeVar.is_var_value(value):
                    return float(value) == default_value
            return str(value) == str(default_value)
        if value is not None:
            return False
        return True


class InputFileIterator(ModelIterator):
    """Iterate and extract all InputFile filenames."""

    def __init__(self, sim_data, update_filenames=True):
        self.result = []
        self.sim_data = sim_data
        self._update_filenames = update_filenames

    def field(self, model, field_schema, field):
        def _beam_input_file():
            self.result.append(
                self.sim_data.lib_file_name_with_model_field(
                    "bunchFile",
                    "sourceFile",
                    model[field],
                ),
            )

        def _input_file():
            self.result.append(
                self.sim_data.lib_file_name_with_model_field(
                    LatticeUtil.model_name_for_data(model), field, model[field]
                )
            )

        t = PKDict({"InputFile": _input_file, "BeamInputFile": _beam_input_file})
        s = field_schema[1]
        f = None
        for k in t:
            if s.startswith(k):
                f = t[k]
                break
        if not model[field] or not f:
            return
        if not self._update_filenames:
            self.result.append(model[field])
        else:
            f()


class LatticeIterator(ElementIterator):
    """Iterate all lattice elements/fields which are not set to the default value."""

    def is_ignore_field(self, field):
        return field in ["name", "type", "_id"] or re.search("(X|Y|File)$", field)


class UpdateIterator(ModelIterator):
    def __init__(self, update_func):
        self.update_func = update_func

    def field(self, model, field_schema, field):
        if field_schema[1] == "RPNValue":
            self.update_func(model, field)


class LatticeParser(object):
    COMMAND_PREFIX = "command_"

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
        lines = lattice_text.replace("\r", "").split("\n")
        self.__parse_lines(lines)
        return self.data

    def _add_variables_for_lattice_references(self):
        # iterate all values, adding "x->y" lattice referenes as variables "x.y"
        from sirepo.template.code_variable import CodeVar

        def _fix_value(value, names):
            value = re.sub(r"\-\>", ".", value)
            expr = CodeVar.infix_to_postfix(value.lower())
            for v in expr.split(" "):
                if CodeVar.is_var_value(v):
                    m = re.match(r"^(.*?)\.(.*)", v)
                    if m:
                        names[v] = [m.group(1), m.group(2)]
            return value

        names = {}
        for v in self.data.models.rpnVariables:
            if CodeVar.is_var_value(v.value):
                v.value = _fix_value(v.value, names)
        for el in self.data.models.elements:
            for f in el:
                v = el[f]
                if CodeVar.is_var_value(v):
                    el[f] = _fix_value(v, names)
        for name in names:
            for el in self.data.models.elements:
                if el.name.lower() == names[name][0]:
                    f = names[name][1]
                    if f in el:
                        self.data.models.rpnVariables.append(
                            PKDict(
                                name=name,
                                value=el[f],
                            )
                        )

    def _code_variables_to_float(self, code_var):
        def _float_update(model, field):
            if not code_var.is_var_value(model[field]) and type(model[field]) != float:
                model[field] = float(model[field])

        for v in self.data.models.rpnVariables:
            if not code_var.is_var_value(v.value):
                v.value = float(v.value)
        LatticeUtil(self.data, self.schema).iterate_models(
            UpdateIterator(_float_update)
        )

    def _compute_drifts(self, code_var):
        drifts = PKDict()
        for el in self.data.models.elements:
            if el.type == "DRIFT":
                length = self._format_length(self._eval_var(code_var, el.l))
                if length not in drifts:
                    drifts[length] = el._id
        return drifts

    def _downcase_variables(self, code_var):
        def _downcase_update(model, field):
            if code_var.is_var_value(model[field]):
                model[field] = model[field].lower()

        for v in self.data.models.rpnVariables:
            v.name = v.name.lower()
            if code_var.is_var_value(v.value):
                v.value = v.value.lower()
        LatticeUtil(self.data, self.schema).iterate_models(
            UpdateIterator(_downcase_update)
        )

    def _eval_var(self, code_var, value):
        return code_var.eval_var_with_assert(value)

    @classmethod
    def _format_command(cls, name):
        return f"{cls.COMMAND_PREFIX}{name}"

    def _format_length(self, length):
        res = "{:.8E}".format(length)
        res = re.sub(r"(\.\d+?)(0+)E", r"\1e", res)
        res = re.sub(r"e\+00$", "", res)
        return res

    def _get_drift(self, drifts, length, allow_negative_drift=False):
        if length == 0:
            return None
        if length < 0 and not allow_negative_drift:
            pkdlog("warning: negative drift: {}", length)
            return None
        length = self._format_length(length)
        if length not in drifts:
            name = "D{}".format(length)
            name = re.sub(r"\+", "", name)
            name = re.sub(r"e?-", "R", name)
            drift = PKDict(
                _id=self.parser.next_id(),
                l=float(length),
                name=name,
                type="DRIFT",
            )
            self.sim_data.update_model_defaults(drift, "DRIFT")
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
        elif self.data.models.beamlines:
            beamline_id = self.data.models.beamlines[-1].id
        self.data.models.simulation.activeBeamlineId = (
            self.data.models.simulation.visualizationBeamlineId
        ) = beamline_id

    def __model_name(self, cmd):
        res = cmd
        while res not in self.schema.model:
            parent = self.elements_by_name[res]
            assert parent and parent.type
            res = parent.type
        return res

    def __parse_beamline(self, label, values):
        assert label
        # remove beamline attributes
        attrs = PKDict()
        items = []
        values[0] = re.sub(r"^.*?=\s*\(\s*", "", values[0])
        for v in values:
            if "=" in v:
                m = re.match(r"^\s*([\w.]+)\s*:?=\s*(.+?)\s*$", v)
                if m:
                    attrs[m.group(1).lower()] = m.group(2)
            else:
                items.append(v)
        items[-1] = re.sub(r"\s*\)$", "", items[-1])
        res = PKDict(
            name=label,
            id=self.parser.next_id(),
            items=[],
        ).pkupdate(attrs)
        self.sim_data.update_model_defaults(res, "beamline")
        for v in items:
            v = self.__remove_quotes(v)
            count = 1
            m = re.match(r"^(\d+)\s*\*\s*\(?([\w.]+)\)?$", v)
            if m:
                count = int(m.group(1))
                v = m.group(2)
            reverse = False
            if v[0] == "-":
                reverse = True
                v = v[1:]
            el = self.elements_by_name.get(v.upper())
            assert el, "line: {}, element not found: {}".format(label, v)
            el_id = el._id if "_id" in el else el.id
            for _ in range(count):
                res["items"].append(-el_id if reverse else el_id)
        assert (
            label.upper() not in self.elements_by_name
        ), "duplicate beamline: {}".format(label)
        self.elements_by_name[label.upper()] = res
        self.data.models.beamlines.append(res)

    def __parse_element(self, cmd, label, values):
        res = self.__parse_fields(
            self.__model_name(cmd),
            values,
            PKDict(
                name=label,
                _id=self.parser.next_id(),
            ),
        )
        res.type = cmd
        if self.container:
            assert "at" in res, 'sequence element missing "at": {}'.format(values)
            at = res.at
            del res["at"]
            # assert label, 'unlabeled element: {}'.format(values)
            if not label:
                label = cmd
            if label.upper() in self.elements_by_name:
                self.container["items"].append(
                    [self.elements_by_name[label.upper()]._id, at]
                )
                return
            if cmd not in self.schema.model:
                parent = self.elements_by_name[cmd]
                assert parent
                assert len(res) >= 3
                # if len(res) == 3:
                #     self.container["items"].append([parent._id, at])
                #     return
            self.container["items"].append([res._id, at])
        assert "at" not in res
        # copy in superclass values
        while cmd not in self.schema.model:
            parent = self.elements_by_name[cmd]
            assert parent and parent.type
            res = PKDict(list(parent.items()) + list(res.items()))
            res.type = parent.type
            cmd = parent.type
        self.sim_data.update_model_defaults(res, res.type)
        if not label:
            label = values[0].upper()
            assert (
                label in self.elements_by_name
            ), "no element for label: {}: {}".format(label, values)
            self.elements_by_name[label].update(res)
        else:
            # assert label.upper() not in self.elements_by_name, \
            #     'duplicate element labeled: {}'.format(label)
            self.elements_by_name[label.upper()] = res
        self.data.models.elements.append(res)

    def __parse_fields(self, cmd, values, res):
        model_schema = self.schema.model.get(cmd)
        prev_field = None
        for value in values[1:]:
            m = re.match(r"^\s*([\w.]+)\s*:?=\s*(.+?)\s*$", value)
            if m:
                f, v = m.group(1, 2)
                f = f.lower()
                # allow native fields named "type" which conflicts element sirepo element type
                if f == "type" and model_schema and f not in model_schema:
                    f = f"{cmd.lower()}_type"
                # skip non-schema fields, with the exception of positional fields "at" and "elemedge"
                if (
                    model_schema
                    and f not in model_schema
                    and f not in ("at", "elemedge", "z")
                ):
                    continue
                if f != "name":
                    # some commands may have a "name" field
                    assert f not in res, "field already defined: {}, values: {}".format(
                        f, values
                    )
                res[f] = self.__remove_quotes(v)
                prev_field = f
                continue
            # no assignment, maybe a boolean value
            m = re.match(r"^\s*(!|-)?\s*([\w.]+)\s*$", value)
            assert m, "failed to parse field assignment: {}".format(value)
            v, f = m.group(1, 2)
            if model_schema and f not in model_schema:
                # special case for "column" field, may contain multiple comma separated values
                if prev_field == "column":
                    res[prev_field] += f", {f}"
                continue
            res[f.lower()] = "0" if v else "1"
        return res

    def __parse_lines(self, lines):
        prev_line = ""
        in_comment = False
        for line in lines:
            self.parser.increment_line_number()
            line = re.sub(r"\&\s*$", "", line)
            # strip comments
            line = line.strip()
            line = re.sub(r"(.*?)(!|//).*$", r"\1", line)
            line = re.sub(r"\/\*.*?\*\/", "", line)
            # special case, some commands often missing a comma
            line = re.sub(
                r"^\s*(title|exec|call)\s+([^,])", r"\1, \2", line, flags=re.IGNORECASE
            )
            if in_comment and re.search(r"^.*\*\/", line):
                line = re.sub(r"^.*\*\/", "", line)
                in_comment = False
            if re.search(r"\/\*.*$", line):
                line = re.sub(r"\/\*.*$", "", line)
                in_comment = True
            if not line or in_comment:
                continue
            assert not re.search(
                r"^\s*(if|while)\s*\(", line, re.IGNORECASE
            ), "Remove conditional if() or while() statements from input file before import"
            while ";" in line:
                m = re.match(r"^(.*?);(.*)$", line)
                assert m, "parse ; failed: {}".format(line)
                item = (prev_line + " " + m.group(1)).strip()
                self.__parse_values(self.__split_values(item))
                line = m.group(2)
                prev_line = ""
            prev_line += line
        self.data.models["rpnVariables"] = [
            PKDict(name=k, value=v) for k, v in self.data.models.rpnVariables.items()
        ]

    def __parse_statement(self, cmd, label, values):
        if cmd.upper() in self.schema.model or cmd.upper() in self.elements_by_name:
            self.__parse_element(cmd.upper(), label, values)
            return
        cmd = cmd.lower()
        if self.container and cmd == "end{}".format(self.container.type):
            assert len(values) == 1, "invalid end{}: {}".format(self.container, values)
            self.container = None
            return
        if cmd in ("sequence", "track"):
            self.container = PKDict(
                name=label,
                type=cmd,
                _id=self.parser.next_id(),
            )
            self.__parse_fields(self._format_command(cmd), values, self.container)
            self.container["items"] = []
            if cmd == "sequence":
                self.data.models.sequences.append(self.container)
                return
        if self._format_command(cmd) in self.schema.model:
            res = PKDict(
                _type=cmd,
                _id=self.parser.next_id(),
                name=label,
            )
            self.__parse_fields(self._format_command(cmd), values, res)
            self.sim_data.update_model_defaults(
                res, LatticeUtil.model_name_for_data(res)
            )
            self.data.models.commands.append(res)
        elif cmd == "line":
            self.__parse_beamline(label, values)
        elif cmd == "title":
            if len(values) > 1:
                self.data.models.simulation.name = self.__remove_quotes(values[1])
        elif cmd not in self.ignore_commands:
            assert (
                cmd != "call"
            ), '"CALL" statement not supported, combine subfiles into one input file before import'
            if re.search(r"^ptc_", cmd):
                pass
            else:
                pkdlog("unknown cmd: {}", values)

    def __parse_values(self, values):
        if not values:
            return
        if (
            (re.search(r"^\s*REAL\s", values[0], re.IGNORECASE) or len(values) == 1)
            and "=" in values[0]
            and not re.search(r"\Wline\s*\:?=\s*\(", values[0].lower())
        ):
            if re.search(R"^\s*(BOOL|STRING)\s", values[0], re.IGNORECASE):
                return
            # a variable assignment
            val = ", ".join(values)
            m = re.match(r".*?([\w.\'\-]+)\s*:?=\s*(.*)$", val)
            assert m, "invalid variable assignment: {}".format(val)
            name = m.group(1)
            v = m.group(2)
            if name not in self.data.models.rpnVariables:
                self.data.models.rpnVariables[name] = v
            return
        if ":" in values[0]:
            m = re.match(r'(".*?")\s*:\s*(".*?")', values[0])
            if not m:
                m = re.match(r'(".*?")\s*:\s*(\w+)', values[0])
                if not m:
                    m = re.match(r'([\w.#"\-\/]+)\s*:\s*([\w."]+)', values[0])
            assert m, "label match failed: {}".format(values[0])
            label, cmd = m.group(1, 2)
            label = self.__remove_quotes(label)
            cmd = self.__remove_quotes(cmd)
        else:
            label, cmd = None, values[0]
        self.__parse_statement(cmd, label, values)

    def __remove_quotes(self, value):
        return re.sub(r'[\'"](.*)[\'"]', r"\1", value)

    def __split_values(self, item):
        # split items into values by commas
        values = []
        while item:
            item = item.strip()
            m = re.match(r'^(".*?"\s*:\s*\w+)\s*,(.*)$', item)
            if m:
                values.append(m.group(1))
                item = m.group(2)
                continue
            m = re.match(
                r'^\s*((?:[\w.\']+\s*:?=\s*)(?:(?:".*?")|(?:\'.*?\')|(?:\{.*?\})|(?:\w+\(.*?\).*?)))(?:,(.*))?$',
                item,
            )
            if m:
                values.append(m.group(1))
                assert item != m.group(2)
                item = m.group(2)
                continue
            m = re.match(r"^\s*(.+?)(?:,(.*))?$", item)
            if m:
                values.append(m.group(1).strip())
                assert item != m.group(2)
                item = m.group(2)
                continue
            assert False, "line parse failed: {}".format(item)
        # try to fix up mismatched parenthesis
        res = []
        for idx in range(len(values)):
            v = values[idx]
            if len(res):
                prev = res[-1]
                mismatch_count = prev.count("(") - prev.count(")")
                if mismatch_count and not re.search(r"\bline\b", prev, re.IGNORECASE):
                    if mismatch_count == v.count(")") - v.count("("):
                        res[-1] += f", {v}"
                        continue
            res.append(v)
        return res


class LatticeUtil(object):
    _OUTPUT_NAME_PREFIX = "elementAnimation"
    _FILE_ID_SEP = "-"

    """Utility class for generating lattice elements, beamlines and commands.
    """

    def __init__(self, data, schema):
        self.data = data
        self.schema = schema
        self.id_map, self.max_id = self.__build_id_map(data)

    def explode_beamline(self, beamline_id):
        res = []
        for bid in self.get_item(beamline_id)["items"]:
            e = self.get_item(abs(bid))
            if self.is_beamline(e):
                r = self.explode_beamline(e.id)
                if bid < 0:
                    r.reverse()
                res += r
            else:
                res.append(bid)
        return res

    @classmethod
    def find_first_command(cls, data, command_type):
        for m in data.models.commands:
            if m._type == command_type:
                return m
        return None

    @classmethod
    def file_id(cls, model_id, field_index):
        return f"{model_id}{LatticeUtil._FILE_ID_SEP}{field_index}"

    @classmethod
    def file_id_from_output_model_name(cls, name):
        return re.sub(cls._OUTPUT_NAME_PREFIX, "", name)

    @classmethod
    def fixup_output_files(cls, data, schema, output_file_iterator):
        # if new model fields are added to the schema,
        # the output file id may be invalid, fixup original by filename
        v = LatticeUtil(data, schema).iterate_models(output_file_iterator).result
        remove_list = []
        add_list = {}
        for m in data.models:
            if not cls.__is_output_model_name(m):
                continue
            if cls.file_id_from_output_model_name(m) in v:
                continue
            file_id = None
            if "xFile" in data.models[m]:
                for k in v:
                    if v[k] == data.models[m].xFile:
                        file_id = k
                        break
            if file_id:
                name = cls.output_model_name(file_id)
                if name not in data.models:
                    add_list[name] = data.models[m]
                    data.models[m].xFileId = file_id
            remove_list.append(m)
        for m in remove_list:
            del data.models[m]
        for m in add_list:
            data.models[m] = add_list[m]

    def get_item(self, item_id):
        return self.id_map[item_id]

    @classmethod
    def get_lattice_id_from_file_id(cls, data, file_id):
        for c in data.models.commands:
            if (
                c._id == int(file_id.split(LatticeUtil._FILE_ID_SEP)[0])
                and "use_beamline" in c
            ):
                return c.use_beamline
        return None

    @classmethod
    def has_command(cls, data, command_type):
        for cmd in data.models.commands:
            if cmd._type == command_type:
                return True
        return False

    @classmethod
    def is_beamline(cls, model):
        """Is the model a beamline?"""
        return "_id" not in model and "type" not in model

    @classmethod
    def is_command(cls, model):
        """Is the model a command or a lattice element?"""
        return "_type" in model

    def iterate_models(self, iterator, name=None):
        """Iterate the models in the named container.
        By default the commands and elements containers are iterated.
        """
        iterator.id_map = self.id_map
        names = (name,) if name else ("commands", "elements")
        for name in names:
            for m in self.data.models[name]:
                model_schema = self.schema.model[self.model_name_for_data(m)]
                iterator.start(m)
                for k in sorted(m):
                    if k in model_schema:
                        iterator.field(m, model_schema[k], k)
                iterator.end(m)
        return iterator

    @classmethod
    def max_id(cls, data):
        max_id = 1
        for model_type in "elements", "beamlines", "commands":
            if model_type not in data.models:
                continue
            for m in data.models[model_type]:
                assert "_id" in m or "id" in m, "Missing id: {}".format(m)
                i = m._id if "_id" in m else m.id
                if i > max_id:
                    max_id = i
        return max_id

    @classmethod
    def model_name_for_data(cls, model):
        """Returns the model's schema name."""
        return (
            LatticeParser._format_command(model._type)
            if cls.is_command(model)
            else model.type
        )

    @classmethod
    def output_model_name(cls, file_id):
        return "{}{}".format(cls._OUTPUT_NAME_PREFIX, file_id)

    def render_lattice(
        self,
        fields,
        quote_name=False,
        want_semicolon=False,
        want_name=True,
        want_var_assign=False,
        madx_name=False,
        comment="//",
    ):
        """Render lattice elements."""
        from sirepo.template.code_variable import CodeVar

        res = ""
        for el in fields:
            # el is [model, [[f, v], [f, v]...]]
            el_type = self.type_for_data(el[0])
            if (
                ElementIterator.IS_DISABLED_FIELD in el[0]
                and el[0][ElementIterator.IS_DISABLED_FIELD] == "1"
            ):
                res += comment + " "
            if want_name:
                name = self.__format_name(el[0].name, quote_name, madx_name)
                res += "{}: {},".format(name, el_type)
            else:
                res += "{},".format(el_type)
            for f in el[1]:
                var_assign = ""
                if want_var_assign:
                    s = self.schema.model[el_type]
                    if (
                        f[0] in s
                        and s[f[0]][1] == "RPNValue"
                        and CodeVar.is_var_value(f[1])
                    ):
                        var_assign = ":"
                res += "{}{}={},".format(f[0], var_assign, f[1])
            res = res[:-1]
            if want_semicolon:
                res += ";"
            res += "\n"
        return res

    def render_lattice_and_beamline(self, iterator, **kwargs):
        return self.render_lattice(
            self.iterate_models(iterator, "elements").result, **kwargs
        ) + self.__render_beamline(**kwargs)

    def select_beamline(self):
        """Returns the beamline to use based for the selected report."""
        sim = self.data.models.simulation
        if self.data.get("report", "") == "twissReport":
            beamline_id = sim.activeBeamlineId
        else:
            if "visualizationBeamlineId" not in sim or not sim.visualizationBeamlineId:
                sim.visualizationBeamlineId = self.data.models.beamlines[0].id
            beamline_id = sim.visualizationBeamlineId
        return self.get_item(int(beamline_id))

    def sort_elements_and_beamlines(self):
        """Sort elements and beamline models in place, by (type, name) and (name)"""
        m = self.data.models
        m.elements = sorted(m.elements, key=lambda e: (e.type, e.name.lower()))
        m.beamlines = sorted(m.beamlines, key=lambda e: e.name.lower())

    @classmethod
    def type_for_data(cls, model):
        return model["_type" if cls.is_command(model) else "type"]

    def __add_beamlines(self, beamline, beamlines, ordered_beamlines):
        if beamline in ordered_beamlines:
            return
        for bid in beamline["items"]:
            bid = abs(bid)
            if bid in beamlines and "type" not in beamlines[bid]:
                self.__add_beamlines(beamlines[bid], beamlines, ordered_beamlines)
        ordered_beamlines.append(beamline)

    def __build_id_map(self, data):
        """Returns a map of beamlines and elements, (id => model)."""
        res = {}
        for bl in data.models.beamlines:
            res[bl.id] = bl
        for el in data.models.elements:
            res[el._id] = el
        if "commands" in data.models:
            for cmd in data.models.commands:
                # TODO(pjm): some old elegant sims have overlap in element and command ids
                if cmd._id not in res:
                    res[cmd._id] = cmd
        max_id = max(res.keys()) if res else 0
        return res, max_id

    def __format_name(self, name, quote_name, madx_name, is_reversed=False):
        name = name.upper()
        if madx_name:
            name = re.sub(r"[\-:/]", "_", name)
        if is_reversed:
            name = f"-{name}"
        if quote_name:
            name = '"{}"'.format(name)
        return name

    @classmethod
    def __is_output_model_name(cls, name):
        return cls._OUTPUT_NAME_PREFIX in name

    def __render_beamline(
        self,
        quote_name=False,
        want_semicolon=False,
        want_var_assign=False,
        madx_name=False,
    ):
        """Render the beamlines list in precedence order."""
        ordered_beamlines = []
        for bid in sorted(self.id_map):
            model = self.id_map[bid]
            if "type" not in model and not self.is_command(model):
                self.__add_beamlines(model, self.id_map, ordered_beamlines)
        res = ""
        for bl in ordered_beamlines:
            if bl["items"]:
                name = self.__format_name(bl.name, quote_name, madx_name)
                res += "{}: LINE=(".format(name)
                for bid in bl["items"]:
                    res += "{},".format(
                        self.__format_name(
                            self.id_map[abs(bid)].name,
                            quote_name,
                            madx_name,
                            is_reversed=bid < 0,
                        )
                    )
                res = res[:-1]
                res += ")"
                if want_semicolon:
                    res += ";"
                res += "\n"
        return res
