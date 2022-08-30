# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.importer`

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc


def test_importer(import_req):
    from pykern import pkunit
    from sirepo.template import opal
    from sirepo.template import opal_parser
    import re

    for d in pkunit.case_dirs():
        data, files = opal_parser.parse_file(
            pkio.read_text(d.join("opal.in")), filename=d.join("opal.in")
        )
        data["report"] = "animation"
        pkio.write_text(d.join("opal.txt"), opal.python_source_for_model(data, None))
