# -*- coding: utf-8 -*-
"""activait simulation data operations

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import contextlib
import io
import sirepo.sim_data
import zipfile
import tarfile


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def fixup_old_data(cls, data):
        if data.simulationType == "ml":
            data.simulationType = "activait"
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


class DataReader(PKDict):

    _SUPPORTED_ARCHIVES = PKDict(
        {
            ".tar.gz": PKDict(
                dir_check="isdir",
                extractor="extractfile",
                file_ctx=tarfile.open,
                item_name="name",
                lister="getmembers",
            ),
            ".zip": PKDict(
                dir_check="is_dir",
                extractor="open",
                file_ctx=zipfile.ZipFile,
                item_name="filename",
                lister="infolist",
            ),
        },
    )

    _SUPPORTED_ARCHIVE_EXTENSIONS = _SUPPORTED_ARCHIVES.keys()

    def __init__(self, file_path):
        super().__init__()
        self.pkupdate(path=pkio.py_path(file_path))
        self.pkupdate(
            DataReader._SUPPORTED_ARCHIVES.get(self._get_archive_extension(), {})
        )

    def _get_archive_extension(self):
        x = list(
            filter(
                lambda s: self.path.basename.endswith(s),
                DataReader._SUPPORTED_ARCHIVE_EXTENSIONS,
            )
        )
        return x[0] if x else None

    def is_archive(self):
        return self._get_archive_extension() is not None

    @contextlib.contextmanager
    def data_context_manager(self, data_path):
        if not self.is_archive():
            yield open(self.path)
        else:
            with self.file_ctx(self.path, mode="r") as f:
                yield io.TextIOWrapper(getattr(f, self.extractor)(data_path))

    def get_data_list(self, item_filter):
        if not self.is_archive():
            return None
        with self.file_ctx(self.path, mode="r") as f:
            return [
                getattr(x, self.item_name)
                for x in getattr(f, self.lister)()
                if item_filter(x)
            ]
