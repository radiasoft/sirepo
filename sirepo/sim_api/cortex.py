"""api for cortex

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.quest
import sirepo.sim_data
import sirepo.template.cortex_sql_db
import sirepo.template.cortex_xlsx


_SIM_DATA, SIM_TYPE, _ = sirepo.sim_data.template_globals(sim_type="cortex")


_EXT = ".xlsx"


class API(sirepo.quest.API):

    @sirepo.quest.Spec("require_plan", sim_type=f"SimType const={SIM_TYPE}")
    async def api_cortexDb(self):
        a = self.parse_post(type=SIM_TYPE).req_data
        return getattr(self, f"_cortext_db_{a.op_name}")(**a.op_args)

    def _cortext_db_delete_material(self, material_id):
        sirepo.template.cortex_sql_db.delete_material(self, material_id)
        return self.__reply_ok()

    def _cortext_db_insert_material(self):
        def _save():
            f = self.sreq.form_file_get()
            if not f.filename.lower().endswith(_EXT):
                self.reply_error(f"invalid file='{f.filename}' must be '{_EXT}'")
            p = _SIM_DATA.lib_file_name_with_type(
                sirepo.srtime.utc_now().strftime("%Y%m%d%H%M%S") + _EXT,
                "import-material",
            )
            _SIM_DATA.lib_file_write(p, f.as_bytes(), qcall=self)
            return _SIM_DATA.lib_file_abspath(p, qcall=self)

        p = sirepo.template.cortex_xlsx.Parser(_save())
        if p.errors:
            return self.reply_error("\n".join(p.errors))
        try:
            sirepo.template.cortex_sql_db.insert_material(parsed=p.result, qcall=self)
        except sirepo.template.cortex_sql_db.Error as e:
            return self.reply_error(e.args[0])
        return self.__reply_ok(material_name=p.result.material_name)

    def _cortext_db_list_materials(self):
        return self.__reply_ok(sirepo.template.cortex_sql_db.list_materials(self))

    def __reply_ok(self, op_result=None, **kwargs):
        return self.reply_ok(PKDict(op_result=op_result or PKDict(kwargs)))
