"""api for cortex

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import asyncio
import asyncio.exceptions
import pykern.pkasyncio
import sirepo.quest
import sirepo.sim_api.cortex.material_db
import sirepo.sim_api.cortex.material_xlsx
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, _ = sirepo.sim_data.template_globals(sim_type="cortex")

#: These operations are all fast. There shouldn't be much contention
_ACTION_TIMEOUT = 20

_EXT = ".xlsx"

_action_loop = None


def init_apis(**kwargs):
    global _action_loop

    sirepo.sim_api.cortex.material_db.init_from_api()
    _action_loop = _CortexDb()


class API(sirepo.quest.API):

    @sirepo.quest.Spec("require_plan", sim_type=f"SimType const={SIM_TYPE}")
    async def api_cortexDb(self):
        a = self.parse_post(type=SIM_TYPE).req_data
        self.__loop = asyncio.get_event_loop()
        self.__result = asyncio.Queue()
        try:
            _action_loop.action(a.op_name, a.op_args.pkupdate(qcall=self))
            r = await asyncio.wait_for(self.__result.get(), timeout=_ACTION_TIMEOUT)
            self.__result.task_done()
            if isinstance(r, Exception):
                raise r
            return r
        except asyncio.exceptions.TimeoutError:
            pkdlog("timed out secs={} req_data={}", _ACTION_TIMEOUT, a)
            # TODO(robnagler) is there a better way?
            raise

    def cortex_db_done(self, result):
        self.__loop.call_soon_threadsafe(self.__result.put_nowait, result)


class _CortexDb(pykern.pkasyncio.ActionLoop):

    _SOURCE_DESC = PKDict(
        EXP="experiment",
        PP="predictive physics model",
        NOM="nominal (design target) value",
        ML="maching learning",
        DFT="Density Functional Theory",
    )

    def action_delete_material(self, arg, uid):
        sirepo.sim_api.cortex.material_db.delete_material(
            material_id=arg.material_id, uid=uid
        )
        return PKDict()

    def action_insert_material(self, arg, uid):
        def _save():
            f = arg.qcall.sreq.form_file_get()
            if not f.filename.lower().endswith(_EXT):
                arg.qcall.reply_error(f"invalid file='{f.filename}' must be '{_EXT}'")
            p = _SIM_DATA.lib_file_name_with_type(
                sirepo.srtime.utc_now().strftime("%Y%m%d%H%M%S") + _EXT,
                "import-material",
            )
            _SIM_DATA.lib_file_write(p, f.as_bytes(), qcall=arg.qcall)
            return _SIM_DATA.lib_file_abspath(p, qcall=arg.qcall)

        p = sirepo.sim_api.cortex.material_xlsx.Parser(_save())
        if p.errors:
            return PKDict(error=p.errors)
        try:
            return sirepo.sim_api.cortex.material_db.insert_material(
                parsed=p.result, uid=uid
            )
        except sirepo.sim_api.cortex.material_db.Error as e:
            return PKDict(error=[PKDict(msg=str(e.args[0]))])

    def action_list_materials(self, arg, uid):
        return PKDict(rows=sirepo.sim_api.cortex.material_db.list_materials(uid=uid))

    def action_material_detail(self, arg, uid):
        try:
            r = sirepo.sim_api.cortex.material_db.material_detail(arg.material_id, uid)
        except pykern.sql_db.NoRows:
            raise sirepo.util.NotFound("Material not found")
        return PKDict(detail=self._format_material(r))

    def _destroy(self):
        pass

    def _dispatch_action(self, method, arg):
        qcall = arg.qcall
        try:
            r = method(arg, uid=qcall.auth.logged_in_user())
            if not isinstance(r, PKDict):
                raise AssertionError(
                    f"invalid action result type={type(r)} method={method}"
                )
            if e := r.get("error"):
                r = qcall.reply_error(e)
            else:
                r = qcall.reply_ok(PKDict(op_result=r))
        except Exception as e:
            pkdlog(
                "returning error={} method={} arg={} stack={}",
                e,
                method,
                arg,
                pkdexc(simplify=True),
            )
            r = e
        qcall.cortex_db_done(r)
        return None

    def _format_material(self, material):

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
                    "Homogenized Divertor": _to_yes_no(
                        material.is_homogenized_divertor
                    ),
                }
            ),
            components=material.components,
            composition=_find_property(material.properties, "composition"),
            composition_density=_find_property(
                material.properties, "composition_density"
            ),
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
                            f"{p.source}, {self._SOURCE_DESC[p.source]}"
                            if p.source in self._SOURCE_DESC
                            else p.source
                        ),
                        Pointer=p.pointer,
                        Comments=p.comments,
                    ),
                )
        return res
