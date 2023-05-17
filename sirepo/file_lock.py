# -*- coding: utf-8 -*-
"""file locking

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import fcntl
import os
import pykern.pkconfig
import pykern.pkio
import time

_LOOP_SLEEP = None

_LOOP_COUNT = None


class FileLock:
    def __init__(self, path):
        p = pykern.pkio.py_path(path)
        if p.check(dir=True):
            p = p.join("lock")
        else:
            p += ".lock"
        self._path = str(p)

    def __enter__(self):
        for i in range(_LOOP_COUNT):
            try:
                f = os.open(self._path, os.O_RDWR | os.O_CREAT | os.O_TRUNC)
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                # Verify open file and path on disk are same file
                # https://stackoverflow.com/a/18745264
                if os.stat(f).st_ino == os.stat(self._path).st_ino:
                    self._lock = f
                    return None
            except (IOError, OSError, FileNotFoundError):
                pass
            if f:
                try:
                    os.close(f)
                except Exception:
                    pass
            time.sleep(_LOOP_SLEEP)
        raise RuntimeError(f"fail to flock path={self._path} timeout={_cfg.timeout}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._lock:
            os.unlink(self._path)
            os.close(self._lock)
            self._lock = None
        return False


def _init():
    global _cfg, _LOOP_SLEEP, _LOOP_COUNT
    _cfg = pykern.pkconfig.init(
        timeout=(60, pykern.pkconfig.parse_seconds, "how long to wait on flock"),
    )
    ms = 50
    _LOOP_COUNT = _cfg.timeout * (1000 // ms)
    _LOOP_SLEEP = ms / 1000.0


_init()
