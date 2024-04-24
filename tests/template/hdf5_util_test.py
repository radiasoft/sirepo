# -*- coding: utf-8 -*-
"""Test for :mod:`sirepo.template.hdf5_util`

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import asyncio
import os
import time


def test_read_while_writing():
    from sirepo.template.hdf5_util import HDF5Util
    from pykern import pkunit

    for d in pkunit.case_dirs():
        h = HDF5Util(d.join("does_not_exist_at_first.h5"))

        async def _write_to_filename():
            # async with lock:
                # time.sleep(4)
            os.rename(d.join("x.h5"), d.join("does_not_exist_at_first.h5"))

        async def _read():
            # async with lock:
            with h.read_while_writing() as f:
                print("trying to read non existent")

        async def _run():
            # lock = asyncio.Lock()
            await asyncio.gather(_read(), _write_to_filename())

        asyncio.run(_run())
