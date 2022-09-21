# -*- coding: utf-8 -*-
"""Tests conversion of keras model into PKDict format UI understands

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import keras.models
import sirepo.template.activait
from pykern import pkjson, pkunit
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from pykern.pkcollections import PKDict


def test_load_model_to_ui_data():
    from pykern import pkjson

    for d in pkunit.case_dirs():
        pkjson.dump_pretty(
            sirepo.template.activait._build_ui_nn(
                keras.models.load_model(d.join("model.h5"))
            ).layers,
            filename="ui_model.json",
        )
