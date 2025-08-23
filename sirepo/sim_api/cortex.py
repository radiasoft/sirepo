"""api for cortex

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.template.cortex_sql_db
import sirepo.quest
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, _ = sirepo.sim_data.template_globals(sim_type="cortex")


class API(sirepo.quest.API):

    @sirepo.quest.Spec("require_plan", sim_type=f"SimType const={SIM_TYPE}")
    async def api_cortexDb(self):
        a = self.parse_post(type=SIM_TYPE).req_data
        if a.op_name == "list_materials":
            return self.reply_ok(
                PKDict(
                    op_result=pkdp(sirepo.template.cortex_sql_db.list_materials(self))
                ),
            )
        if a.op_name == "delete_material":
            sirepo.template.cortex_sql_db.delete_material(self, a.op_args.material_id)
            return PKDict()
        raise AssertionError("Unhandled op_name: {}", a.op_name)
