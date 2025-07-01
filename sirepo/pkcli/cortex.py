"""utilities for cortex

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import csv
import io
import requests

_CENTURY = 100.0 * 365 * 24 * 60 * 60


def gen_components():

    def _livechart_csv():
        r = requests.get(
            "https://nds.iaea.org/relnsd/v1/data?fields=ground_states&nuclides=all"
        )
        r.raise_for_status()
        return io.StringIO(r.text)

    def _parse():
        rv = PKDict(elements=set(), nuclides=set())
        first = True
        for r in csv.reader(_livechart_csv()):
            if not r:
                continue
            if first:
                first = False
                continue
            # num protons
            z = int(r[0])
            if z <= 0:
                continue
            symbol = r[2]
            rv.elements.add(symbol)
            # half_life or from stephen:
            # "Actually, there may be some short-lived lithium isotopes that may be embedded in 1st wall materials, so let’s include all the Lithiums"
            if r[12] != "STABLE" and symbol != "Li":
                # half_life_sec
                if r[16] in ("", "?") or float(r[16]) < _CENTURY:
                    continue
            rv.nuclides.add(r[2] + str(int(r[1]) + z))
        return rv

    def _to_str(components):
        rv = "_COMPONENTS = PKDict(\n"
        i = " " * 4
        j = i * 2
        for c in sorted(components.keys()):
            rv += i + c + "={\n"
            for n in sorted(components[c]):
                rv += f'{j}"{n}",\n'
            rv += i + "},\n"
        return rv + ")\n"

    return _to_str(_parse())
