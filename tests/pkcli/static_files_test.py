# -*- coding: utf-8 -*-
"""test sirepo.pkcli.static_files

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp


def test_get():
    from pykern import pkunit
    from sirepo.pkcli import static_files

    for d in pkunit.case_dirs(is_bytes=True):
        static_files.gen(d)
