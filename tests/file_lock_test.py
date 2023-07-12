# -*- coding: utf-8 -*-
"""test file_lock

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_four_processes():
    import multiprocessing
    import time
    from pykern import pkunit
    from sirepo import file_lock
    from pykern.pkdebug import pkdp
    import os

    def _io(expect, append, before=0, after=0):
        p = _path()
        if before:
            time.sleep(before)
        with file_lock.FileLock(p):
            v = p.read() if p.exists() else ""
            pkunit.pkeq(expect, v)
            p.write(v + append)
            if after:
                time.sleep(after)

    def _path():
        from pykern import pkunit

        return pkunit.work_dir().join("foo")

    def _start(name, *args, **kwargs):
        p = multiprocessing.Process(target=_io, name=name, args=args, kwargs=kwargs)
        p.start()
        return p

    pkunit.empty_work_dir()
    for p in [
        # Test order: t1, t2, t4, and t3 so the before values have to align that way
        # and after=1 causes t3 and t4 to queue
        _start("t1", "", "a"),
        _start("t2", "a", "b", before=1, after=2),
        # More than the _LOOP_SLEEP
        _start("t3", "abd", "c", before=3),
        _start("t4", "ab", "d", before=2),
    ]:
        p.join()
    pkunit.pkeq("abdc", _path().read())


def test_happy():
    from pykern import pkunit
    from sirepo import file_lock

    def _simple(path):
        with file_lock.FileLock(path):
            pass

    _simple(pkunit.empty_work_dir())
