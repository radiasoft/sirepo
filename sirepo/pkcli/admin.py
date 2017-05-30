# -*- coding: utf-8 -*-
u"""?

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


def purge_users(days=180, confirm=False):
    """Remove old users from db which have not registered.

    Args:
        days (int): maximum days of untouched files (old is mtime > days)
        confirm (bool): delete the directories if True (else don't delete) [False]

    Returns:
        list: directories removed (or to remove if confirm)
    """
    from pykern import pkio
    from sirepo import server
    from sirepo import simulation_db
    import datetime

    days = int(days)
    assert days >= 1, \
        '{}: days must be a positive integer'
    server.init()
    uids = server.all_uids()
    now = datetime.datetime.utcnow()
    to_remove = []
    for d in pkio.sorted_glob(simulation_db.user_dir_name('*')):
        if simulation_db.uid_from_dir_name(d) in uids:
            continue
        for f in pkio.walk_tree(d):
            if (now - now.fromtimestamp(f.mtime())).days <= days:
                break
        else:
            to_remove.append(d)
    if confirm:
        pkio.unchecked_remove(*to_remove)
    return to_remove
