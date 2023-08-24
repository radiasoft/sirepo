# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(dm, cls.schema().model.keys())
        if "sim1BeamAnimation" in dm:
            cls._map_old_sim_structure(dm)

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        return res

    @classmethod
    def _map_old_sim_structure(cls, dm):
        _COUNT = 4
        sims = []
        w = dm.simWorkflow
        for c1 in range(1, _COUNT + 1):
            s = PKDict(
                simulationType=w[f"simType_{c1}"],
                simulationId=w[f"simId_{c1}"],
            )
            if s.simulationType and s.simulationId:
                sims.append(s)
            del w[f"simType_{c1}"]
            del w[f"simId_{c1}"]
            del dm[f"sim{c1}BeamAnimation"]
            for c2 in range(1, _COUNT + 1):
                del dm[f"sim{c1}Phase{c2}Animation"]
        sims.append(cls.model_defaults("coupledSim"))
        w.coupledSims = sims
