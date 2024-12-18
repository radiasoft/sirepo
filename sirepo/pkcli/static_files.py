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


def gen(target_dir):
    """Generate static files into `target_dir`

    Args:
        target_dir (str): directory must exist or be creatable
    """

    _Gen(target_dir)


class _Gen(PKDict):
    def __init__(self, target_dir):
        self.tgt = pykern.pkio.py_path(target_dir)
        for r, s in sirepo.resource.static_files():
            self._copy(r, s)
        with sirepo.quest.start(in_pkcli=True) as qcall:
            for k, v in PKDict(
                robotsTxt="robots.txt",
                securityTxt="security.txt",
            ).items():
                pykern.pkio.write_text(
                    self.tgt.join("static").join(v),
                    qcall.call_api_sync(k).content_as_str(),
                )

    def _copy(self, rel, src):
        t = self.tgt.join(rel)
        pykern.pkio.mkdir_parent_only(t)
        src.copy(t, stat=True)
