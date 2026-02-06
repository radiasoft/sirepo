"""api for cortex

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import asyncio
import asyncio.exceptions
import pykern.pkasyncio
import re
import sirepo.quest
import sirepo.sim_api.cortex.material_db
import sirepo.sim_api.cortex.material_xlsx
import sirepo.sim_data
import sirepo.simulation_db

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
                # TODO(pjm): Raising an exception caused a timeout and no response returned to the client
                #           instead it returns a general system-error message
                # raise r
                return PKDict(
                    error=[
                        PKDict(
                            value="An internal error occurred. Please contact support@sirepo.com",
                        ),
                    ],
                )
            return r
        except asyncio.exceptions.TimeoutError:
            pkdlog("timed out secs={} req_data={}", _ACTION_TIMEOUT, a)
            # TODO(robnagler) is there a better way?
            raise

    @sirepo.quest.Spec("require_plan", sim_type=f"SimType const={SIM_TYPE}")
    async def api_cortexSim(self):
        # TODO(pjm): does this need a asyncio loop also?
        a = self.parse_post(type=SIM_TYPE).req_data
        return await getattr(self, f"_sim_{a.op_name}")(a.op_args)

    def cortex_db_done(self, result):
        self.__loop.call_soon_threadsafe(self.__result.put_nowait, result)

    async def _sim_delete(self, args):
        s = await _find_sim(self, args.material_id)
        if not len(s):
            return PKDict()
        await self.call_api(
            "deleteSimulation",
            body=PKDict(simulationType=SIM_TYPE, simulationId=s[0].simulationId),
        )
        return PKDict()

    async def _sim_runTile(self, args):
        s = await self._update_material_sim(args.material_id)
        await self.call_api(
            "runSimulation",
            body=PKDict(
                forceRun=True,
                report="tileAnimation",
                models=s.models,
                simulationType=SIM_TYPE,
                simulationId=s.models.simulation.simulationId,
            ),
        )
        return PKDict()

    async def _sim_sync(self, args):
        return PKDict(
            simulationId=(
                await self._update_material_sim(args.material_id)
            ).models.simulation.simulationId,
        )

    async def _update_material_sim(self, material_id):
        """Get/create the associated Sirepo sim for the material_id and update
        the sirepo-data.json from values in the database.
        """

        async def _update_sim(sim, material_id):
            m = (
                (
                    await self.call_api(
                        "cortexDb",
                        body=PKDict(
                            op_name="material_detail",
                            op_args=PKDict(
                                material_id=material_id,
                            ),
                        ),
                    )
                )
                .content_as_object()
                .op_result.detail
            )
            sim.models.material.pkupdate(
                name=m.name,
                density=float(re.sub(r"\s.*", "", m.density)),
                percent_type="ao" if m.is_atom_pct else "wo",
                components=[
                    PKDict(
                        component_type=(
                            "nuclide"
                            if re.search(r"\d", c.material_component_name)
                            else "element"
                        ),
                        component=c.material_component_name,
                        percent=c.target_pct,
                    )
                    for c in m.components
                ],
            )
            return sirepo.simulation_db.save_simulation_json(
                sim, fixup=True, qcall=self
            )

        s = await _find_sim(self, material_id)
        sim = None
        if len(s):
            sim = sirepo.simulation_db.open_json_file(
                SIM_TYPE, sid=s[0].simulationId, qcall=self
            )
        else:
            d = sirepo.simulation_db.default_data(SIM_TYPE)
            d.models.simulation.name = str(material_id)
            sim = sirepo.simulation_db.save_new_simulation(d, qcall=self)
        return await _update_sim(sim, material_id)


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
        # TODO(pjm): need to delete the Sirepo sim associated with the material_id
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
                "returning error={} method={} stack={}",
                e,
                method,
                pkdexc(simplify=True),
            )
            r = e
        qcall.cortex_db_done(r)
        return None

    def _format_material(self, material):

        # these were required for old xls imports, now they are brought in with independent_variables
        _OLD_PROPERTY_COLUMNS = PKDict(
            temperature_k="Temperature [K]",
            neutron_fluence_1_cm2="Neutron Fluence [1/cm²]",
        )

        def _add_doi(prop):
            if prop.doi_or_url is None:
                t = None
                u = None
            elif prop.doi_or_url.lower().startswith("http"):
                t = "URL"
                u = prop.doi_or_url
            else:
                t = "DOI"
                u = f"https://doi.org/{prop.doi_or_url}"
            prop.doi = PKDict(
                type=t,
                url=u,
                linkText=prop.doi_or_url,
                rows=PKDict(
                    Source=(
                        f"{prop.source}, {self._SOURCE_DESC[prop.source]}"
                        if prop.source in self._SOURCE_DESC
                        else prop.source
                    ),
                    Pointer=prop.pointer,
                    Comments=prop.comments,
                ),
            )

        def _add_property_values(prop):
            def _has_column_value(rows, key):
                for r in rows:
                    if r[k]:
                        return True
                return False

            prop.valueHeadings = PKDict(
                value="Value"
                + (f" [{prop.property_unit}]" if prop.property_unit else ""),
                uncertainty="Uncertainty",
            )
            for k in prop.vals[0]:
                if k in prop.valueHeadings or k.endswith("_id"):
                    continue
                if _has_column_value(prop.vals, k):
                    prop.valueHeadings[k] = _OLD_PROPERTY_COLUMNS.get(k, k)

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
                    "Availability Factor": (
                        f"{material.availability_factor}%"
                        if material.availability_factor
                        else ""
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
            if "vals" in p and len(p.vals):
                _add_property_values(p)
            if p.doi_or_url or p.comments:
                _add_doi(p)
        return res


async def _find_sim(api, material_id):
    return (
        await api.call_api(
            "listSimulations",
            body=PKDict(
                simulationType=SIM_TYPE,
                search=PKDict({"simulation.name": str(material_id)}),
            ),
        )
    ).content_as_object()
