# -*- coding: utf-8 -*-
u"""simulation data manipulations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

def fixup_package_data_json():
    import pykern.pkconfig
    import tempfile

    pykern.pkconfig.reset_state_for_testing(
        dict(SIREPO_SIMULATION_DB_TMP_DIR=tempfile.mkdtemp()),
    )

    from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdpretty
    from pykern.pkcollections import PKDict
    import pykern.pkcollections
    import pykern.pkio
    import sirepo.auth
    import sirepo.feature_config
    import sirepo.server
    import sirepo.simulation_db
    import sirepo.util

    i = 0
    for f in pykern.pkio.sorted_glob(
        pykern.pkio.py_path().join('*', 'examples', '*.json'),
    ) + pykern.pkio.sorted_glob(
        pykern.pkio.py_path().join('*', 'default-data.json'),
    ):
        if not any(x for x in sirepo.feature_config.cfg().sim_types if x in str(f)):
            continue
        pkdlog(f)
        d = sirepo.simulation_db.json_load(f)
        if f.basename != 'default-data.json':
            d.models.pksetdefault(simulation=PKDict).simulation.isExample = True
        d = sirepo.simulation_db.fixup_old_data(d, force=True)[0]
        pykern.pkcollections.unchecked_del(
            d.models.simulation,
            'simulationSerial',
            'simulationId',
        )
        d.pkdel('version')
        d.models.pkdel('simulationStatus')
        for m in d.models.values():
            if isinstance(m, dict):
                m.pkdel('startTime')
        sirepo.util.json_dump(d, path=f, pretty=True)
        i += 1
    if i <= 0:
        pykern.pkcli.command_error('must be run from package_data/template')
