"""TEA manufacturing cost model material lookup for cortex

Only the cheap, database-touching part of the cost calculation lives here
(so it can run on the api server's single-threaded cortexDb action loop
without blocking it for long) - the actual tea evaluation and chart
rendering is CPU-heavy and runs via a statelessCompute call to
sirepo.template.cortex, which may execute on a different server and so
can't query this database itself; material_spec() returns a plain,
JSON-serializable dict with everything that side needs.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import openmc.data
import re
import sirepo.sim_api.cortex.material_db


def material_spec(material_id, is_public, uid):
    """A plain, JSON-serializable material spec for the tea cost model.

    Returns:
        PKDict: name, density, composition ({element: {wt, type}}),
            remainder_element, is_plasma_facing
    """
    d = sirepo.sim_api.cortex.material_db.material_detail(material_id, is_public, uid)
    materials = PKDict(
        m=PKDict(
            is_atom_pct=bool(d.is_atom_pct),
            components=PKDict(
                (
                    c.material_component_name.capitalize(),
                    PKDict(
                        target_pct=c.target_pct,
                        min_pct=c.min_pct,
                        max_pct=c.max_pct,
                    ),
                )
                for c in d.components
            ),
        ),
    )
    elements = _aggregate_elements(_convert_ao_to_wo(materials).m.components)
    remainder_element = max(elements, key=lambda e: elements[e].target_pct)
    composition = PKDict(
        (
            e,
            PKDict(wt=v.target_pct, type=v.type),
        )
        for e, v in elements.items()
        # tea rejects a non-positive wt, and a 0% element has no cost anyway
        if e != remainder_element and v.target_pct > 0
    )
    return PKDict(
        name=d.material_name,
        density=d.density_g_cm3,
        composition=composition,
        remainder_element=remainder_element,
        is_plasma_facing=bool(d.is_plasma_facing),
    )


def _aggregate_elements(components):
    """Sum isotope/nuclide-level composition entries (e.g. O16/O17/O18) up
    to their parent element (O) - tea's cost database only has plain
    element entries, and cost is inherently an element-level concept (you
    buy aluminum by the kg, not by isotope). An element is classified
    'alloy' if any of its isotopes was (min_pct != 0), else 'residual'."""
    rv = PKDict()
    for name, v in components.items():
        e = re.sub(r"\d+$", "", name)
        rv.pksetdefault(e, PKDict(target_pct=0.0, is_alloy=False))
        a = rv[e]
        a.target_pct += v.target_pct
        if v.min_pct != 0:
            a.is_alloy = True
    return PKDict(
        (e, PKDict(target_pct=a.target_pct, type="alloy" if a.is_alloy else "residual"))
        for e, a in rv.items()
    )


def _convert_ao_to_wo(materials):

    def _ao_to_wo(ao):
        weight_sum = 0
        mass = PKDict()
        weight = PKDict()
        for e in ao:
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
            mass[e] = w / openmc.data.AVOGADRO
            weight[e] = ao[e].target_pct * mass[e]
            weight_sum += weight[e]

        wo = PKDict()
        for e in ao:
            # ao to wo scale factor, independent of target_pct which may be 0
            f = 100.0 * mass[e] / weight_sum
            wo[e] = PKDict(
                target_pct=ao[e].target_pct * f,
                min_pct=None,
                max_pct=None,
            )
            if ao[e].max_pct is not None:
                if ao[e].min_pct is None:
                    wo[e].max_pct = wo[e].target_pct
                else:
                    wo[e].min_pct = ao[e].min_pct * f
                    wo[e].max_pct = ao[e].max_pct * f
        return wo

    for m in materials.values():
        if m.is_atom_pct:
            m.components = _ao_to_wo(m.components)
        del m["is_atom_pct"]
    return materials
