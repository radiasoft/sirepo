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
    def _read_not_written(case_work_dir):
        p = _proc(case_work_dir, "read.py", "does_not_exist_at_first.h5")
        time.sleep(10)
        os.rename(
            case_work_dir.join("x.h5"),
            case_work_dir.join("does_not_exist_at_first.h5"),
        )
        _raise(p)

    def _read_while_write(case_work_dir):
        _proc(case_work_dir, "write.py", "x.h5")
        _raise(_proc(case_work_dir, "read.py", "x.h5"))

    _case_dirs_from_same_data_dir(
        [
            _read_not_written,
            _read_while_write,
            # TODO (gurhar1133): test KeyError case
            # TODO (gurhar1133): also, maybe these should be different tests?
        ]
    )


def _case_dirs_from_same_data_dir(cases):
    from pykern import pkunit

    w = pkunit.work_dir()
    for i in range(len(cases)):
        c = w.join(str(i + 1))
        shutil.copytree(pkunit.data_dir(), c)
        cases[i](c)


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
