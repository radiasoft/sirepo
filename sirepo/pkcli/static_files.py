# -*- coding: utf-8 -*-
"""generate static files from package_data

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


def gen(target_dir):
    """Generate static files into `target_dir`

    Args:
        target_dir (str): directory must exist or be creatable
    """

    _Gen(target_dir)


class _Gen(PKDict):
    def __init__(self, target_dir):
        self.tgt = pykern.pkio.py_path(target_dir)
        self.count = PKDict(root=0)
        for r, s in sirepo.resource.static_files():
            self._copy(r, s)
            self._maybe_root(r, s)

        self._verify()
        with sirepo.quest.start(in_pkcli=True) as qcall:
            pykern.pkio.write_text(
                self.tgt.join("robots.txt"),
                qcall.call_api_sync("robotsTxt").content_as_str(),
            )

    def _copy(self, rel, src):
        t = self.tgt.join(rel)
        pykern.pkio.mkdir_parent_only(t)
        src.copy(t, stat=True)

    def _maybe_root(self, rel, src):
        if rel in _ROOT_FILES:
            self._copy(src.basename, src)
            self.count.root += 1

    def _verify(self):
        for k, v in self.count.items():
            if v < 2:
                raise AssertionError(f"{k} file count={v} less than 2")
