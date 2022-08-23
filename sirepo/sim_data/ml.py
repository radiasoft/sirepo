# -*- coding: utf-8 -*-
"""ML simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
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

    _ARCHIVE_EXTENSIONS = (
        ".tar.gz",
        ".zip",
    )

    def __init__(self, file_path):
        super().__init__()
        self.pkupdate(
            file_path=file_path,
            filename=file_path if isinstance(file_path, str) else file_path.basename,
        )
        if self._is_archive_type(".zip"):
            self.dir_check = "is_dir"
            self.extractor = "open"
            self.file_ctx = zipfile.ZipFile
            self.item_name = "filename"
            self.lister = "infolist"
        if self._is_archive_type(".tar.gz"):
            self.dir_check = "isdir"
            self.extractor = "extractfile"
            self.file_ctx = tarfile.open
            self.item_name = "name"
            self.lister = "getmembers"

    def _is_archive_type(self, ext):
        return self.filename.endswith(ext)

    def is_archive(self):
        return any([self._is_archive_type(s) for s in DataReader._ARCHIVE_EXTENSIONS])

    @contextlib.contextmanager
    def data_context_manager(self, data_path):
        if not self.is_archive():
            yield open(self.file_path)
        else:
            with self.file_ctx(self.file_path, mode="r") as f:
                yield io.TextIOWrapper(getattr(f, self.extractor)(data_path))

    def get_data_list(self, item_filter):
        if not self.is_archive():
            return None
        with self.file_ctx(self.file_path, mode="r") as f:
            return [
                getattr(x, self.item_name)
                for x in getattr(f, self.lister)()
                if item_filter(x)
            ]
