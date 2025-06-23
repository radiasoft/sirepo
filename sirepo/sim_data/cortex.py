# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        cls._init_models(data.models)

    @classmethod
    def _lib_file_basenames(cls, data):
        dm = data.models
        if "xlsFile" in dm.materialImport:
            return [
                cls.lib_file_name_with_model_field(
                    "materialImport",
                    "xlsFile",
                    data.models.materialImport.xlsFile,
                ),
            ]
        return []
