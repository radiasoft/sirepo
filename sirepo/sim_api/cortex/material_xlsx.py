"""cortex input spreadsheet parser

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import math
import pandas
import pykern.pkcompat
import re
import urllib

# true expressions return a group(1) that's true (not None)
_BOOL_RE = re.compile(r"^(?:(t|true|y|yes)|f|false|n|no)$", re.IGNORECASE)

# Loose
_TYPE_RE = re.compile(r"(?:(fac(?:e|ing))|structur)", re.IGNORECASE)

_WALL_RE = re.compile(r"^(?:(iter)|demo)$", re.IGNORECASE)

_NEUTRON_SOURCE_RE = re.compile(r"\b(?:(d\W?t)|d\W?d)\b", re.IGNORECASE)

_POINTER_RE = re.compile(r"^((?:p|t|f)\d+(?:\.\d+)?)$", re.IGNORECASE)

_SOURCE_RE = re.compile(r"^(exp|pp|nom|ml|dft)$", re.IGNORECASE)

_IGNORE_FIRST_CELL_RE = re.compile(
    r"^(?:select|enter|please|choose)\s|^(?:material\s+name|multi-layer\s+geometry|operating\s+condition|composition|density\s+unit|legend|required\s+data|optional\s+data|add\s+or\s+remove)",
)

# TODO(pjm): comment is misspelled in xlsx
_IGNORE_INDEPENDENT_VARIABLE_HEADER_RE = re.compile(
    r"add add+itional independent", re.IGNORECASE
)

_COMPONENTS_COL = "components"

_COMPONENT_FROM_LOWER = None

_LABEL_TO_COL = None

_VALID_COLS = None

_WEIGHT = "Weight %"
_ATOM = "Atom %"

# Order in spreadsheet
_COMPONENT_VALUE_KINDS = (_WEIGHT, _ATOM)

_KINDS_ERR = " or ".join(_COMPONENT_VALUE_KINDS)

_TARGET = "Target"

_MIN = "Min"

_MAX = "Max"

_VALUE = "Value"

# Order in spreadsheet
_COMPONENT_VALUE_LABELS = (_TARGET, _MIN, _MAX)
_COMPOSITION_PROPERTIES = PKDict(
    density=PKDict(
        property_name="composition_density",
        property_unit="g/cm3",
    ),
    composition=PKDict(
        property_name="composition",
        property_unit="1",
    ),
)
_PROPERTY_VALUE_LABELS = (
    _VALUE,
    "Uncertainty",
    "Temperature [K]",
    "Neutron Fluence [1/cm2]",
)

_PROPERTY_NAMES = (
    "density",
    "yield strength",
    "tensile strength",
    "Young's modulus",
    "Poisson ratio",
    "fracture toughness",
    "creep",
    "thermal conductivity",
    "specific heat",
    "swelling",
    "hardness",
    "DBTT",
)
_PROPERTY_KEY_TO_NAME = None

_COMPONENT_ERROR = "error"

_BALANCE = "balance"

# TODO(robnagler) what's reasonable?
_EPSILON = 1e-8

_SUM = 100.0

_SUM_MAX = _SUM + _EPSILON

_SUM_MIN = _SUM - _EPSILON


class Parser:
    def __init__(self, path):
        self.errors = []
        self._sheet = self._run_now = self._col_num = None
        self.result = PKDict(
            components=PKDict(),
            properties=PKDict(),
        )
        self._parse_rows(self._read_and_split(path))
        if not self.errors:
            self._validate_result()

    def _error(self, msg, is_exc=False, **kwargs):
        """Append to errors and log

        Args:
            msg (str): to user
            is_exc (bool): to print stack
            col_num (int): if supplied else self._col_num
        """
        rv = PKDict(msg=msg)
        if s := self._sheet:
            rv.sheet = s
            if r := self._row_num:
                rv.row = r
                if c := kwargs.get("col_num", self._col_num):
                    rv.col = c
        self.errors.append(rv)
        pkdlog(
            "{}{}{}",
            rv,
            *(("stack=", pkdexc()) if is_exc else ("", "")),
        )
        return None

    def _parse_component(self, name, cols):
        c_err = f" for component={cols[0]}"

        def _floats(kind, values, start):
            for l, v, i in zip(
                _COMPONENT_VALUE_LABELS, values, range(start, start + 3)
            ):
                if isinstance(v, str):
                    if not len(v):
                        continue
                    if v.lower() == _BALANCE and l == _TARGET:
                        yield l, _BALANCE
                        continue
                rv, e = _parse_percent(v)
                if e:
                    self._error(f"{kind} {l} {e} in cell={v}{c_err}", col_num=i)
                    rv = None
                yield l, rv

        def _min_max(percentage):
            if _MAX not in percentage and _MIN not in percentage:
                return True
            if _MAX not in percentage:
                self._error(
                    f"{percentage.kind} {_MAX} must be provided with {_MIN}{c_err}"
                )
                return False
            if percentage[_MAX] == 0.0:
                self._error(f"{percentage.kind} {_MAX} must not be 0{c_err}")
                return False
            if _MIN not in percentage:
                percentage[_MIN] = 0.0
            elif percentage[_MIN] > percentage[_MAX]:
                self._error(
                    f"{percentage.kind} {_MAX}={percentage[_MAX]} must not be less than {_MIN}={percentage[_MIN]}{c_err}"
                )
                return False
            return True

        def _name():
            if not _COMPONENT_FROM_LOWER.get(name):
                return self._error(
                    f"unknown nuclide or element in cell={cols[0]}", col_num=1
                )
            if name in self.result.components:
                return self._error(
                    f"duplicate nuclide or element in cell={cols[0]}", col_num=1
                )
            return True

        def _percentage():
            rv = PKDict()
            for i, k in zip((1, 4), _COMPONENT_VALUE_KINDS):
                if x := PKDict(_floats(k, cols[i : i + 3], start=i + 1)):
                    rv[k] = x
            if len(rv) == 0:
                return self._error(f"either {_KINDS_ERR} must be provided{c_err}")
            if len(rv) > 1:
                return self._error(f"provide {_KINDS_ERR} not both{c_err}")
            if any(v is None for v in list(rv.values())[0].values()):
                # Message already output above
                return None
            return rv

        def _target(percentage):
            x = percentage.get(_MAX)
            if (rv := percentage.get(_TARGET)) is None:
                if percentage[_MIN] == 0.0:
                    return x
                return (x - percentage[_MIN]) / 2.0 + percentage[_MIN]
            if x is None:
                return rv
            if rv == _BALANCE:
                return rv
            if rv < percentage[_MIN]:
                return self._error(
                    f"{percentage.kind} {_TARGET}={rv} must not be less than {_MIN}={percentage[_MIN]}{c_err}"
                )
            if rv > percentage[_MAX]:
                return self._error(
                    f"{percentage.kind} {_TARGET}={rv} must not be greater than {_MAX}={x}{c_err}"
                )
            return rv

        if not _name():
            return None
        if not (p := _percentage()):
            return None
        x = list(p.keys())[0]
        rv = p[x].pkupdate(kind=x)
        if not _min_max(rv):
            return None
        if (x := _target(rv)) is None:
            return None
        rv[_TARGET] = x
        return rv

    def _add_property_value(self, name, values):
        # TODO(pjm): add independent variable columns
        # TODO(pjm): don't allow duplicate "value" values
        # TODO(pjm): only uncertainty may be empty
        self.result.properties[name].vals.append(
            PKDict(
                value=_parse_float(values[0]),
                uncertainty=_parse_float(values[1]),
                temperature_k=_parse_float(values[2]),
                neutron_fluence_1_cm2=_parse_float(values[3]),
            )
        )
        for i, p in self._independent_variables.items():
            if i < len(values):
                if "independent_variables" not in self.result.properties[name]:
                    self.result.properties[name].independent_variables = PKDict()
                if p.name not in self.result.properties[name].independent_variables:
                    self.result.properties[name].independent_variables[p.name] = []
                self.result.properties[name].independent_variables[p.name].append(
                    _parse_float(values[i])
                )

    def _parse_rows(self, rows):
        # TODO(robnagler) track the sheet/row of each element so
        # can provide more context in _validate_result

        def _component(label, cols):
            if self._in_components is _COMPONENT_ERROR:
                return
            self.result.components[label] = PKDict(
                name=label,
                label=cols[0],
                percentage=self._parse_component(label, cols),
            )

        def _dispatch(cols):
            if _early_check(cols):
                return
            e = None
            l = cols[0].lower()
            v = cols[1]
            if isinstance(v, str) and v.lower() == _VALUE.lower():
                self._last_property = _format_property(l)
            elif _IGNORE_FIRST_CELL_RE.search(l):
                if self._in_components:
                    self._in_components = False
            elif x := _LABEL_TO_COL.get(l):
                _known_col(l, v, x)
            elif "nuclide" in l:
                _nuclide(cols)
            elif self._in_components:
                _component(l, cols)
            elif (
                l == _PROPERTY_VALUE_LABELS[0].lower()
                and tuple(cols[0:4]) == _PROPERTY_VALUE_LABELS
            ):
                _property_value(cols)
            else:
                self._error(f"unable to parse row={cols}")

        def _early_check(cols):
            if not isinstance(cols[0], str) and not self._in_property_values:
                self._error(f"expected string cell={cols[0]}", col_num=1)
            elif self._in_property_values and isinstance(cols[0], float):
                self._add_property_value(self._last_property, cols)
            else:
                return False
            return True

        def _known_col(label, value, col):
            if self._in_components:
                self._in_components = False
            if not (e := _simple(col, value)):
                return
            s = str(value)
            if len(s):
                s = "=" + s
            self._error(f"invalid {label}{s} {e}", col_num=2)

        def _nuclide(cols):
            assert self._in_components is None
            if tuple(cols[1:7]) == _COMPONENT_VALUE_LABELS * 2:
                self._in_components = True
            else:
                self._in_components = _COMPONENT_ERROR
                self._error(
                    f"Element and Nuclide column labels incorrect cols={cols[1:7]}"
                )

        def _next_row():
            try:
                return next(rows)
            except StopIteration:
                return None

        def _property_value(cols):
            self._in_property_values = True
            i = len(_PROPERTY_VALUE_LABELS)
            while cols[i] and not _IGNORE_INDEPENDENT_VARIABLE_HEADER_RE.search(
                cols[i]
            ):
                self._independent_variables[i] = PKDict(name=cols[i], vals=[])
                i += 1

        def _simple(col, value):
            if isinstance(value, str) and not len(value):
                if col.is_required:
                    return "may not be blank"
                v = None
            else:
                v, e = col.parser(value)
                if e:
                    return e
            if col.name == "property_name":
                self._last_property = v
                self._independent_variables = PKDict()
            n = col.name
            if col.is_property and self._last_property:
                u = None
                if self._sheet == "Properties":
                    p = self._last_property
                elif self._last_property in _COMPOSITION_PROPERTIES:
                    p = _COMPOSITION_PROPERTIES[self._last_property].property_name
                    u = _COMPOSITION_PROPERTIES[self._last_property].property_unit
                if p not in self.result.properties:
                    self.result.properties[p] = PKDict(
                        vals=[],
                        property_unit=u,
                    )
                self.result.properties[p][n] = v
            self.result[n] = v
            return None

        self._in_property_values = False
        self._independent_variables = PKDict()
        self._in_components = None
        self._last_property = None
        while r := _next_row():
            try:
                # first case probably doesn't happen, but need the check anyway
                if len(r) < 2 or not r[0]:
                    continue
                _dispatch(r)
            except Exception as e:
                self._error(f"error={e}", is_exc=True)
            finally:
                self._col_num = None

    def _read_and_split(self, path):
        def _fix(col_num, v):
            self._col_num = col_num
            if isinstance(v, bool):
                return v
            if isinstance(v, float):
                return "" if math.isnan(v) else v
            if isinstance(v, int):
                # TODO(robnagler) seems reasonable
                return float(v)
            # Always strip strings
            return str(v).strip()

        n = None
        try:
            for n, s in pandas.read_excel(
                str(path), header=None, sheet_name=None
            ).items():
                self._sheet = n
                if self._in_components:
                    self._in_components = False
                for i, r in enumerate(s.itertuples(index=False), start=1):
                    # Remove pandas objects to avoid problems in string
                    # conversions later. See also
                    # https://github.com/radiasoft/pykern/issues/574
                    self._row_num = i
                    rv = tuple(_fix(*x) for x in enumerate(r, start=1))
                    self._col_num = None
                    yield rv
        except Exception as e:
            self._error(f"error={e}", is_exc=True)
        finally:
            self._sheet = None

    def _validate_components(self, rows):
        def _balance(kind):
            s = 0.0
            b = None
            for r in rows.values():
                t = r.percentage[_TARGET]
                if t == _BALANCE:
                    if b:
                        return self._error(
                            f"'balance' may only be used once components=({r.label}, {b.label})"
                        )
                    b = r
                else:
                    s += t
            if s > _SUM_MAX:
                return self._error(f"{kind} sum={s:g} greater than {_SUM:g}")
            if not b:
                if s < _SUM_MIN:
                    return self._error(f"{kind} sum={s:g} less than {_SUM:g}")
            else:
                b.percentage[_TARGET] = _SUM - s
                if b.percentage[_TARGET] < 0.0:
                    b.percentage[_TARGET] = 0.0
            return kind

        def _db_fields():
            rv = PKDict()
            for r in rows.values():
                rv[r.name] = PKDict(
                    material_component_name=r.name,
                    max_pct=r.percentage.get(_MAX),
                    min_pct=r.percentage.get(_MIN),
                    target_pct=r.percentage[_TARGET],
                )
            self.result.components = rv

        def _kind():
            k = list(rows.values())[0].percentage.kind
            if any(r.percentage.kind != k for r in rows.values()):
                return self._error(f"do not provide both {_KINDS_ERR}")
            self.result.is_atom_pct = k == _ATOM
            return k

        if any(v.percentage is None for v in rows.values()):
            # error for at least one component output
            return
        if _balance(_kind()):
            _db_fields()

    def _validate_result(self):
        def _labels(names):
            return ", ".join(sorted(_VALID_COLS[n].label for n in names))

        if x := set(_VALID_COLS) - set(self.result.keys()):
            self._error(f"missing properties=({_labels(x)})")
        if not (x := self.result.get(_COMPONENTS_COL)):
            self._error("at least one element or nuclide must be provided")
            return
        self._validate_components(x)
        # TODO(pjm): validate properties
        # remove property values at root level
        for col in _LABEL_TO_COL.values():
            if col.is_property and col.name in self.result:
                del self.result[col.name]


def _format_property(name):
    return re.sub(r"'", "", name).replace(" ", "_").lower()


def _init():
    def _cols():
        for k, v, r, p in (
            ("Availability Factor", "availability_factor", False, False),
            ("Bare Tile", "is_bare_tile", False, False),
            ("Comments", "comments", False, True),
            ("DOI or URL", "doi_or_url", False, True),
            ("Density", "density_g_cm3", True, False),
            ("Homogenized Divertor", "is_homogenized_divertor", False, False),
            ("Homogenized HCPB", "is_homogenized_hcpb", False, False),
            ("Homogenized WCLL", "is_homogenized_wcll", False, False),
            ("Material Type", "is_plasma_facing", True, False),
            ("Microstructure Information", "microstructure", False, False),
            ("Name", "material_name", True, False),
            ("Neutron Source", "is_neutron_source_dt", False, False),
            ("Neutron Wall Loading", "neutron_wall_loading", False, False),
            ("Pointer", "pointer", False, True),
            ("Processing", "processing_steps", False, False),
            ("Property Name", "property_name", False, False),
            ("Property Unit", "property_unit", False, True),
            ("Source", "source", False, True),
            ("Structure", "structure", False, False),
        ):
            yield k.lower(), PKDict(
                label=k,
                name=v,
                parser=globals()[f"_parse_{v}"],
                is_required=r,
                is_property=p,
            )

    def _components():
        for x in "elements", "nuclides":
            for y in _COMPONENTS[x]:
                yield y.lower(), y

    global _COMPONENT_FROM_LOWER, _LABEL_TO_COL, _VALID_COLS, _PROPERTY_KEY_TO_NAME
    _COMPONENT_FROM_LOWER = PKDict(_components())
    _LABEL_TO_COL = PKDict(_cols())
    _VALID_COLS = PKDict(
        {c.name: c for c in [v for v in _LABEL_TO_COL.values() if v.is_required]}
    )
    _PROPERTY_KEY_TO_NAME = PKDict(
        zip(
            [_format_property(v) for v in _PROPERTY_NAMES],
            _PROPERTY_NAMES,
        )
    )


def _parse_availability_factor(value):
    return _parse_percent(value)


def _parse_bool(value):
    if isinstance(value, bool):
        return value, None
    if isinstance(value, str) and (m := _BOOL_RE.match(value)):
        return bool(m.group(1)), None
    return None, "must be yes, no, true, false"


def _parse_comments(value):
    return value, None


def _parse_density_g_cm3(value):
    if (rv := _parse_float(value)) is None:
        return None, "must be number (g/cm3)"
    if 0.0 < rv < 25:
        return rv, None
    return None, "must be between 0 and 25 g/cm3"


def _parse_doi_or_url(value):
    # ex. 10.1007/s11089-018-0833-1 or a url
    if urllib.parse.urlparse(value).scheme in ("http", "https") or re.search(
        r"^10\.\d{4}/.+", value
    ):
        return value, None
    return None, "Expecting a valid URL or DOI"


def _parse_float(value):
    if isinstance(value, float):
        return value
    if not isinstance(value, str):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _parse_is_bare_tile(value):
    return _parse_bool(value)


def _parse_is_homogenized_divertor(value):
    return _parse_bool(value)


def _parse_is_homogenized_hcpb(value):
    return _parse_bool(value)


def _parse_is_homogenized_wcll(value):
    return _parse_bool(value)


def _parse_material_name(value):
    return value, None


def _parse_is_plasma_facing(value):
    if isinstance(value, str) and (m := _TYPE_RE.search(value)):
        return bool(m.group(1)), None
    return None, "must be structural or plasma-facing"


def _parse_is_neutron_source_dt(value):
    if isinstance(value, str) and (m := _NEUTRON_SOURCE_RE.search(value)):
        return bool(m.group(1)), None
    return None, "must be D-T or D-D"


def _parse_microstructure(value):
    return _parse_string(value, 500)


def _parse_neutron_wall_loading(value):
    if isinstance(value, str) and (m := _WALL_RE.search(value)):
        # ITER is true
        return ("ITER" if m.group(1) else "DEMO"), None
    return None, "must be ITER or DEMO"


def _parse_percent(value):
    if (rv := _parse_float(value)) is None:
        return None, "must be a number (percentage)"
    if value < 0.0:
        return None, "must not be negative"
    if value > _SUM:
        return None, f"must not be greater than {_SUM:g}"
    return value, None


def _parse_pointer(value):
    if isinstance(value, str) and (m := _POINTER_RE.search(value)):
        return m.group(1).upper(), None
    return None, "expected location number with P, T or F prefix"


def _parse_property_name(value):
    if value and _format_property(value) not in _PROPERTY_KEY_TO_NAME:
        return None, f"unknown property name"
    return _format_property(value), None


def _parse_property_unit(value):
    # TODO(pjm): expected SI unit per property type
    return value, None


def _parse_source(value):
    if isinstance(value, str) and (m := _SOURCE_RE.search(value)):
        return m.group(1).upper(), None
    return None, "invalid source value"


def _parse_string(value, length):
    if value and len(value) > length:
        return None, f"value exceeded {length} characters"
    return value, None


def _parse_structure(value):
    return _parse_string(value, 100)


def _parse_processing_steps(value):
    return _parse_string(value, 500)


# See pkcli.cortex.gen_components
_COMPONENTS = PKDict(
    elements={
        "Ac",
        "Ag",
        "Al",
        "Am",
        "Ar",
        "As",
        "At",
        "Au",
        "B",
        "Ba",
        "Be",
        "Bh",
        "Bi",
        "Bk",
        "Br",
        "C",
        "Ca",
        "Cd",
        "Ce",
        "Cf",
        "Cl",
        "Cm",
        "Cn",
        "Co",
        "Cr",
        "Cs",
        "Cu",
        "Db",
        "Ds",
        "Dy",
        "Er",
        "Es",
        "Eu",
        "F",
        "Fe",
        "Fl",
        "Fm",
        "Fr",
        "Ga",
        "Gd",
        "Ge",
        "H",
        "He",
        "Hf",
        "Hg",
        "Ho",
        "Hs",
        "I",
        "In",
        "Ir",
        "K",
        "Kr",
        "La",
        "Li",
        "Lr",
        "Lu",
        "Lv",
        "Mc",
        "Md",
        "Mg",
        "Mn",
        "Mo",
        "Mt",
        "N",
        "Na",
        "Nb",
        "Nd",
        "Ne",
        "Nh",
        "Ni",
        "No",
        "Np",
        "O",
        "Og",
        "Os",
        "P",
        "Pa",
        "Pb",
        "Pd",
        "Pm",
        "Po",
        "Pr",
        "Pt",
        "Pu",
        "Ra",
        "Rb",
        "Re",
        "Rf",
        "Rg",
        "Rh",
        "Rn",
        "Ru",
        "S",
        "Sb",
        "Sc",
        "Se",
        "Sg",
        "Si",
        "Sm",
        "Sn",
        "Sr",
        "Ta",
        "Tb",
        "Tc",
        "Te",
        "Th",
        "Ti",
        "Tl",
        "Tm",
        "Ts",
        "U",
        "V",
        "W",
        "Xe",
        "Y",
        "Yb",
        "Zn",
        "Zr",
    },
    nuclides={
        "Ag107",
        "Ag109",
        "Al26",
        "Al27",
        "Am241",
        "Am243",
        "Ar36",
        "Ar38",
        "Ar39",
        "Ar40",
        "As75",
        "Au197",
        "B10",
        "B11",
        "Ba130",
        "Ba132",
        "Ba134",
        "Ba135",
        "Ba136",
        "Ba137",
        "Ba138",
        "Be10",
        "Be9",
        "Bi208",
        "Bi209",
        "Bk247",
        "Br79",
        "Br81",
        "C12",
        "C13",
        "C14",
        "Ca40",
        "Ca41",
        "Ca42",
        "Ca43",
        "Ca44",
        "Ca46",
        "Ca48",
        "Cd106",
        "Cd108",
        "Cd110",
        "Cd111",
        "Cd112",
        "Cd113",
        "Cd114",
        "Cd116",
        "Ce136",
        "Ce138",
        "Ce140",
        "Ce142",
        "Cf249",
        "Cf251",
        "Cl35",
        "Cl36",
        "Cl37",
        "Cm245",
        "Cm246",
        "Cm247",
        "Cm248",
        "Cm250",
        "Co59",
        "Cr50",
        "Cr52",
        "Cr53",
        "Cr54",
        "Cs133",
        "Cs135",
        "Cu63",
        "Cu65",
        "Dy154",
        "Dy156",
        "Dy158",
        "Dy160",
        "Dy161",
        "Dy162",
        "Dy163",
        "Dy164",
        "Er162",
        "Er164",
        "Er166",
        "Er167",
        "Er168",
        "Er170",
        "Eu151",
        "Eu153",
        "F19",
        "Fe54",
        "Fe56",
        "Fe57",
        "Fe58",
        "Fe60",
        "Ga69",
        "Ga71",
        "Gd150",
        "Gd152",
        "Gd154",
        "Gd155",
        "Gd156",
        "Gd157",
        "Gd158",
        "Gd160",
        "Ge70",
        "Ge72",
        "Ge73",
        "Ge74",
        "Ge76",
        "H1",
        "H2",
        "He3",
        "He4",
        "Hf174",
        "Hf176",
        "Hf177",
        "Hf178",
        "Hf179",
        "Hf180",
        "Hf182",
        "Hg194",
        "Hg196",
        "Hg198",
        "Hg199",
        "Hg200",
        "Hg201",
        "Hg202",
        "Hg204",
        "Ho163",
        "Ho165",
        "I127",
        "I129",
        "In113",
        "In115",
        "Ir191",
        "Ir193",
        "K39",
        "K40",
        "K41",
        "Kr78",
        "Kr80",
        "Kr81",
        "Kr82",
        "Kr83",
        "Kr84",
        "Kr86",
        "La137",
        "La138",
        "La139",
        "Li10",
        "Li11",
        "Li12",
        "Li4",
        "Li5",
        "Li6",
        "Li7",
        "Li8",
        "Li9",
        "Lu175",
        "Lu176",
        "Mg24",
        "Mg25",
        "Mg26",
        "Mn53",
        "Mn55",
        "Mo100",
        "Mo92",
        "Mo93",
        "Mo94",
        "Mo95",
        "Mo96",
        "Mo97",
        "Mo98",
        "N14",
        "N15",
        "Na23",
        "Nb91",
        "Nb92",
        "Nb93",
        "Nb94",
        "Nd142",
        "Nd143",
        "Nd144",
        "Nd145",
        "Nd146",
        "Nd148",
        "Nd150",
        "Ne20",
        "Ne21",
        "Ne22",
        "Ni58",
        "Ni59",
        "Ni60",
        "Ni61",
        "Ni62",
        "Ni63",
        "Ni64",
        "Np236",
        "Np237",
        "O16",
        "O17",
        "O18",
        "Os184",
        "Os186",
        "Os187",
        "Os188",
        "Os189",
        "Os190",
        "Os192",
        "P31",
        "Pa231",
        "Pb202",
        "Pb204",
        "Pb205",
        "Pb206",
        "Pb207",
        "Pb208",
        "Pd102",
        "Pd104",
        "Pd105",
        "Pd106",
        "Pd107",
        "Pd108",
        "Pd110",
        "Po209",
        "Pr141",
        "Pt190",
        "Pt192",
        "Pt194",
        "Pt195",
        "Pt196",
        "Pt198",
        "Pu239",
        "Pu240",
        "Pu242",
        "Pu244",
        "Ra226",
        "Rb85",
        "Rb87",
        "Re185",
        "Re187",
        "Rh103",
        "Ru100",
        "Ru101",
        "Ru102",
        "Ru104",
        "Ru96",
        "Ru98",
        "Ru99",
        "S32",
        "S33",
        "S34",
        "S36",
        "Sb121",
        "Sb123",
        "Sc45",
        "Se74",
        "Se76",
        "Se77",
        "Se78",
        "Se79",
        "Se80",
        "Se82",
        "Si28",
        "Si29",
        "Si30",
        "Si32",
        "Sm144",
        "Sm146",
        "Sm147",
        "Sm148",
        "Sm149",
        "Sm150",
        "Sm152",
        "Sm154",
        "Sn112",
        "Sn114",
        "Sn115",
        "Sn116",
        "Sn117",
        "Sn118",
        "Sn119",
        "Sn120",
        "Sn122",
        "Sn124",
        "Sn126",
        "Sr84",
        "Sr86",
        "Sr87",
        "Sr88",
        "Ta181",
        "Tb158",
        "Tb159",
        "Tc97",
        "Tc98",
        "Tc99",
        "Te120",
        "Te122",
        "Te123",
        "Te124",
        "Te125",
        "Te126",
        "Te128",
        "Te130",
        "Th229",
        "Th230",
        "Th232",
        "Ti46",
        "Ti47",
        "Ti48",
        "Ti49",
        "Ti50",
        "Tl203",
        "Tl205",
        "Tm169",
        "U233",
        "U234",
        "U235",
        "U236",
        "U238",
        "V50",
        "V51",
        "W180",
        "W182",
        "W183",
        "W184",
        "W186",
        "Xe124",
        "Xe126",
        "Xe128",
        "Xe129",
        "Xe130",
        "Xe131",
        "Xe132",
        "Xe134",
        "Xe136",
        "Y89",
        "Yb168",
        "Yb170",
        "Yb171",
        "Yb172",
        "Yb173",
        "Yb174",
        "Yb176",
        "Zn64",
        "Zn66",
        "Zn67",
        "Zn68",
        "Zn70",
        "Zr90",
        "Zr91",
        "Zr92",
        "Zr93",
        "Zr94",
        "Zr96",
    },
)

_init()
