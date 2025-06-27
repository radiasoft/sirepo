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


def stateful_compute_import_file(data):
    return _import_file(data)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        "print('done')",
    )


def _import_file(data):
    def _write_db(result):
        f = "materials.sqlite"
        p = _SIM_DATA.lib_file_exists(f) or pykern.pkio.py_path(f)
        sirepo.template.cortex_sql_db.add_parsed_material(p, result)
        _SIM_DATA.lib_file_write(f, p)

    f = "material.xlsx"
    pykern.pkio.write_binary(
        f,
        data.args.pknested_get("import_file_arguments.file_as_bytes"),
    )
    p = sirepo.template.cortex_xlsx.Parser(f)
    if p.errors:
        return PKDict(error="\n".join(p.errors))
    #    _write_db(p.result)
    rv = sirepo.simulation_db.default_data(SIM_TYPE)
    rv.models.simulation.name = p.result.material_name
    # TODO(robnagler) define in schema?
    rv.models.parsed_material = (p.result,)
    return PKDict(imported_data=rv)
