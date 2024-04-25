# -*- coding: utf-8 -*-
"""Test for :mod:`sirepo.template.hdf5_util`

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import os
import shutil
import subprocess
import time


def test_read_while_writing():
    from pykern import pkunit

    d = pkunit.data_dir()
    w = pkunit.work_dir()
    for case_work_dir in _case_dirs_from_same_data_dir(d, w, 2):
        if case_work_dir.basename == "1":
            p = _proc(case_work_dir, "read.py", "does_not_exist_at_first.h5")
            time.sleep(10)
            os.rename(
                case_work_dir.join("x.h5"),
                case_work_dir.join("does_not_exist_at_first.h5"),
            )
            _raise(p)
        if case_work_dir.basename == "2":
            _proc(case_work_dir, "write.py", "x.h5")
            _raise(_proc(case_work_dir, "read.py", "x.h5"))


def _case_dirs_from_same_data_dir(data_dir, work_dir, cases):
    res = []
    for i in range(cases):
        w = work_dir.join(str(i + 1))
        shutil.copytree(data_dir, w)
        res.append(w)
    return res


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
