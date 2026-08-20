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
import re
import sirepo.pkcli.cortex
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
    elements = _aggregate_elements(
        sirepo.pkcli.cortex._convert_ao_to_wo(materials).m.components
    )
    remainder_element = max(elements, key=lambda e: elements[e].target_pct)
    composition = PKDict(
        (
            e,
            PKDict(wt=v.target_pct, type=v.type),
        )
        for e, v in elements.items()
        if e != remainder_element
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
