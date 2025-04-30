"""test file_lock

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_three_processes():
    import multiprocessing
    import time
    from pykern import pkunit, pkdebug
    from sirepo import file_lock
    from pykern.pkdebug import pkdp
    import os

    def _io(expect, append, before=0, after=0):
        pkdebug.pkdlog("start expect={}", expect)
        p = _path()
        if before:
            time.sleep(before)
        pkdebug.pkdlog("before={} expect={}", before, expect)
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
        # Test order: t1, t2, and t3. The before ensures the run-time
        _start("t1", "", "a"),
        _start("t2", "a", "b", before=0.5, after=1),
        _start("t3", "ab", "c", before=1),
    ]:
        p.join()
    pkunit.pkeq("abc", _path().read())
