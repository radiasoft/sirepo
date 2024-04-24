# -*- coding: utf-8 -*-
"""Test for :mod:`sirepo.template.hdf5_util`

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import os
import subprocess
import time


def test_read_while_writing():
    from pykern import pkunit

    def _proc(dir, exe_name, data_name):
        return subprocess.Popen(
            ["python", dir.join(exe_name), dir.join(data_name)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def _raise(process):
        _, e = process.communicate()
        if e:
            raise AssertionError(e.decode())

    for d in pkunit.case_dirs():
        if d.basename == "1":
            p = _proc(d, "read.py", "does_not_exist_at_first.h5")
            time.sleep(10)
            os.rename(d.join("x.h5"), d.join("does_not_exist_at_first.h5"))
            _raise(p)
        if d.basename == "2":
            _proc(d, "write.py", "x.h5")
            _raise(_proc(d, "read.py", "x.h5"))
