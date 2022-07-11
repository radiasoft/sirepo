# -*- coding: utf-8 -*-
"""PyTest for :mod:`sirepo.template.srw_shadow`

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
import pytest


def test_conversion():
    from sirepo.template.srw_shadow import Convert

    for d in pkunit.case_dirs():
        if "to_shadow" in str(d):
            _write_converted_data(
                Convert().to_shadow,
                d.join("srw.json"),
                d.join("shadow.json"),
            )
        else:
            _write_converted_data(
                Convert().to_srw,
                d.join("shadow.json"),
                d.join("srw.json"),
            )


def _write_converted_data(conversion_function, in_path, out_path):
    from pykern import pkjson

    c = conversion_function(pkjson.load_any(in_path)).models
    c.simulation.lastModified = ""
    pkjson.dump_pretty(c, out_path)
