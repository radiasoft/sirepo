"""cortex execution template.

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
import pykern.sql_db
import re
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.template.cortex_sql_db
import sirepo.template.cortex_xlsx
import sirepo.util

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def stateful_compute_delete_material(data, **kwargs):
    sirepo.template.cortex_sql_db.delete_material(data.args.material_id)
    return PKDict()


def stateful_compute_list_materials(data, **kwargs):
    res = sirepo.template.cortex_sql_db.list_materials()
    for r in res:
        # convert python datetime to javascript datetime
        r.created *= 1000
    return PKDict(
        result=res,
    )


def stateful_compute_material_detail(data, **kwargs):
    try:
        return PKDict(
            result=_format_material(
                sirepo.template.cortex_sql_db.material_detail(data.args.material_id)
            ),
        )
    except pykern.sql_db.NoRows:
        raise sirepo.util.NotFound("Material not found")


def stateful_compute_import_file(data, **kwargs):
    return _import_file(data)


def _format_material(material):

    _SOURCE_DESC = PKDict(
        EXP="experiment",
        PP="predictive physics model",
        NOM="nominal (design target) value",
        ML="maching learning",
        DFT="Density Functional Theory",
    )

    def _find_property(properties, name):
        for p in properties:
            if p.property_name == name:
                return p
        return None

    def _to_yes_no(value):
        if value is None:
            return ""
        return "Yes" if value else "No"

    res = PKDict(
        name=material.material_name,
        density=f"{material.density_g_cm3} g/cm³",
        is_atom_pct=material.is_atom_pct,
        section1=PKDict(
            {
                "Material Type": (
                    "plasma-facing" if material.is_plasma_facing else "structural"
                ),
                "Structure": material.structure,
                "Microstructure Information": material.microstructure,
                "Processing": material.processing_steps,
            }
        ),
        section2=PKDict(
            {
                "Neutron Source": "D-T" if material.is_neutron_source_dt else "D-D",
                "Neutron Wall Loading": material.neutron_wall_loading,
                "Availability Factor": f"{material.availability_factor}%",
            }
        ),
        section3=PKDict(
            {
                "Bare Tile": _to_yes_no(material.is_bare_tile),
                "Homogenized WCLL": _to_yes_no(material.is_homogenized_wcll),
                "Homogenized HCPB": _to_yes_no(material.is_homogenized_hcpb),
                "Homogenized Divertor": _to_yes_no(material.is_homogenized_divertor),
            }
        ),
        components=material.components,
        composition=_find_property(material.properties, "composition"),
        composition_density=_find_property(material.properties, "composition_density"),
        properties=[
            p
            for p in material.properties
            if not p.property_name.startswith("composition")
        ],
    )
    for c in res.components:
        c.material_component_name = c.material_component_name.capitalize()
    for p in material.properties:
        p.valueHeadings = PKDict(
            value="Value" + (f" [{p.property_unit}]" if p.property_unit else ""),
            uncertainty="Uncertainty",
            temperature_k="Temperature [K]",
            neutron_fluence_1_cm2="Neutron Fluence [1/cm²]",
        )
        if "vals" in p and len(p.vals):
            for k in p.vals[0]:
                if k in p.valueHeadings or k.endswith("_id"):
                    continue
            p.valueHeadings[k] = k

        if p.doi_or_url:
            if p.doi_or_url.lower().startswith("http"):
                t = "URL"
                u = p.doi_or_url
            else:
                t = "DOI"
                u = f"https://doi.org/{p.doi_or_url}"
            p.doi = PKDict(
                type=t,
                url=u,
                linkText=p.doi_or_url,
                rows=PKDict(
                    Source=(
                        f"{p.source}, {_SOURCE_DESC[p.source]}"
                        if p.source in _SOURCE_DESC
                        else p.source
                    ),
                    Pointer=p.pointer,
                    Comments=p.comments,
                ),
            )
    return res


def _import_file(data):

    def _format_errors(errors):
        p = PKDict(
            col=r"\scol=(\d+)",
            row=r"\srow=(\d+)",
            sheet=r"\ssheet=(.*)",
            value=r"(invalid\s.*?=\w*\s)",
        )
        res = []
        sheet = None
        for line in errors:
            e = PKDict(
                line=line,
            )
            for f in p:
                m = re.search(p[f], line)
                if m:
                    e[f] = m[1]
                    line = re.sub(p[f], "", line)
            if line:
                e.msg = line
                if "value" in e:
                    e.value = re.sub(r"=$", "", e.value.strip())
                if "sheet" in e and e.sheet == sheet:
                    del e["sheet"]
                else:
                    sheet = e.get("sheet")
                res.append(e)
        return res

    p = sirepo.template.cortex_xlsx.Parser(
        _SIM_DATA.lib_file_abspath(data.args.lib_file)
    )
    if p.errors:
        return PKDict(error=_format_errors(p.errors))
    try:
        sirepo.template.cortex_sql_db.insert_material(p.result)
    except sirepo.template.cortex_sql_db.Error as e:
        return PKDict(error=_format_errors([e.args[0]]))
    rv = sirepo.simulation_db.default_data(SIM_TYPE)
    rv.models.simulation.name = p.result.material_name
    # TODO(robnagler) define in schema?
    rv.models.parsed_material = (p.result,)
    return PKDict(imported_data=rv)
