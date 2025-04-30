"""file locking

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import asyncio
import fcntl
import os
import pykern.pkconfig
import pykern.pkio
import time

_LOOP_SLEEP = None

_LOOP_COUNT = None


class _Base:
    """Lock a file for global mutex

    Args:
        path (py.path.local): base name for lock
    """

    def __init__(self, path):
        self._lock = None
        p = pykern.pkio.py_path(path)
        if p.check(dir=True):
            p = p.join("lock")
        else:
            p += ".lock"
        self._path = str(p)

    def _enter(self):
        for _ in range(_LOOP_COUNT):
            try:
                f = None
                f = os.open(self._path, os.O_RDWR | os.O_CREAT | os.O_TRUNC)
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                if self._verify_lock_path(f):
                    self._lock = f
                    return
            except (IOError, OSError, FileNotFoundError):
                pass
            self._unchecked_close(f)
            # Not asyncio.sleep: not in coroutine, probably should to be (simulation_db.user_lock)
            yield
        raise RuntimeError(f"fail to flock path={self._path} timeout={_cfg.timeout}")

    def _exit(self, *args, **kwargs):
        if self._lock:
            os.unlink(self._path)
            os.close(self._lock)
            self._lock = None
        return False

    def _unchecked_close(self, handle):
        """Close lock path ignoring errors

        We want to ensure the loop continues, and there's
        nothing we can do at this point so close ignoring
        exceptions.

        Args:
           handle (IO): possibly opened file

        """
        if not handle:
            return
        try:
            os.close(handle)
        except Exception:
            pass

    def _verify_lock_path(self, handle):
        """Verify open file and path on disk are same file

        There's a race condition between the open and the flock.
        Two processes might not lock the same file. It's a
        complicated race condition that requires process A to
        speed through all of `__enter__` and `__exit__` during the
        time that process B opens the file before it opens the
        lock. Since our locking is for very small operations
        (typically), this could happen. See `<https://stackoverflow.com/a/18745264>`_

        Args:
            handle (IO): handle to open, locked file
        Return:
            bool: True if `handle` and `self._path` are same inode
        """
        return os.stat(handle).st_ino == os.stat(self._path).st_ino


class AsyncFileLock(_Base):
    """Lock a file for global mutex

    Args:
        path (py.path.local): base name for lock
        qcall (sirepo.quest.API): to ensure not re-entrant
    """

    def __init__(self, path, qcall):
        super().__init__(path)
        # Do here so simpler code below
        if qcall.bucket_unchecked_get(self._path):
            raise AssertionError(f"attempt to relock path={self._path}")
        qcall.bucket_set(self._path, True)

    async def __aenter__(self):
        for _ in self._enter():
            await asyncio.sleep(_LOOP_SLEEP)

    async def __aexit__(self, *args, **kwargs):
        return self._exit(*args, **kwargs)


class FileLock(_Base):
    def __enter__(self):
        for _ in self._enter():
            time.sleep(_LOOP_SLEEP)

    def __exit__(self, *args, **kwargs):
        return self._exit(*args, **kwargs)


def _init():
    global _cfg, _LOOP_SLEEP, _LOOP_COUNT
    _cfg = pykern.pkconfig.init(
        timeout=(60, pykern.pkconfig.parse_seconds, "how long to wait on flock"),
    )
    ms = 50
    _LOOP_COUNT = _cfg.timeout * (1000 // ms)
    _LOOP_SLEEP = ms / 1000.0


_init()
