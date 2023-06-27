# -*- coding: utf-8 -*-
"""test sirepo.pkcli.static_files

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp


def test_gen(monkeypatch):
    from pykern import pkunit
    from pykern.pkdebug import pkdp
    from sirepo import resource
    from sirepo.pkcli import static_files

    for d in pkunit.case_dirs(is_bytes=True):
        monkeypatch.setattr(resource, "glob_paths", lambda p: [d.join("src", p)])
        static_files.gen(d)
