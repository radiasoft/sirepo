"""cortex execution template.

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo.template import template_common
import pykern.pkio
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.template.cortex_sql_db
import sirepo.template.cortex_xlsx

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        return PKDict(
            percentComplete=0,
            frameCount=0,
        )
    return PKDict(
        percentComplete=100,
        frameCount=1,
    )


def stateful_compute_import_file(data, **kwargs):
    return _import_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        "print('done')",
    )


def _import_file(data, qcall=None):
    p = sirepo.template.cortex_xlsx.Parser(
        _SIM_DATA.lib_file_abspath(data.args.lib_file, qcall=qcall)
    )
    if p.errors:
        return PKDict(error="\n".join(p.errors))
    try:
        sirepo.template.cortex_sql_db.insert_material(p.result, qcall=qcall)
    except sirepo.template.cortex_sql_db.Error as e:
        return PKDict(error=e.args[0])
    rv = sirepo.simulation_db.default_data(SIM_TYPE)
    rv.models.simulation.name = p.result.material_name
    # TODO(robnagler) define in schema?
    rv.models.parsed_material = (p.result,)
    return PKDict(imported_data=rv)
