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

    server.init()
    to_rename = []
    for d in pkio.sorted_glob(simulation_db.user_dir_name().join('*/warp')):
        d.rename(d.new(basename='warppba'))
