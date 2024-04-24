# -*- coding: utf-8 -*-
"""Test for :mod:`sirepo.template.hdf5_util`

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import os
import subprocess
import time


def test_read_not_written():
    from pykern import pkunit

    for d in pkunit.case_dirs(group_prefix="1"):
        p = subprocess.Popen(
            ["python", d.join("read.py"), d.join("does_not_exist_at_first.h5")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(10)
        os.rename(d.join("x.h5"), d.join("does_not_exist_at_first.h5"))
        _, e = p.communicate()
        if e:
            raise AssertionError(e.decode())


def test_read_while_writing():
    from pykern import pkunit

    for d in pkunit.case_dirs(group_prefix="2"):
        subprocess.Popen(
            ["python", d.join("write.py"), d.join("x.h5")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        r = subprocess.Popen(
            ["python", d.join("read.py"), d.join("x.h5")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _, e = r.communicate()
        if e:
            raise AssertionError(e.decode())
