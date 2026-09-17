# -*- coding: utf-8 -*-
"""rftrack simulation data operations

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import sirepo.sim_data.lattice


class SimData(sirepo.sim_data.lattice.LatticeSimData):
    _BUNCH_REPORT_DEPENDENCIES = ["beam"]

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        super().fixup_old_data(data, qcall, **kwargs)
        cls._init_models(
            data.models,
            (
                "beam",
                "beamline",
                "simulation",
                "simulationSettings",
                "simulationStatus",
                "statAnimation",
            ),
        )
