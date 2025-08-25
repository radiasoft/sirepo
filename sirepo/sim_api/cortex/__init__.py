"""api for cortex

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import asyncio
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
        except TimeoutError:
            pkdlog("timed out secs={} req_data={}", _ACTION_TIMEOUT, a)
            # TODO(robnagler) is there a better way?
            raise

    def cortex_db_done(self, result):
        self.__loop.call_soon_threadsafe(self.__result.put_nowait, result)


class _CortexDb(pykern.pkasyncio.ActionLoop):

    def action_delete_material(self, arg, uid):
        sirepo.template.cortex_sql_db.delete_material(
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
            return "\n".join(p.errors)
        try:
            sirepo.sim_api.cortex.material_db.insert_material(parsed=p.result, uid=uid)
        except sirepo.sim_api.cortex.material_db.Error as e:
            return str(e.args[0])
        return PKDict(material_name=p.result.material_name)

    def action_list_materials(self, arg, uid):
        return PKDict(rows=sirepo.sim_api.cortex.material_db.list_materials(uid=uid))

    def _dispatch_action(self, method, arg):
        qcall = arg.qcall
        try:
            r = method(arg, uid=qcall.auth.logged_in_user())
            if isinstance(r, PKDict):
                r = qcall.reply_ok(PKDict(op_result=r))
            elif isinstance(r, str):
                r = qcall.reply_error(r)
            else:
                raise AssertionError(
                    f"invalid action result type={type(r)} method={method}"
                )
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
