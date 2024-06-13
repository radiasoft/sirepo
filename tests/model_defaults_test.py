"""PyTest for :mod:`sirepo.template.srw.py`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pytest
from sirepo import srunit


def test_srw_model_defaults():
    from sirepo import srunit

    with srunit.quest_start(want_user=True) as qcall:
        from pykern import pkunit
        from pykern import pkconfig
        from pykern.pkcollections import PKDict
        from sirepo.template import template_common
        from sirepo import simulation_db, sim_data

        s = sim_data.get_class("srw")
        s.resource_path("predefined.json")
        res = s.model_defaults("trajectoryReport")
        assert res == PKDict(
            notes="",
            plotAxisY2="None",
            timeMomentEstimation="auto",
            initialTimeMoment=0.0,
            numberOfPoints=10000,
            plotAxisY="X",
            plotAxisX="Z",
            finalTimeMoment=0.0,
        )
        model = PKDict(
            numberOfPoints=10,
            finalTimeMoment=1.0,
        )
        s.update_model_defaults(model, "trajectoryReport")
        assert model["numberOfPoints"] == 10
        assert model["finalTimeMoment"] == 1.0
        assert model["plotAxisX"] == "Z"
