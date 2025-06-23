# -*- coding: utf-8 -*-
"""Wrapper to run impact from the command line.
:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from pykern.pkcollections import PKDict
from sirepo.template import template_common


def run(cfg_dir):
    # TODO(pjm): import xls file input database here
    res = PKDict(
        # TODO(pjm): return a summary of the import data to display a confirm page to the user
        material=PKDict(name="sample"),
    )
    template_common.write_sequential_result(res, run_dir=pkio.py_path(cfg_dir))
