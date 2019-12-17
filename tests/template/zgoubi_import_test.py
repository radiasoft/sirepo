# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.importer`

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
import pytest
from sirepo import srunit


def test_importer(import_req):
    from pykern import pkcollections
    from pykern import pkjson
    from pykern.pkunit import pkeq
    from sirepo.template import zgoubi
    import sirepo.sim_data

    with pkunit.save_chdir_work():
        for fn in pkio.sorted_glob(pkunit.data_dir().join('*.dat')):
            error = None
            try:
                data = zgoubi.import_file(import_req(fn), unit_test_mode=True)
                sirepo.sim_data.get_class('zgoubi').fixup_old_data(data)
                #TODO(pjm): easier way to convert nested dict to pkcollections.Dict?
                data = pkcollections.json_load_any(pkjson.dump_pretty(data))
            except Exception as e:
                pkdlog(pkdexc())
                error = e.message
            if error:
                actual = error
            else:
                actual = zgoubi.python_source_for_model(data)
            outfile = fn.basename + '.txt'
            pkio.write_text(outfile, actual)
            expect = pkio.read_text(pkunit.data_dir().join(outfile))
            pkeq(expect, actual)
