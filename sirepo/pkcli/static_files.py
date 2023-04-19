# -*- coding: utf-8 -*-
"""generate static files

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkio
import sirepo.quest
import sirepo.resource


_ROOT_FILES = frozenset(("static/img/favicon.ico", "static/img/favicon.png"))


def gen(target_dir):
    """Generate static files into `target_dir`

    Args:
        target_dir (str): directory must exist or be creatable
    """

    def _root_copy(dst, rel, src):
        if rel in _ROOT_FILES:
            src.copy(dst.join(src.basename))

    d = pykern.pkio.py_path(target_dir)
    for r, s in sirepo.resource.static_files():
        t = d.join(r)
        pykern.pkio.mkdir_parent_only(t)
        s.copy(t, stat=True)
        _root_copy(d, r, s)
    with sirepo.quest.start(in_pkcli=True) as qcall:
        pykern.pkio.write_text(
            d.join("robots.txt"),
            qcall.call_api_sync("robotsTxt").content_as_str(),
        )
