# -*- coding: utf-8 -*-
u"""simulation data manipulations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdpretty

def fixup_all_examples():
    import pykern.pkio
    import sirepo.feature_config
    import sirepo.simulation_db
    import sirepo.util

    p = pykern.pkio.py_path()
    for t in sorted(sirepo.feature_config.cfg().sim_types):
        x = pykern.pkio.sorted_glob(p.join(t, 'examples', '*.json'))
        if not x:
            pykern.pkcli.command_error('must be run from package_data/template')
        for f in x:
            d = sirepo.simulation_db.fixup_old_data(
                sirepo.simulation_db.json_load(f),
                force=True,
            )[0]
            d.models.simulation.pkdel('simulationSerial')
            d.models.simulation.pkdel('simulationId')
            sirepo.util.json_dump(d, path=f, pretty=True)
            pkdlog(f.basename)
