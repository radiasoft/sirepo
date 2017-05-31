# -*- coding: utf-8 -*-
u"""Database utilities

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


def upgrade():
    """Upgrade the database"""
    import copy
    from pykern import pkio
    from sirepo import simulation_db

    to_rename = []
    for d in pkio.walk_tree(simulation_db.user_dir_name()):
        if d.basename == 'warp' and d.check(dir=True):
            to_rename.append((d, d.new(basename='warppba')))
    for s, d in to_rename:
        s.rename(d)
