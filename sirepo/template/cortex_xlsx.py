"""?

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pandas


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

class Parser:
    def __init__(self, path):
        self.

    def _tuples(path, sheet=None):
        d = _open(path, sheet)
        # itertuples includes row number as first element
        return tuple((tuple(_str(c, r) for c in r[1:]) for r in d.itertuples()))




def _open(path, sheet):
    try:
        e = path.ext.lower()
        if e == ".csv":
            with codecs.open(str(path), "rb", "cp1252") as f:
                return pandas.read_csv(f, header=None)
        d = pandas.read_excel(str(path), sheet_name=sheet)
        c = d.shape[1]
        # Just in case pandas keeps file open, force garbage collect
        d = None
        # must specify exact number of converters so need to open twice
        return pandas.read_excel(
            str(path),
            sheet_name=sheet,
            converters={z: str for z in range(c)},
        )
    except Exception:
        pkdlog("ERROR path={} sheet={}", path, sheet)
        raise


def _str(v, row):
    if isinstance(v, str):
        # Dates get a time stamp sometimes
        return v.replace(" 00:00:00", "")
    if isinstance(v, float):
        if math.isnan(v):
            return ""
        return str(v)
    if isinstance(v, int):
        return str(v)
    raise RuntimeError(f"value={v} has unhandled type={type(v)}")
