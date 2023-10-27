# -*- coding: utf-8 -*-
"""Simulation run utilities.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
import contextlib
import sirepo.simulation_db

#: created under dir
_TMP_DIR = "tmp"


def cache_dir(basename, qcall=None):
    """Creates a directory in the user's temporary directory.

    Unlike `tmp_dir`, this (possibly new) directory will not be deleted automatically.

    Args:
        basename (str): sub-directory to use, need not be unique
        qcall (sirepo.quest.API): request state
    Returns:
        py.path: path to newly created directory
    """
    return pkio.mkdir_parent(
        sirepo.simulation_db.user_path(qcall=qcall, check=True).join(_TMP_DIR, basename)
    )


@contextlib.contextmanager
def tmp_dir(chdir=False, qcall=None):
    """Generates new, temporary directory

    Args:
        chdir (bool): if true, will save_chdir
        qcall (sirepo.quest.API): request state
    Returns:
        py.path: directory to use for temporary work
    """
    d = None
    try:
        d = sirepo.simulation_db.mkdir_random(
            sirepo.simulation_db.user_path(qcall=qcall, check=True).join(_TMP_DIR)
        )["path"]
        pkio.unchecked_remove(d)
        pkio.mkdir_parent(d)
        if chdir:
            with pkio.save_chdir(d):
                yield d
        else:
            yield d
    finally:
        if d:
            pkio.unchecked_remove(d)
