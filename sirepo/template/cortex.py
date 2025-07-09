"""cortex execution template.

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.template.cortex_sql_db
import sirepo.template.cortex_xlsx

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def stateful_compute_cortex_db(data, **kwargs):
    if data.args.api_name == "list_materials":
        return PKDict(
            api_result=sirepo.template.cortex_sql_db.list_materials(),
        )
    raise AssertionError("Unhandled api_name: {}", data.args.api_name)


def stateful_compute_import_file(data, **kwargs):
    return _import_file(data)


def _import_file(data):
    p = sirepo.template.cortex_xlsx.Parser(
        _SIM_DATA.lib_file_abspath(data.args.lib_file)
    )
    if p.errors:
        return PKDict(error="\n".join(p.errors))
    try:
        sirepo.template.cortex_sql_db.insert_material(p.result)
    except sirepo.template.cortex_sql_db.Error as e:
        return PKDict(error=e.args[0])
    rv = sirepo.simulation_db.default_data(SIM_TYPE)
    rv.models.simulation.name = p.result.material_name
    # TODO(robnagler) define in schema?
    rv.models.parsed_material = (p.result,)
    return PKDict(imported_data=rv)
