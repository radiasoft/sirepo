"""simulation data operations

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        cls._init_models(data.models)

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        s = data.models.get("simulationSettings")
        if s and s.get("inputFile"):
            res.append(
                cls.lib_file_name_with_model_field(
                    "simulationSettings", "inputFile", s.inputFile
                )
            )
            res.extend(
                cls.lib_file_name_with_model_field("simulationSettings", "dataFile", n)
                for n in s.get("dataFiles", [])
            )
        p = data.models.get("plotAnimation")
        if p and p.get("experimentalFile"):
            res.append(
                cls.lib_file_name_with_model_field(
                    "plotAnimation", "experimentalFile", p.experimentalFile
                )
            )
        return res
