# -*- coding: utf-8 -*-
"""Flash Config parser.

:copyright: Copyright (c) 2021 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp, pkdlog
from sirepo.template import template_common
from sirepo.template import flash_views
import os.path
import re


class ConfigParser:
    # D <name> <comment> or D & <comment>
    # DATAFILES <wildcard>
    # LINKIF <filename> <unitename>
    # MASS_SCALAR <name> (EOSMAP: <eosrole> | (EOSMAPIN: <eosrole>)? (EOSMAPOUT: <eosrole>)?)?
    # PARAMETER <name> <type> CONSTANT? <default> <range spec>?
    # PARTICLEMAP TO <partname> FROM <vartype> <varname>
    # PARTICLEPROP <name> <type>
    # PARTICLETYPE <particletype> INITMETHOD <initmethod> MAPMETHOD <mapmethod> ADVMETHOD <advmethod>
    # PPDEFINE <sym> <val>?
    # REQUESTS <unit>
    # REQUIRES <unit>
    # SCRATCHCENTERVAR <name>
    # SPECIES <name> (TO <number of ions>)?
    # USESETUPVARS <var>
    # VARIABLE <name> (TYPE: <vartype)
    # (IF, ELSEIF, ELSE, ENDIF)

    def parse(self, config_text):
        idx = 1
        self.stack = [PKDict(statements=[])]
        for line in config_text.split("\n"):
            line = re.sub(r"#.*$", "", line)
            line = re.sub(r"(TYPE:)(\S)", r"\1 \2", line)
            p = line.split()
            if not p:
                continue
            method = f"_parse_{p[0].lower()}"
            if not hasattr(self, method):
                pkdlog("skipping line={}", line)
                continue
            m = PKDict(
                _id=idx,
                _type=p[0],
            )
            idx += 1
            item = getattr(self, method)(p, m)
            if item:
                self.stack[-1].statements.append(item)
        assert len(self.stack) == 1, "improper IF/ENDIF nesting"
        return self.__move_descriptions_to_parameters(self.stack[0])

    def _parse_d(self, parts, model):
        if parts[1] == "&":
            prev = self.stack[-1].statements[-1]
            assert prev._type == "D", "expected multiline description for D &"
            prev.comment += " {}".format(" ".join(parts[2:]))
            return None
        return model.pkupdate(
            name=parts[1],
            comment=" ".join(parts[2:]),
        )

    def _parse_datafiles(self, parts, model):
        return model.pkupdate(
            wildcard=parts[1],
        )

    def _parse_else(self, parts, model):
        self.stack.pop()
        self.__new_stack(model)
        return None

    def _parse_elseif(self, parts, model):
        self.stack.pop()
        return self._parse_if(parts, model)

    def _parse_endif(self, parts, model):
        self.stack.pop()
        return model

    def _parse_if(self, parts, model):
        self.__new_stack(model, parts[1])
        return None

    def _parse_linkif(self, parts, model):
        return model.pkupdate(
            filename=parts[1],
            unitname=parts[2],
        )

    def _parse_mass_scalar(self, parts, model):
        for i in range(2, len(parts), 2):
            n = parts[i]
            m = re.search(r"^(EOSMAP(IN|OUT)?):$", n)
            assert m, f"unknown MASS_SCALAR arg: {n}"
            model[m.group(1).lower()] = parts[i + 1]
        return model.pkupdate(
            name=parts[1],
        )

    def _parse_parameter(self, parts, model):
        assert re.search(
            r"^(REAL|INTEGER|STRING|BOOLEAN)$", parts[2]
        ), f"invalid Config type: {parts[2]}"
        if parts[3] == "CONSTANT":
            del parts[3]
            model.isConstant = "1"
        else:
            model.isConstant = "0"
        model.range = ""
        if len(parts) > 4:
            model.range = re.sub(r"\[|\]", "", " ".join(parts[4:]))
        return model.pkupdate(
            name=parts[1],
            type=parts[2],
            default=re.sub(r'"', "", parts[3]),
        )

    def _parse_particlemap(self, parts, model):
        assert (
            parts[1] == "TO" and parts[3] == "FROM"
        ), f'invalid PARTICLEMAP def: {" ".join(parts)}'
        return model.pkupdate(
            partname=parts[2],
            pvartype=parts[4],
            varname=parts[5],
        )

    def _parse_particleprop(self, parts, model):
        return model.pkupdate(
            name=parts[1],
            type=parts[2],
        )

    def _parse_particletype(self, parts, model):
        assert (
            parts[2] == "INITMETHOD" and parts[4] == "MAPMETHOD"
        ), f'invalid PARTICLETYPE def: {" ".join(parts)}'
        return model.pkupdate(
            particletype=parts[1],
            initmethod=parts[3],
            mapmethod=parts[5],
            advmethod=parts[7] if len(parts) > 6 and parts[6] == "ADVMETHOD" else "",
        )

    def _parse_ppdefine(self, parts, model):
        return model.pkupdate(
            sym=parts[1],
            val=" ".join(parts[2:]) if len(parts) > 2 else "",
        )

    def _parse_requires(self, parts, model):
        return model.pkupdate(
            unit=parts[1],
        )

    def _parse_requests(self, parts, model):
        return model.pkupdate(
            unit=parts[1],
        )

    def _parse_scratchcentervar(self, parts, model):
        return model.pkupdate(
            name=parts[1],
        )

    def _parse_species(self, parts, model):
        if len(parts) > 2:
            assert parts[2] == "TO", f'invalid SPECIES: {" ".join(parts)}'
            model.numberOfIons = parts[3]
        return model.pkupdate(
            name=parts[1],
        )

    def _parse_usesetupvars(self, parts, model):
        return model.pkupdate(vars=" ".join(parts[1:]))

    def _parse_variable(self, parts, model):
        model.vartype = ""
        if len(parts) > 2:
            assert parts[2] == "TYPE:", f'invalid VARIABLE line: {" ".join(parts)}'
            model.vartype = parts[3]
        return model.pkupdate(
            name=parts[1],
        )

    def __move_descriptions_to_parameters(self, item):
        def _find_all(item, search_type, do_remove=False, res=None):
            if res is None:
                res = PKDict()
            if "_type" in item and item._type == search_type:
                res[item.name] = item
            if "statements" in item:
                for stmt in item.statements:
                    _find_all(stmt, search_type, do_remove, res)
                if do_remove:
                    item.statements = list(
                        filter(lambda x: x._type != search_type, item.statements)
                    )
            return res

        descriptions = _find_all(item, "D", do_remove=True)
        parameters = _find_all(item, "PARAMETER")
        for name in descriptions:
            if name in parameters:
                parameters[name].comment = descriptions[name].comment
        return item.statements

    def __new_stack(self, model, condition=None):
        self.stack[-1].statements.append(
            model.pkupdate(
                statements=[],
            )
        )
        if condition:
            model.condition = condition
        self.stack.append(model)


class ParameterParser:
    def parse(self, sim_in, par_text):
        self.schema = sim_in.models.flashSchema
        self.field_map = self.__field_to_model_map()
        return self.__parse_values(self.__parse_text(par_text))

    def __field_to_model_map(self):
        res = PKDict()
        for m in self.schema.model:
            for f in self.schema.model[m]:
                res[f.lower()] = [m, f]
        return res

    def __parse_text(self, par_text):
        res = PKDict()
        for line in par_text.split("\n"):
            line = re.sub(r"#.*$", "", line)
            m = re.search(r"^(\w.*?)\s*=\s*(.*?)\s*$", line)
            if m:
                f, v = m.group(1, 2)
                res[f.lower()] = v
        return res

    def __parse_values(self, fields):
        enum_map = PKDict()
        for e, items in self.schema.enum.items():
            enum_map[e] = PKDict({v[0].lower(): v[0] for v in items})
        res = PKDict()
        for f, v in fields.items():
            if f not in self.field_map:
                pkdlog(f"Unknown field: {f}: {v}")
                continue
            m, fn = self.field_map[f]
            ftype = self.schema.model[m][fn][1]
            if ftype in self.schema.enum:
                v = re.sub(r'"', "", v).strip()
                assert (
                    v.lower() in enum_map[ftype]
                ), f"Unknown enum value for field: {ftype}: {v} values: {enum_map[ftype].keys()}"
                res[fn] = enum_map[ftype][v.lower()]
            elif ftype == "Boolean":
                v = SetupParameterParser.remove_quotes(v)
                m = re.search(r"^\.(true|false)\.$", v, re.IGNORECASE)
                assert m, f"invalid boolean for field {f}: {v}"
                res[fn] = "1" if m.group(1).lower() == "true" else "0"
            else:
                res[fn] = SetupParameterParser.parse_string_or_number(
                    ftype, fields[f], maybe_quoted=True
                )
        return res


class SetupParameterParser:
    _HUGE = PKDict(
        Integer=2147483647,
        Float=3.40282347e38,
    )
    _MAX_VAR_COUNT = 20
    _SPECIAL_TYPES = PKDict(
        Grid_GridMain=PKDict(
            {
                k: "GridBoundaryType"
                for k in (
                    "xl_boundary_type",
                    "xr_boundary_type",
                    "yl_boundary_type",
                    "yr_boundary_type",
                    "zl_boundary_type",
                    "zr_boundary_type",
                )
            }
        ),
        Grid_GridMain_paramesh=PKDict(
            {
                f"refine_var_{v}": "VariableNameOptional"
                for v in range(1, _MAX_VAR_COUNT)
            }
        ),
        IO_IOMain=PKDict(
            {f"plot_var_{v}": "VariableNameOptional" for v in range(1, _MAX_VAR_COUNT)}
        ),
        physics_Diffuse_DiffuseMain=PKDict(
            {
                k: "DiffuseBoundaryType"
                for k in (
                    "diff_eleXlBoundaryType",
                    "diff_eleXrBoundaryType",
                    "diff_eleYlBoundaryType",
                    "diff_eleYrBoundaryType",
                    "diff_eleZlBoundaryType",
                    "diff_eleZrBoundaryType",
                )
            }
        ),
        physics_Gravity=PKDict(
            grav_boundary_type="GravityBoundaryType",
        ),
        physics_Gravity_GravityMain_Constant=PKDict(
            gdirec="GravityDirection",
        ),
        physics_Hydro_HydroMain_unsplit=PKDict(RiemannSolver="RiemannSolver"),
        physics_RadTrans_RadTransMain_MGD=PKDict(
            {
                k: "RadTransMGDBoundaryType"
                for k in (
                    "rt_mgdXlBoundaryType",
                    "rt_mgdXrBoundaryType",
                    "rt_mgdYlBoundaryType",
                    "rt_mgdYrBoundaryType",
                    "rt_mgdZlBoundaryType",
                    "rt_mgdZrBoundaryType",
                )
            }
        ),
        physics_sourceTerms_EnergyDeposition_EnergyDepositionMain_Laser=PKDict(
            {
                f"ed_crossSectionFunctionType_{v}": "LaserCrossSectionOptional"
                for v in range(1, _MAX_VAR_COUNT)
            }
        ),
    )
    _TINY = PKDict(
        Float=1.17549435e-38,
    )
    _TYPE_MAP = PKDict(
        BOOLEAN="Boolean",
        INTEGER="Integer",
        REAL="Float",
        STRING="String",
    )

    def __add_enum(self, enums, name, values):
        enums[name] = [[v, v] for v in values]

    def __init__(self, setup_dir):
        self.setup_dir = setup_dir

    def generate_schema(self):
        with pkio.open_text(self.setup_dir.join("setup_vars")) as f:
            self.var_names = self.__parse_vars(f)
        with pkio.open_text(self.setup_dir.join("setup_params")) as f:
            self.models, self.views = self.__parse_setup(f)
        with pkio.open_text(self.setup_dir.join("setup_datafiles")) as f:
            self.datafiles = self.__parse_datafiles(f)
        return self.__format_schema()

    @classmethod
    def model_name_from_flash_unit_name(cls, text):
        # TODO(e-carlin): discuss with pjm. Main units have different vars than the non-main
        # return '_'.join(filter(lambda x: not re.search(r'Main$', x), text.split('/')))
        return "_".join(text.split("/"))

    @classmethod
    def parse_string_or_number(cls, field_type, value, maybe_quoted=False):
        if field_type == "String" or field_type == "OptionalString":
            return cls.__parse_string(value)
        if maybe_quoted:
            value = cls.remove_quotes(value)
        if re.search(r"^(-)?(HUGE|TINY)", value):
            return cls.__parse_special_number(field_type, value)
        if field_type == "Integer":
            assert re.search(
                r"^([\-|+])?\d+$", str(value)
            ), f"{field.name} invalid flash integer: {value}"
            return int(value)
        if field_type == "Float":
            value = re.sub(r"\+$", "", value)
            assert template_common.NUMERIC_RE.search(
                value
            ), f"invalid flash float: {value}"
            return float(value)
        if field_type == "Constant":
            return value
        assert False, f"unknown field type: {field_type}, value: {value}"

    @classmethod
    def remove_quotes(cls, value):
        # any value may be quoted
        return re.sub(r'^"(.*)"$', r"\1", value)

    def __create_views(self, schema):
        schema.view = self.views
        for m in schema.model:
            schema.view[m].pkupdate(
                fieldsPerTab=8,
                advanced=[v for v in schema.model[m].keys()],
                basic=[],
            )

    def __field_default(self, field):
        if field.is_constant:
            assert field.default, f"missing constant value: {field.name}"
            return field.default
        return self.__value_for_type(field, field.default)

    def __field_type(self, field, model_name, enums):
        assert field.type in self._TYPE_MAP, f"unknown field type: {field.type}"
        field.type = self._TYPE_MAP[field.type]
        if field.is_constant:
            field.type = "Constant"
            return
        if self.__is_file_field(field):
            field.type = "SetupDatafilesOptional"
            if field.default == '"-none-"' or field.default == '"NOT SPECIFIED"':
                field.default = "none"
            field.enum = [v[0] for v in enums[field.type]]
            return
        if model_name in self._SPECIAL_TYPES:
            if field.name in self._SPECIAL_TYPES[model_name]:
                ftype = self._SPECIAL_TYPES[model_name][field.name]
                field.type = ftype
                field.enum = [v[0] for v in enums[ftype]]
                return
        if "valid_values" in field:
            self.__valid_values(field)
        if "enum" in field:
            enum_name = f"{model_name}{field.name}"
            assert enum_name not in enums, f"duplicate enum: {enum_name}"
            self.__add_enum(enums, enum_name, field.enum)
            field.type = enum_name
        elif field.type == "String" and field.default == '""':
            field.type = "OptionalString"

    def __format_schema(self):
        res = self.__init_schema()
        for name in sorted(self.models.keys()):
            m = self.models[name]
            fields = PKDict()
            for fname in sorted(m):
                field = m[fname]
                # [label, type, default, description, min, max]
                self.__field_type(field, name, res.enum)
                fields[fname] = [fname, field.type, self.__field_default(field)]
                if field.description:
                    fields[fname].append(field.description)
                if "min" in field:
                    if not field.description:
                        fields[fname].append("")
                    if field.min is None:
                        fields[fname].append(None)
                    else:
                        fields[fname].append(self.__value_for_type(field, field.min))
                    if "max" in field:
                        fields[fname].append(self.__value_for_type(field, field.max))
            res.model[name] = fields
        self.__create_views(res)
        return flash_views.SpecializedViews().update_schema(res)

    def __init_schema(self):
        enums = PKDict()
        for name, values in PKDict(
            DiffuseBoundaryType=["dirichlet", "neumann", "outflow", "zero-gradient"],
            GridBoundaryType=[
                "nocurrent",
                "reflect",
                "axisymmetric",
                "eqtsymmetric",
                "outflow",
                "diode",
                "extrapolate",
                "neumann_ins",
                "dirichlet",
                "hydrostatic-f2+nvout",
                "hydrostatic-f2+nvdiode",
                "hydrostatic-f2+nvrefl",
                "hydrostatic+nvout",
                "hydrostatic+nvdiode",
                "hydrostatic+nvrefl",
                "periodic",
                "user",
            ],
            GravityBoundaryType=["dirichlet", "isolated", "periodic"],
            GravityDirection=["x", "y", "z"],
            LaserCrossSectionOptional=["none", "gaussian1D", "gaussian2D", "uniform"],
            RadTransMGDBoundaryType=[
                "dirichlet",
                "neumann",
                "outflow",
                "outstream",
                "reflecting",
                "vacuum",
            ],
            RiemannSolver=[
                "Roe",
                "HLL",
                "HLLC",
                "Marquina",
                "MarquinaModified",
                "Hybrid",
                "HLLD",
            ],
            SetupDatafiles=self.datafiles,
            SetupDatafilesOptional=["none", *sorted(self.datafiles)],
            VariableName=sorted(self.var_names),
            VariableNameOptional=["none", *sorted(self.var_names)],
        ).items():
            self.__add_enum(enums, name, values)
        return PKDict(
            enum=enums,
            model=PKDict(),
        )

    def __is_file_field(self, field):
        # TODO(pjm): there may be other cases of datafile selection
        return re.search(r"^eos_.*?TableFile$", field.name) or re.search(
            r"^op_.*?FileName$", field.name
        )

    def __parse_datafiles(self, in_stream):
        res = []
        for line in in_stream:
            line = line.strip()
            if line:
                res.append(os.path.basename(line))
        return res

    def __parse_description(self, text, field):
        if not field.description:
            m = re.search(r"^Valid Values:\s+(.*)", text)
            if m:
                assert "valid_values" not in field, f"duplicate valid value def: {text}"
                field.valid_values = m.group(1)
                return

            if re.search(r'^"', text) or (
                field.get("valid_values") and field.valid_values.count('"') % 2 == 1
            ):
                assert (
                    "valid_values" in field
                ), f"expected previous valid values def: {text}"
                field.valid_values += " " + text
                return
        field.description += (" " if field.description else "") + text

    def __parse_field(self, text, model):
        # [BOOLEAN] CONSTANT [FALSE]
        # [STRING] ["FLASH 3 run"]
        # [INTEGER] [2]
        # [REAL] [1.0]
        assert model is not None
        m = re.search(r"^(.*?)\s\[(.*?)\]\s(CONSTANT)?\s*\[(.*?)\](.*)", text)
        assert m, f"unparsable field: {text}"
        name = m.group(1)
        assert name not in model, f"duplicate field: {name}"
        ftype = m.group(2)
        is_constant = m.group(3) == "CONSTANT"
        fdefault = m.group(4)
        assert not m.group(5), f"extra values in field def: {line}"
        model[name] = PKDict(
            name=name,
            type=ftype,
            is_constant=is_constant,
            default=fdefault,
            description="",
        )
        return model[name]

    def __parse_model(self, text, models, views):
        name = self.model_name_from_flash_unit_name(text)
        if name not in models:
            models[name] = PKDict()
            views[name] = PKDict(
                title=text,
            )
        return models[name]

    def __parse_setup(self, in_stream):
        models = PKDict()
        views = PKDict()
        model = None
        field = None
        for line in in_stream:
            if line == "\n":
                continue
            m = re.search(r"(^\w.*)", line)
            if m:
                model = self.__parse_model(m.group(1), models, views)
                continue
            m = re.search(r"^\s{4}(\w.*)", line)
            if m:
                if m.group(1) != "__doc__":
                    field = self.__parse_field(m.group(1), model)
                continue
            m = re.search(r"^\s{8}(\S.*)", line)
            if m:
                self.__parse_description(m.group(1), field)
                continue
            assert False, f'unhandled line: "{line}"'
        return models, views

    @classmethod
    def __parse_special_number(cls, field_type, value):
        res = (
            cls._HUGE[field_type]
            if re.search(r".*?HUGE", value)
            else cls._TINY[field_type]
        )
        if re.search(r"^-", value):
            return -res
        return res

    @classmethod
    def __parse_string(cls, value):
        assert re.search(r'^".*"$', value), f"invalid string: {value}"
        return cls.remove_quotes(value)

    def __parse_vars(self, in_stream):
        res = set()
        state = "name"
        for line in in_stream:
            if line == "\n":
                if state == "newline":
                    state = "name"
                continue
            if state == "name":
                m = re.search(r"^Name: (.*)\s*$", line)
                assert m, f"expected var name: {line}"
                res.add(m.group(1))
                state = "newline"
        return res

    def __valid_values(self, field):
        vv = field.valid_values
        if vv == "Unconstrained":
            return
        m = re.search(r"^([\-0-9\.]+) to ([\-0-9\.]+)$", vv)
        if m:
            field.min = m.group(1)
            field.max = m.group(2)
            return
        if re.search(r"^([\-0-9]+,\s*)+[\-0-9]+$", vv):
            # integer pick list
            field.enum = re.split(r",\s*", vv)
            return
        if re.search(r'^(".*?",\s*)*".*?"+$', vv):
            # string pick list
            field.enum = [self.__parse_string(v) for v in re.split(r",\s*", vv)]
            return
        m = re.search(r"^(\S+) to INFTY$", vv)
        if m:
            field.min = m.group(1)
            return
        m = re.search(r"^-INFTY to (\S+)$", vv)
        if m:
            field.min = None
            field.max = m.group(1)
            return
        m = re.search(r"\sto\s([\-0-9]+)$", vv)
        if m:
            field.min = None
            field.max = m.group(1)
            field.description = f"Valid Values: {field.description}"
            return
        if re.search(r"\sto\sINFTY$", vv) or re.search(
            r"^([\-0-9.]+,\s*)+[\-0-9.]+$", vv
        ):
            # restore valid value info to description
            field.description = f"Valid Values: {field.description}"
            return
        assert False, f"unhandled Valid Values for {field.name}: {vv}"

    def __value_for_type(self, field, value):
        if "enum" in field:
            if re.search(r'"', value):
                value = self.__parse_string(value)
            if field.type.endswith("Optional"):
                if not value or value == " ":
                    value = field.enum[0]
            assert value in field.enum, f"enum: {value} not in list: {field.enum}"
            return value
        if field.type == "Boolean":
            assert re.search(
                r"^(true|false)$", value, re.IGNORECASE
            ), f"{field.name} invalid flash boolean: {value}"
            return "1" if value.lower() == "true" else "0"
        return self.parse_string_or_number(field.type, value)
