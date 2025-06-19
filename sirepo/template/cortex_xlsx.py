"""?

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pandas
import pykern.pkcompat


"""
k
Operating Conditions

Neutron Source        D-T fusion        (options: D-T, D-D)

Neutron Wall Loading        1 MW/m2        (options: ITER, DEMO, ...)
        "NeutronWallLoadingName": [
            ["ITER", "ITER 0.57"],
            ["DEMO", "DEMO 1.04"],
            ["OTHER", "Other"]

Availability Factor        25%


Multi-Layer Geometry Options
Select the geometry scenarios you would like to simulate for your material.

Bare Tile                YES
Homogenized WCLL                NO
Homogenized HCPB                YES
Homogenized divertor                NO

Material Type                plasma-facing

Material Name

Name        Simple One        Enter the name of your material for storage in the database.

Density        3.33        Enter the density of your material during in-service conditions.
Density Unit        g/cm3

Composition
Enter the composition of your material. The components of a material must ALL be given in weight % or ALL be given in atomic percent. Neutronics simulations will use the "target" value if provided. If the "target" value is not provided, the midpoint of the max/min range will be used, unless the "min" value is zero in which case the maximum is used (assuming a conservative approach for impurities). One element or nuclide can be indicated as "balance" in order to fill the remaining material components to 100% weight percent or 100% atomic percent.

        Weight %                        Atom %
        Element or Nuclide        Target        Min        Max        Target        Min        Max
        C        20
        Cr        5
        W        10
        Fe        65
"""

# Known list https://nds.iaea.org/relnsd/v1/data?fields=ground_states&nuclides=all

_COMPONENT_FROM_LOWER = None

_LABEL_TO_COL = PKDict({
    "name": "material_name",
    "density": "density_g_cm3",
    "neutron source": "neutron_source",
    "neutron wall loading": "neutron_wall_loading_mw_m2",
    "availability factor": "availability_factor",
    "bare tile": "is_bare_tile",
    "homogenized wcll": "is_homogenized wcll",
    "homogenized divertor": "is_homogenized_divertor",
    "material type": "is_plasma_facing",
})

class Parser:
    def __init__(self, path, qcall=None):
        self._parse_rows(reversed(self._read_and_split(path)))
# >         "Simple One",

# >         "Density",
# >         3.33,

# >         "Density Unit",
# >         "g/cm3",

# >         "Neutron Source",
# >         "dt",

# >         "Neutron Wall Loading",
# >         "iter",

# >         "Availability Factor",
# >         0.66,

# >         "Bare Tile",
# >         "n"

# >         "Homogenized WCLL",
# >         "yes"

# >         "Homogenized divertor",
# >         true

# >         "Material Type",
# >         "face"

    def _parse_rows(self, reversed_rows):
        def _col_availability_factor(value):
            return value

        def _col_density_g_cm3(value):
            return value

        def _col_is_bare_tile(value):
            return value

        def _col_is_homogenized wcll(value):
            return value

        def _col_homogenized_divertor(value):
            return value

        def _col_material_name(value):
            return value

        def _col_is_plasma_facing(value):
            return value

        def _col_neutron_source(value):
            return value

        def _col_neutron_wall_loading_mw_m2(value):
            return value

        def _dispatch(label, value, row, reversed_rows):
            if x := _LABEL_TO_COL.get(label):
                e = _dispatch(x, value)
            elif "nuclide" in label:
                e = _parse_components(reversed_rows)
            else:
                e = _maybe_error(r)
            if e:
                errors
        while r := next(reversed_rows):
            if len(r) >= 2 and r[0]:
                _dispatch(r[0].lower(), r[1], r, reversed_rows)



#         "Weight %",
#         NaN,
#         NaN,
#         "Atom %",
#         NaN,
#         NaN
#         NaN,
#         "Element or Nuclide",
#         "Target",
#         "Min",
#         "Max",
#         "Target",
#         "Min",
#         "Max"

    def _read_and_split(self, path):
        n = None
        try:
            for n, s in pandas.read_excel(
                str(path), header=None, sheet_name=None
            ).items():
                for r in s.itertuples(index=False):
                    yield list(r)
        except Exception:
            pkdlog("ERROR path={} sheet={}", path, n)
            raise

def _init():
    def _iter():
        for x in "elements", "nuclides":
            for y in _COMPONENTS[x]:
                yield y.lower(), y

    global _COMPONENT_FROM_LOWER
    _COMPONENT_FROM_LOWER = PKDict(_convert())


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

# https://nds.iaea.org/relnsd/v1/data?fields=ground_states&nuclides=all
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
