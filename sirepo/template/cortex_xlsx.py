"""cortex spreadsheet parser

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import math
import pandas
import pykern.pkcompat
import re

# true expressions return a group(1) that's true (not None)
_BOOL_RE = re.compile(r"^(?:(t|true|y|yes)|f|false|n|no)$", re.IGNORECASE)

# Loose
_TYPE_RE = re.compile(r"(?:(fac(?:e|ing))|structur)", re.IGNORECASE)

_WALL_RE = re.compile(r"^(?:(iter)|demo)$", re.IGNORECASE)

_SOURCE_RE = re.compile(r"\b(?:(d\W?t)|d\W?d)\b", re.IGNORECASE)

_IGNORE_FIRST_CELL_RE = re.compile(
    r"^(?:select|enter|please|choose)\s|^(?:material\s+name|multi-layer\s+geometry|operating\s+condition|composition|density\s+unit)",
)
_COMPONENTS_COL = "components"

_COMPONENT_FROM_LOWER = None

_LABEL_TO_COL = None

_VALID_COLS = None

_WEIGHT = "Weight %"
_ATOM = "Atom %"

# Order in spreadsheet
_COMPONENT_VALUE_KINDS = (_WEIGHT, _ATOM)

_KINDS_OR_STR = " or ".join(_COMPONENT_VALUE_KINDS)

_TARGET = "Target"

_MIN = "Min"

_MAX = "Max"

# Order in spreadsheet
_COMPONENT_VALUE_LABELS = (_TARGET, _MIN, _MAX)

_COMPONENT_ERROR = "error"

_BALANCE = "balance"


class Parser:
    def __init__(self, path, qcall=None):
        self.errors = []
        self._sheet = self._run_now = self._col_num = None
        self.result = PKDict(components=PKDict())
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
        if s := self._sheet:
            msg += f" sheet={s}"
            if r := self._row_num:
                msg += f" row={r}"
                if c := kwargs.get("col_num", self._col_num):
                    msg += f" col={c}"
        self.errors.append(msg)
        pkdlog(
            "{}{}{}",
            msg,
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
                if (rv := _parse_float(v, is_percent=True)) is None:
                    self._error(
                        f"{kind} {n} must be a percentage in cell={v}{c_err}", col_num=i
                    )
                yield l, rv

        def _min_max(percentage):
            if _MAX not in percentage and _MIN not in percentage:
                return True
            if _MAX not in percentage:
                self._error(f"{percentage.kind} {_MAX} must be provided with {_MIN}{c_err}")
                return False
            if percentage[_MAX] == 0.0:
                self._error(f"{percentage.kind} {_MAX} must not be 0{c_err}")
                return False
            if _MIN not in percentage:
                percentage[_MIN] = 0.0
            elif percentage[_MIN] > percentage[_MAX]:
                self._error(f"{percentage.kind} {_MAX}={percentage[_MAX]} must not be less than {_MIN}={percentage[_MIN]}{c_err}")
                return False
            return True

        def _name():
            if not _COMPONENT_FROM_LOWER.get(name):
                return self._error(
                    f"unknown nuclide or element in cell='{cols[0]}'", col_num=1
                )
            if name in self.result.components:
                return self._error(
                    f"duplicate nuclide or element in cell='{cols[0]}'", col_num=1
                )
            return True

        def _target(percentage):
            x = percentage.get(_MAX)
            if (rv := percentage.get(_TARGET)) is None:
                if percentage[_MIN] == 0.0:
                    return x
                return (x - percentage[_MIN]) / 2.0
            if x is None:
                return rv
            if rv < percentage[_MIN]:
                return self._error(f"{percentage.kind} {_TARGET}={rv} must not be less than {_MIN}={percentage[_MIN]}{c_err}")
            if rv > percentage[_MAX]:
                return self._error(f"{percentage.kind} {_TARGET}={rv} must not be greater than {_MAX}={x}{c_err}")
            return rv

        def _percentage():
            rv = PKDict()
            for i, k in zip((1, 4), _COMPONENT_VALUE_KINDS):
                if x := PKDict(_floats(k, cols[i : i + 3], start=i + 1)):
                    rv[k] = x
            if len(rv) == 0:
                return self._error(f"either {_KINDS_OR_STR} must be provided{c_err}")
            if len(rv) > 1:
                return self._error(f"provide {_KINDS_OR_STR} not both{c_err}")
            if any(v is None for v in list(rv.values())[0].values()):
                # Message already output above
                return None
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

    def _parse_rows(self, rows):
        # TODO(robnagler) track the sheet/row of each element so
        # can provide more context in _validate_result

        def _dispatch(cols):
            e = None
            if not isinstance(cols[0], str):
                self._error(f"expected string cell='{cols[0]}'", col_num=1)
                return
            l = cols[0].lower()
            if _IGNORE_FIRST_CELL_RE.search(l):
                if self._in_components:
                    self._in_components = False
            elif x := _LABEL_TO_COL.get(l):
                if self._in_components:
                    self._in_components = False
                if e := _simple(x, cols[1]):
                    self._error(f"invalid {l}='{cols[1]}' {e}", col_num=2)
            elif "nuclide" in l:
                assert self._in_components is None
                if tuple(cols[1:7]) == _COMPONENT_VALUE_LABELS * 2:
                    self._in_components = True
                else:
                    self._in_components = _COMPONENT_ERROR
                    self._error(
                        f"Element and Nuclide column labels incorrect cols={cols[1:7]}"
                    )
            elif self._in_components:
                if self._in_components is not _COMPONENT_ERROR:
                    self.result.components[l] = PKDict(
                        name=l, label=cols[0], percentage=self._parse_component(l, cols)
                    )
            else:
                self._error(f"unable to parse row='{cols}'")

        def _next_row():
            try:
                return next(rows)
            except StopIteration:
                return None

        def _simple(col, value):
            if isinstance(value, str) and not len(value):
                return "may not be blank"
            v, e = col.parser(value)
            if e:
                return e
            self.result[col.name] = v
            return None

        self._in_components = None
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
        def _kind():
            rv = list(rows.values())[0].percentage.kind
            if any(r.percentage.kind != rv for r in rows.values()):
                self._error(f"do not provide both {_KINDS_OR_STR}")
                return None
            return rv

        # def _targets(kind_values):
        #     rv = []
        #     if _TARGET not in v:
        #         if

        if any(v.percentage is None for v in rows.values()):
            # error for at least one component output
            return
        if not (k := _kind()):
            return

    #        _balance(_targets(r.values[k] for r in rows.values()), rows)

    def _validate_result(self):
        def _labels(names):
            ", ".join(sorted(_VALID_COLS[n].label for n in names))

        if x := set(_VALID_COLS) - set(self.result.keys()):
            self._error(f"missing properties=({_labels(x)})")
        if not (x := self.result.get(_COMPONENTS_COL)):
            self._error("at least one element or nuclide must be provided")
            return
        self._validate_components(x)


def _parse_bool(value):
    if isinstance(value, bool):
        return value, None
    if isinstance(value, str) and (m := _BOOL_RE.match(value)):
        return bool(m.group(1)), None
    return None, "must be yes, no, true, false"


def _parse_float(value, is_percent=False):
    if isinstance(value, float):
        return value
    if not isinstance(value, str):
        return None
    if is_percent:
        value = value.rstrip("%")
    try:
        return float(value)
    except Exception:
        return None


def _parse_availability_factor(value):
    if (rv := _parse_float(value, is_percent=True)) is None:
        return None, "must be a percentage"
    # 1 is unreasonable
    if 1 < rv < 100:
        return rv / 100, None
    if 0 < rv < 1:
        return rv, None
    return None, "must be between 1 and 100"


def _parse_density_g_cm3(value):
    if (rv := _parse_float(value, is_percent=True)) is None:
        return None, "must be number (g/cm3)"
    # 1 is unreasonable
    if 1 <= rv <= 25:
        return rv, None
    return None, "must be between 1 and 25 g/cm3"


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
    if isinstance(value, str) and (m := _TYPE_RE.match(value)):
        return bool(m.group(1)), None
    return None, "must be structural or plasma-facing"


def _parse_is_neutron_source_dt(value):
    if isinstance(value, str) and (m := _SOURCE_RE.match(value)):
        return bool(m.group(1)), None
    return None, "must be D-T or D-D"


def _parse_neutron_wall_loading(value):
    if isinstance(value, str) and (m := _WALL_RE.match(value)):
        # ITER is true
        return ("ITER" if m.group(1) else "DEMO"), None
    return None, "must be ITER or DEMO"


#    if isinstance(value, float):
#        if 0.1 <= value <= 10.0:
#            return value, None
#    return None, "must be iter, demo, or MW/m2 between .1 and 10"


def _init():
    def _cols():
        for k, v in (
            ("Availability Factor", "availability_factor"),
            ("Bare Tile", "is_bare_tile"),
            ("Density", "density_g_cm3"),
            ("Homogenized Divertor", "is_homogenized_divertor"),
            ("Homogenized HCPB", "is_homogenized_hcpb"),
            ("Homogenized WCLL", "is_homogenized_wcll"),
            ("Material Type", "is_plasma_facing"),
            ("Name", "material_name"),
            ("Neutron Source", "is_neutron_source_dt"),
            ("Neutron Wall Loading", "neutron_wall_loading"),
        ):
            yield k.lower(), PKDict(label=k, name=v, parser=globals()[f"_parse_{v}"])

    def _components():
        for x in "elements", "nuclides":
            for y in _COMPONENTS[x]:
                yield y.lower(), y

    global _COMPONENT_FROM_LOWER, _LABEL_TO_COL, _VALID_COLS
    _COMPONENT_FROM_LOWER = PKDict(_components())
    _LABEL_TO_COL = PKDict(_cols())
    _VALID_COLS = PKDict({c.name: c for c in _LABEL_TO_COL.values()})


# _COMPONENTS generated from
# https://nds.iaea.org/relnsd/v1/data?fields=ground_states&nuclides=all
#
# from pykern.pkcollections import PKDict
# import csv
#
# _CENTURY = 100. * 365 * 24 * 60 * 60
#
# rv = PKDict(elements=set(), nuclides=set())
# with open('livechart.csv', 'r') as f:
#     first = True
#     for r in csv.reader(f):
#         if not r:
#             continue
#         if first:
#             first = False
#             continue
#         # num protons
#         if int(r[0]) > 0:
#             rv.elements.add(r[2])
#         # half_life or from stephen:
#         # "Actually, there may be some short-lived lithium isotopes that may be embedded in 1st wall materials, so let’s include all the Lithiums"
#         if r[12] != "STABLE" and r[2] != "Li":
#             # half_life_sec
#             if r[16] in ("", "?") or float(r[16]) < _CENTURY:
#                 continue
#         rv.nuclides.add(r[2] + r[1])
#
# print(rv)
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
        "Ag60",
        "Ag62",
        "Al13",
        "Al14",
        "Am146",
        "Am148",
        "Ar18",
        "Ar20",
        "Ar21",
        "Ar22",
        "As42",
        "Au118",
        "B5",
        "B6",
        "Ba74",
        "Ba76",
        "Ba78",
        "Ba79",
        "Ba80",
        "Ba81",
        "Ba82",
        "Be5",
        "Be6",
        "Bi125",
        "Bi126",
        "Bk150",
        "Br44",
        "Br46",
        "C6",
        "C7",
        "C8",
        "Ca20",
        "Ca21",
        "Ca22",
        "Ca23",
        "Ca24",
        "Ca26",
        "Ca28",
        "Cd58",
        "Cd60",
        "Cd62",
        "Cd63",
        "Cd64",
        "Cd65",
        "Cd66",
        "Cd68",
        "Ce78",
        "Ce80",
        "Ce82",
        "Ce84",
        "Cf151",
        "Cf153",
        "Cl18",
        "Cl19",
        "Cl20",
        "Cm149",
        "Cm150",
        "Cm151",
        "Cm152",
        "Cm154",
        "Co32",
        "Cr26",
        "Cr28",
        "Cr29",
        "Cr30",
        "Cs78",
        "Cs80",
        "Cu34",
        "Cu36",
        "Dy88",
        "Dy90",
        "Dy92",
        "Dy94",
        "Dy95",
        "Dy96",
        "Dy97",
        "Dy98",
        "Er100",
        "Er102",
        "Er94",
        "Er96",
        "Er98",
        "Er99",
        "Eu88",
        "Eu90",
        "F10",
        "Fe28",
        "Fe30",
        "Fe31",
        "Fe32",
        "Fe34",
        "Ga38",
        "Ga40",
        "Gd86",
        "Gd88",
        "Gd90",
        "Gd91",
        "Gd92",
        "Gd93",
        "Gd94",
        "Gd96",
        "Ge38",
        "Ge40",
        "Ge41",
        "Ge42",
        "Ge44",
        "H0",
        "H1",
        "He1",
        "He2",
        "Hf102",
        "Hf104",
        "Hf105",
        "Hf106",
        "Hf107",
        "Hf108",
        "Hf110",
        "Hg114",
        "Hg116",
        "Hg118",
        "Hg119",
        "Hg120",
        "Hg121",
        "Hg122",
        "Hg124",
        "Ho96",
        "Ho98",
        "I74",
        "I76",
        "In64",
        "In66",
        "Ir114",
        "Ir116",
        "K20",
        "K21",
        "K22",
        "Kr42",
        "Kr44",
        "Kr45",
        "Kr46",
        "Kr47",
        "Kr48",
        "Kr50",
        "La80",
        "La81",
        "La82",
        "Li1",
        "Li2",
        "Li3",
        "Li4",
        "Li5",
        "Li6",
        "Li7",
        "Li8",
        "Li9",
        "Lu104",
        "Lu105",
        "Mg12",
        "Mg13",
        "Mg14",
        "Mn28",
        "Mn30",
        "Mo50",
        "Mo51",
        "Mo52",
        "Mo53",
        "Mo54",
        "Mo55",
        "Mo56",
        "Mo58",
        "N7",
        "N8",
        "Na12",
        "Nb50",
        "Nb51",
        "Nb52",
        "Nb53",
        "Nd82",
        "Nd83",
        "Nd84",
        "Nd85",
        "Nd86",
        "Nd88",
        "Nd90",
        "Ne10",
        "Ne11",
        "Ne12",
        "Ni30",
        "Ni31",
        "Ni32",
        "Ni33",
        "Ni34",
        "Ni35",
        "Ni36",
        "Np143",
        "Np144",
        "O10",
        "O8",
        "O9",
        "Os108",
        "Os110",
        "Os111",
        "Os112",
        "Os113",
        "Os114",
        "Os116",
        "P16",
        "Pa140",
        "Pb120",
        "Pb122",
        "Pb123",
        "Pb124",
        "Pb125",
        "Pb126",
        "Pd56",
        "Pd58",
        "Pd59",
        "Pd60",
        "Pd61",
        "Pd62",
        "Pd64",
        "Po125",
        "Pr82",
        "Pt112",
        "Pt114",
        "Pt116",
        "Pt117",
        "Pt118",
        "Pt120",
        "Pu145",
        "Pu146",
        "Pu148",
        "Pu150",
        "Ra138",
        "Rb48",
        "Rb50",
        "Re110",
        "Re112",
        "Rh58",
        "Ru52",
        "Ru54",
        "Ru55",
        "Ru56",
        "Ru57",
        "Ru58",
        "Ru60",
        "S16",
        "S17",
        "S18",
        "S20",
        "Sb70",
        "Sb72",
        "Sc24",
        "Se40",
        "Se42",
        "Se43",
        "Se44",
        "Se45",
        "Se46",
        "Se48",
        "Si14",
        "Si15",
        "Si16",
        "Si18",
        "Sm82",
        "Sm84",
        "Sm85",
        "Sm86",
        "Sm87",
        "Sm88",
        "Sm90",
        "Sm92",
        "Sn62",
        "Sn64",
        "Sn65",
        "Sn66",
        "Sn67",
        "Sn68",
        "Sn69",
        "Sn70",
        "Sn72",
        "Sn74",
        "Sn76",
        "Sr46",
        "Sr48",
        "Sr49",
        "Sr50",
        "Ta108",
        "Tb93",
        "Tb94",
        "Tc54",
        "Tc55",
        "Tc56",
        "Te68",
        "Te70",
        "Te71",
        "Te72",
        "Te73",
        "Te74",
        "Te76",
        "Te78",
        "Th139",
        "Th140",
        "Th142",
        "Ti24",
        "Ti25",
        "Ti26",
        "Ti27",
        "Ti28",
        "Tl122",
        "Tl124",
        "Tm100",
        "U141",
        "U142",
        "U143",
        "U144",
        "U146",
        "V27",
        "V28",
        "W106",
        "W108",
        "W109",
        "W110",
        "W112",
        "Xe70",
        "Xe72",
        "Xe74",
        "Xe75",
        "Xe76",
        "Xe77",
        "Xe78",
        "Xe80",
        "Xe82",
        "Y50",
        "Yb100",
        "Yb101",
        "Yb102",
        "Yb103",
        "Yb104",
        "Yb106",
        "Yb98",
        "Zn34",
        "Zn36",
        "Zn37",
        "Zn38",
        "Zn40",
        "Zr50",
        "Zr51",
        "Zr52",
        "Zr53",
        "Zr54",
        "Zr56",
    },
)

_init()
