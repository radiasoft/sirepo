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

#: Any directory in the database whose name ends with this suffix will be
#: automatically removed after some time.
TMP_DIR_SUFFIX = '.tmp'

#: Every TMP_DIR_CLEANUP_TIME seconds, we scan through the run database, and
#: any directories that are named '*.tmp', and whose mtime is
#: >TMP_DIR_CLEANUP_TIME in the past, are deleted.
TMP_DIR_CLEANUP_TIME = 24 * 60 * 60  # 24 hours


def root():
    if not _root:
        _init_root()
    return _root


def runner_socket_path():
    return root() / 'runner.sock'


def server_init_root(value):
    _init_root(value)
    return root()


@pkconfig.parse_none
def _cfg_root(value):
    """Config value or root package's parent or cwd with `_DEFAULT_ROOT`"""
    return value


def _init_root(*args):
    global _root

    if args:
        assert not cfg.root, \
            'Cannot set both SIREPO_SRDB_ROOT ({}) and SIREPO_SERVER_DB_DIR ({})'.format(
                cfg.root,
                args[0],
            )
        cfg.root = args[0]
    v = cfg.root
    if v:
        assert os.path.isabs(v), \
            '{}: SIREPO_SRDB_ROOT must be absolute'.format(v)
        assert os.path.isdir(v), \
            '{}: SIREPO_SRDB_ROOT must be a directory and exist'.format(v)
        v = pkio.py_path(v)
    else:
        assert pkconfig.channel_in('dev'), \
            'SIREPO_SRDB_ROOT must be configured except in DEV'
        fn = sys.modules[pkinspect.root_package(_init_root)].__file__
        root = pkio.py_path(pkio.py_path(pkio.py_path(fn).dirname).dirname)
        # Check to see if we are in our dev directory. This is a hack,
        # but should be reliable.
        if not root.join('requirements.txt').check():
            # Don't run from an install directory
            root = pkio.py_path.local('.')
        v = pkio.mkdir_parent(root.join(_DEFAULT_ROOT))
    _root = v


cfg = pkconfig.init(
    root=(None, _cfg_root, 'where database resides'),
)
