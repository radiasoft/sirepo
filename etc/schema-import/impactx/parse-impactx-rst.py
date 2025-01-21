from impactx import elements, distribution
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog
import docutils.frontend
import docutils.parsers.rst
import docutils.utils
import inspect
import pykern.pkio
import pykern.pkjson
import re

_SKIP_FIELDS = PKDict(
    BeamMonitor=["backend", "encoding"],
)


def models_from_python():
    _TYPE = PKDict(
        {
            "float": "Float",
            "str": "String",
            "int": "Integer",
            "list[float]": "FloatArray",
        }
    )

    def _parse_init(name, init):
        m = re.match(r".*?,\s*(.*?)\)", init)
        if m:
            res = {}
            n = m.group(1)
            for v in re.findall(r"(\w+)\: (.*?)(?:,|$)", n):
                f, t = v
                d = None
                if "=" in t:
                    t, d = re.split(r"\s*=\s*", t)
                t = _TYPE[t]
                if d is not None:
                    if t == "Float":
                        d = float(d)
                    elif t == "Integer":
                        d = int(d)
                    elif t == "String":
                        d = re.sub(r'"|\'', "", d)
                assert f not in res
                res[f] = PKDict(
                    type=t,
                    default=d,
                )
            return res
        return None

    models = {}
    for name, obj in inspect.getmembers(distribution) + inspect.getmembers(elements):
        cls = (
            getattr(elements, name)
            if hasattr(elements, name)
            else getattr(distribution, name)
        )
        if not inspect.isclass(cls):
            continue
        v = _parse_init(name, inspect.getdoc(cls.__init__))
        if v:
            models[name] = v
    return models


class PyClass(docutils.parsers.rst.Directive):
    has_content = True
    models = []

    def run(self):
        desc = ""
        help = None
        state = "header"
        for r in self.content:
            if state == "header":
                name, fields = self._parse_init(r)
                if not name:
                    return []
                state = "desc"
                continue
            if state in ("desc", "help") and ":param" in r:
                state = "param"
            if state == "desc":
                if desc:
                    desc += "\n"
                desc += r
                continue
            if state == "param":
                m = re.search(":param\s+(\w+): (.*)", r)
                assert m, f"failed to parse param: {r}"
                f = m.group(1)
                help = [m.group(2)]
                assert f in fields, f"unknown field: {name}.{f}"
                fields[f].help = help
                state = "help"
                continue
            if state == "help":
                if not r:
                    continue
                if re.search(r"\.\. py:property::", r):
                    break
                help.append(r)
                continue
        if not name:
            return []
        PyClass.models.append(
            PKDict(
                name=name,
                description=desc,
                fields=fields,
            )
        )
        return []

    def _parse_init(self, init):
        m = re.search(r"impactx.(?:elements|distribution).(\w+)\((.*)\)", init)
        if m:
            fields = {}
            name = m.group(1)
            args = re.split(r",\s*", m.group(2))
            for a in args:
                dv = None
                if "=" in a:
                    f, dv = a.split("=")
                else:
                    f = a
                fields[f] = PKDict(
                    default=dv,
                )
            return m.group(1), fields
        return "", {}


class PyFunction(docutils.parsers.rst.Directive):
    has_content = True

    def run(self):
        return []


