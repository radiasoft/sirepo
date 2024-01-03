# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.importer`

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_importer(fc):
    from pykern import pkio, pkunit
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
    from pykern.pkunit import pkeq, pkok
    from sirepo import sim_data, template
    import asyncio

    for f in pkio.sorted_glob(pkunit.data_dir().join("*.dat")):
        file_ext = "dat"
        pkdlog("file={}", f)
        sim_type = "zgoubi"
        fc.sr_get_root(sim_type)
        is_dev = "deviance" in f.basename
        res = fc.sr_post_form(
            "importFile",
            PKDict(folder="/importer_test"),
            PKDict(simulation_type=sim_type),
            file=f,
        )
        sim_name = f.purebasename
        pkok("models" in res, "no models file={} res={}", f, res)
