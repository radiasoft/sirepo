# -*- coding: utf-8 -*-
u"""PyTest for :mod:`sirepo.importer`

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc


def test_importer(import_req):
    from pykern.pkunit import pkeq
    from sirepo.template import opal
    from sirepo.template import opal_parser
    import re

    with pkunit.save_chdir_work():
        for fn in pkio.sorted_glob(pkunit.data_dir().join('*.in')):
            error = None
            try:
                data, files = opal_parser.parse_file(pkio.read_text(fn), filename=fn)
            except Exception as e:
                pkdlog(pkdexc())
                error = str(e)
            if error:
                actual = error
            else:
                data['report'] = 'animation'
                actual = opal.python_source_for_model(data, None)
            outfile = re.sub(r'\.in$', '.txt', fn.basename)
            pkio.write_text(outfile, actual)
            expect = pkio.read_text(pkunit.data_dir().join(outfile))
            pkeq(expect, actual)
