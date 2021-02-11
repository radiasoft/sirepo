# -*- coding: utf-8 -*-
u"""db configuration

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import os.path
import sys

#: Relative to current directory only in dev mode
_DEFAULT_ROOT = 'run'

#: Configured root either by server_set_root or cfg
_root = None

#: internal config (always use `root`)
_cfg = None

#: subdir of where proprietary codes live
_PROPRIETARY_CODE_DIR = 'proprietary_code'


#: where job db is stored under srdb.root
_SUPERVISOR_DB_SUBDIR = 'supervisor-job'


def proprietary_code_dir(sim_type):
    """Directory for proprietary code binaries

    Args:
        sim_type (str): not validated code name
    """
    return root().join(_PROPRIETARY_CODE_DIR, sim_type)


def root():
    return _root or _init_root()


def supervisor_db_dir():
    """Directory for supervisor job db"""

    return root().join(_SUPERVISOR_DB_SUBDIR)


def _init_root():
    global _cfg, _root

    def _cfg_root(v):
        """Config value or root package's parent or cwd with `_DEFAULT_ROOT`"""
        if not os.path.isabs(v):
            pkconfig.raise_error(f'{v}: SIREPO_SRDB_ROOT must be absolute')
        if not os.path.isdir(v):
            pkconfig.raise_error(f'{v}: SIREPO_SRDB_ROOT must be a directory and exist')
        return pkio.py_path(v)

    _cfg = pkconfig.init(
        root=(None, _cfg_root, 'where database resides'),
    )
    _root = _cfg.root
    if _root:
        return _root
    assert pkconfig.channel_in('dev'), \
        'SIREPO_SRDB_ROOT must be configured except in dev'
    r = pkio.py_path(
        sys.modules[pkinspect.root_package(_init_root)].__file__,
    ).dirpath().dirpath()
    # Check to see if we are in our dev directory. This is a hack,
    # but should be reliable.
    if not r.join('requirements.txt').check():
        # Don't run from an install directory
        r = pkio.py_path('.')
    _root = pkio.mkdir_parent(r.join(_DEFAULT_ROOT))
    return _root
