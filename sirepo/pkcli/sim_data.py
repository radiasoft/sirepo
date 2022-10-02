# -*- coding: utf-8 -*-
"""simulation data manipulations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdpretty
import pykern.pkcollections
import pykern.pkconfig
import pykern.pkio
import sirepo.feature_config
import sirepo.simulation_db
import tempfile


def fixup_package_data_json():
    def _is_valid(path):
        return any(
            x
            for x in sirepo.feature_config.cfg().sim_types
            if pykern.pkio.py_path().bestrelpath(f).startswith(x + "/")
        )

    i = 0
    for f in pykern.pkio.sorted_glob("*/examples/*.json") + pykern.pkio.sorted_glob(
        "*/default-data.json"
    ):
        if not _is_valid(f):
            continue
        pkdlog(f)
        d = sirepo.simulation_db.json_load(f)
        if f.basename != "default-data.json":
            d.models.pksetdefault(simulation=PKDict).simulation.isExample = True
        d = sirepo.simulation_db.fixup_old_data(d, force=True)[0]
        pykern.pkcollections.unchecked_del(
            d.models.simulation,
            "lastModified",
            "simulationId",
            "simulationSerial",
        )
        d.pkdel("version")
        d.models.pkdel("simulationStatus")
        for m in d.models.values():
            if isinstance(m, dict):
                m.pkdel("startTime")
        sirepo.simulation_db.write_json(f, d)
        i += 1
    if i <= 0:
        pykern.pkcli.command_error(
            "no examples found; must be run from package_data/template"
        )
