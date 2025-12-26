"""Tests conversion of keras model into PKDict format UI understands

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_load_model_to_ui_data():
    from pykern import pkjson, pkjson, pkunit
    from keras import models
    from sirepo.template import activait

    for d in pkunit.case_dirs():
        pkjson.dump_pretty(
            activait._build_ui_nn(models.load_model(d.join("model.h5"))).layers,
            filename="ui_model.json",
        )
