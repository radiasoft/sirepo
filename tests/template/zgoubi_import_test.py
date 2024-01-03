# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.importer`

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest


def test_importer(import_req):
    from pykern import pkio
    from pykern import pkunit
    from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
    from pykern.pkunit import pkeq
    from sirepo import sim_data, template
    import asyncio

    with pkunit.save_chdir_work() as w:
        for fn in pkio.sorted_glob(pkunit.data_dir().join("*.dat")):
            error = None
            req = import_req(fn)
            try:
                data = asyncio.run(
                    template.import_module("zgoubi").import_file(
                        req,
                        unit_test_mode=True,
                    )
                )
                sim_data.get_class("zgoubi").fixup_old_data(
                    data,
                    qcall=req.qcall,
                )
            except Exception as e:
                pkdlog(pkdexc())
                error = e.message
            if error:
                actual = error
            else:
                actual = zgoubi.python_source_for_model(data, qcall=req.qcall)
            outfile = fn.basename + ".txt"
            pkio.write_text(outfile, actual)
            e = pkunit.data_dir().join(outfile)
            expect = pkio.read_text(e)
            pkeq(expect, actual, "diff {} {}", e, w.join(outfile))
