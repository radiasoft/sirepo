# -*- coding: utf-8 -*-
"""db configuration

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkinspect
from pykern import pkio
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import pykern.util
import os.path
import sys

#: Relative to current directory only in dev mode
_DEFAULT_ROOT = "run"

#: Configured root either by server_set_root or cfg
_root = None

#: internal config (always use `root`)
_cfg = None

#: subdir of where proprietary codes live
_PROPRIETARY_CODE_DIR = "proprietary_code"


#: where job db is stored under srdb.root
_SUPERVISOR_DB_SUBDIR = "supervisor-job"


def proprietary_code_dir(sim_type):
    """Directory for proprietary code binaries

    Args:
        sim_type (str): not validated code name
    """
    return root().join(_PROPRIETARY_CODE_DIR, sim_type)


def root():
    return _root or _init_root()


def supervisor_dir():
    """Directory for supervisor job db"""

    return root().join(_SUPERVISOR_DB_SUBDIR)


def _init_root():
    global _cfg, _root

    _cfg = pkconfig.init(
        root=(
            None,
            pykern.util.cfg_absolute_dir,
            "where database resides",
        ),
    )
    _root = _cfg.root
    if _root:
        return _root
    _root = pykern.util.dev_run_dir(_init_root)
    return _root
