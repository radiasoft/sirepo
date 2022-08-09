# -*- coding: utf-8 -*-
"""Tests conversion of neural network data into functional nn code

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import sirepo.template.ml
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern.pkcollections import PKDict


def test_data_to_python():
    from pykern import pkio
    from pykern import pkjson

    for d in pkunit.case_dirs():
        i = pkjson.load_any(d.join("net.json"))
        pkio.write_text("net.py", sirepo.template.ml._build_model_py(i))
