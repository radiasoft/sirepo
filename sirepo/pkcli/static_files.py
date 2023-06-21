# -*- coding: utf-8 -*-
"""generate static files

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkio
import sirepo.const
import sirepo.quest
import sirepo.resource
import re

_ROOT_FILES = frozenset(("static/img/favicon.ico", "static/img/favicon.png"))
_REACT_RE = re.compile(f"({sirepo.const.REACT_BUNDLE_FILE_PAT}.*)")


def gen(target_dir):
    """Generate static files into `target_dir`

    Args:
        target_dir (str): directory must exist or be creatable
    """

    def _copy(dst, rel, src):
        tgt = dst.join(rel)
        pykern.pkio.mkdir_parent_only(tgt)
        src.copy(tgt, stat=True)

    def _react_copy(dst, rel, src):
        m = _REACT_RE.match(rel)
        if m:
            _copy(dst, m.group(1), src)

    def _root_copy(dst, rel, src):
        if rel in _ROOT_FILES:
            _copy(dst, src.basename, src)

    d = pykern.pkio.py_path(target_dir)
    for r, s in sirepo.resource.static_files():
        _copy(d, r, s)
        _root_copy(d, r, s)
        _react_copy(d, r, s)
    with sirepo.quest.start(in_pkcli=True) as qcall:
        pykern.pkio.write_text(
            d.join("robots.txt"),
            qcall.call_api_sync("robotsTxt").content_as_str(),
        )
