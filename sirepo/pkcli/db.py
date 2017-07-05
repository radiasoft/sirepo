# -*- coding: utf-8 -*-
u"""Database utilities

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


def upgrade():
    """Upgrade the database"""
    from pykern import pkio
    from sirepo import simulation_db
    from sirepo import server
    import re

    def _inc(m):
        return m.group(1) + str(int(m.group(2)) + 1)

    server.init()
    for d in pkio.sorted_glob(simulation_db.user_dir_name().join('*/warppba')):
        for fn in pkio.sorted_glob(d.join('*/sirepo-data.json')):
            with open(str(fn)) as f:
                t = f.read()
            for old, new in (
                ('"WARP example laser simulation"', '"Laser-Plasma Wakefield"'),
                ('"Laser Pulse"', '"Laser-Plasma Wakefield"'),
                ('"WARP example electron beam simulation"', '"Electron Beam"'),
            ):
                if not old in t:
                    continue
                t = t.replace(old, new)
                t = re.sub(r'(simulationSerial":\s+)(\d+)', _inc, t)
                break
            with open(str(fn), 'w') as f:
                f.write(t)
