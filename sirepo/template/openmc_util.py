"""OpenMC utilities.

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import openmc.data
import re


def wo_to_ao(wo):
    """Converts weight percentage to atomic weight percentage for collection of elements and/or nuclides"""
    weight_sum = 0
    weight = PKDict()
    for e in wo:
        if re.search(r"\d", e):
            # Nuclide
            try:
                w = openmc.data.atomic_mass(e)
            except KeyError as err:
                raise ValueError(f"Unknown nuclide: {e}")
        else:
            # Element
            if e not in openmc.data.ATOMIC_NUMBER:
                raise ValueError(f"Unknown element: {e}")
            # may raise ValueError: No naturally-occuring isotopes for element
            w = openmc.data.atomic_weight(e)
        weight[e] = wo[e] * openmc.data.AVOGADRO / w
        weight_sum += weight[e]

    ao = PKDict()
    for e in wo:
        ao[e] = 100.0 * weight[e] / weight_sum
    return ao
