# -*- coding: utf-8 -*-
"""ML simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def fixup_old_data(cls, data):
        dm = data.models
        cls._init_models(
            dm,
            cls.schema().model.keys(),
        )
        if "colsWithNonUniqueValues" not in dm.columnInfo:
            dm.columnInfo.colsWithNonUniqueValues = PKDict()
        for m in dm:
            if "fileColumnReport" in m:
                cls.update_model_defaults(dm[m], "fileColumnReport")
        dm.analysisReport.pksetdefault(history=[])
        dm.hiddenReport.pksetdefault(subreports=[])

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if "fileColumnReport" in analysis_model:
            return "fileColumnReport"
        if "partitionColumnReport" in analysis_model:
            return "partitionColumnReport"
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = [
            "columnInfo.header",
            "dataFile.file",
            "dataFile.inputsScaler",
        ]
        if "fileColumnReport" in r:
            d = data.models.dataFile
            if d.appMode == "classification":
                # no outputsScaler for classification
                return res
            res.append("dataFile.outputsScaler")
            if d.inputsScaler == d.outputsScaler:
                # If inputsScaler and outputsScaler are the same then the
                # the columns will be unchanged when switching between input/output
                return res
            return res + ["columnInfo.inputOutput"]
        if "partitionColumnReport" in r:
            res.append("partition")
        return res

    @classmethod
    def _lib_file_basenames(cls, data):
        name = data.models.dataFile.get("file")
        if name:
            return [cls.lib_file_name_with_model_field("dataFile", "file", name)]
        return []