def schema_from_python_rst(filename):

    def _format_default(field_type, value):
        if value is None:
            return value
        if field_type == "Integer":
            return int(value)
        if field_type == "Float":
            return float(value)
        value = re.sub(r'"|\'', "", value)
        return value

    def _format_desc(desc):
        desc = re.sub(r"\.\. math::\n\n\s+(.*?)\n\n", r"$\1$ ", desc, re.MULTILINE)
        desc = re.sub(r"\:math:`(.*?)`", r"$\1$", desc)
        desc = re.sub(r"\\", r"\\\\", desc)
        desc = re.sub(r"``", "", desc)
        desc = re.sub(r"(`_+)|`", "", desc)
        desc = re.sub(r"<(http.*?)>", r"\1", desc)
        desc = re.sub(r"\.?\n+$", "", desc)
        return desc

    def _parse_field_desc(field_info):
        h = field_info.get("help", [])
        h = " ".join([re.sub(r":math:`(.*?)`", r"$\1$", s.strip()) for s in h])
        # normalize text
        h = re.sub(r"\.$", "", h)
        h = re.sub(r"\((in )?meters\)", "in m", h)
        h = re.sub(r"\((in )?radians\)", "in rad", h)
        h = re.sub(r"\[degrees\]", "in deg", h)
        field_info.units = None
        e = r"(?:\s+in (m\^\(-2\)|m\^\(-1\)|m|1/m|rad|deg))(\b|\s|$)"
        m = re.match(rf".*?{e}", h)
        if m:
            field_info.units = m.group(1)
            h = re.sub(e, "", h, 1)
        field_info.help = h
        _parse_type(field_info)
        field_info.help = _format_desc(h)

    def _parse_type(field_info):
        h = field_info.help
        enum_values = []
        for v in re.findall(r"``(.*?)``", h):
            if "float" in v:
                break
            v = re.sub('"', "", v)
            enum_values.append(v)
        if len(enum_values):
            field_info.enum = enum_values
            field_info.type = "enum"
            field_info.help = re.sub(r"``", "", h)
        elif "array of ``float``" in h:
            field_info.type = "FloatArray"
        elif h.startswith("name of"):
            field_info.type = "String"
        elif (
            re.search(r"\bnumber of", h)
            or h.startswith("index")
            or h.startswith("specification of units")
        ):
            field_info.type = "Integer"
        else:
            field_info.type = "Float"

    docutils.parsers.rst.directives.register_directive("py:class", PyClass)
    docutils.parsers.rst.directives.register_directive("py:function", PyFunction)

    docutils.parsers.rst.Parser().parse(
        pykern.pkio.read_text(filename),
        docutils.utils.new_document(
            filename,
            docutils.frontend.get_default_settings(docutils.parsers.rst.Parser),
        ),
    )

    schema = PKDict(
        enum=PKDict(
            unit=[
                ["0", "1/m"],
                ["1", "T"],
            ],
        ),
        model={},
        view={},
    )

    for m in PyClass.models:
        model = {}
        schema.model[m.name] = model
        schema.view[m.name] = PKDict(
            description=_format_desc(m.description),
        )

        for f, v in m.fields.items():
            if f in _SKIP_FIELDS.get(m.name, []):
                continue
            v.field = f
            _parse_field_desc(v)
            if v.type == "enum":
                assert f not in schema.enum
                schema.enum[f] = [[e, e] for e in v.enum]
                v.type = f
            if f == "unit":
                v.type = "unit"
            label = f
            if v.units:
                label += f" [{v.units}]"
            model[f] = [
                label,
                v.type,
                _format_default(v.type, v.default),
                v.help,
            ]
    return schema


def parse_schema(filename):
    schema = schema_from_python_rst(filename)
    pymodels = models_from_python()

    for name in schema.model:
        assert name in pymodels
        m1 = pymodels[name]
        m2 = schema.model[name]
        for f in m1:
            f2 = f
            if f2 in _SKIP_FIELDS.get(name, []):
                continue
            if f2 not in m2:
                if f2.lower() in m2:
                    f2 = f.lower()
                else:
                    pkdlog("missing: {} {}", name, f)
                    continue
            if m2[f2][1] != m1[f].type and m2[f][1] != f:
                pkdlog(
                    "warning: type mismatch: {} {} {} != {}",
                    name,
                    f,
                    m2[f2][1],
                    m1[f].type,
                )
            if m2[f2][2] != m1[f].default:
                pkdlog(
                    "warning: default mismatch: {} {} {} != {}",
                    name,
                    f,
                    m2[f2][2],
                    m1[f].default,
                )
    return schema


# the RST parser will show an error: Unknown interpreted text role "py:class", but it continues after that.
pykern.pkjson.dump_pretty(
    parse_schema("/home/vagrant/src/ECP-WarpX/impactx/docs/source/usage/python.rst"),
    "impactx-schema.json",
)
