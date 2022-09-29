# -*- coding: utf-8 -*-
"""activait simulation data operations

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import contextlib
import h5py
import io
import sirepo.sim_data
import zipfile
import tarfile


class SimData(sirepo.sim_data.SimDataBase):

    _OLD_NEURAL_NET_FIELDS = [
        "activationActivation",
        "alphaDropoutRate",
        "denseActivation",
        "denseDimensionality",
        "dropoutRate",
        "gaussianDropoutRate",
        "gaussianNoiseStddev",
    ]

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
        cls._fixup_neural_net(dm)
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
    def _fixup_neural_net(cls, dm):
        for l in dm.neuralNet.layers:
            for (old, new) in cls._layer_fields(l):
                cls._update(l, old, new)
            for f in cls._OLD_NEURAL_NET_FIELDS:
                if f in l:
                    del l[f]

    @classmethod
    def _layer_fields(cls, layer):
        f = []
        n = layer.layer.lower()
        for field in layer:
            if n in field.lower():
                f.append((field, field.lower().replace(n, "")))
        return f

    @classmethod
    def _lib_file_basenames(cls, data):
        name = data.models.dataFile.get("file")
        if name:
            return [cls.lib_file_name_with_model_field("dataFile", "file", name)]
        return []

    @classmethod
    def _update(cls, layer, old, new):
        if old in layer:
            layer[new] = layer[old]
            layer.pop(old)


class DataReader(PKDict):

    def __init__(self, file_path):
        super().__init__()
        self.file_ctx = open
        self.pkupdate(path=pkio.py_path(file_path))

    def is_archive(self):
        return False

    def is_dir(self, item):
        return False

    @contextlib.contextmanager
    def data_context_manager(self, data_path):
        yield self.file_ctx(self.path, mode="r")

    def get_data_list(self, item_filter):
        return None


class ArchiveDataReader(DataReader):
    def __init__(self, file_path):
        super().__init__(file_path)

    @contextlib.contextmanager
    def file_context_manager(self):
        yield self.file_ctx(self.path, mode="r")

    def is_archive(self):
        return True


class HDF5DataReader(ArchiveDataReader):
    def __init__(self, file_path):
        super().__init__(file_path)
        self.file_ctx = h5py.File

    def is_dir(self, item):
        return isinstance(item, h5py.Group)

    @contextlib.contextmanager
    def data_context_manager(self, data_path):
        with super().data_context_manager(data_path) as f:
            yield f[data_path]


class TarDataReader(ArchiveDataReader):

    def __init__(self, file_path):
        super().__init__(file_path)
        self.file_ctx = tarfile.open

    @contextlib.contextmanager
    def data_context_manager(self, data_path):
        with self.file_context_manager() as f:
            yield io.TextIOWrapper(f.extractfile(data_path))

    def get_data_list(self, item_filter):
        with self.file_context_manager() as f:
            return [
                x.name
                for x in f.getmembers()
                if item_filter(x)
            ]

    def is_dir(self, item):
        return item.isdir()


class ZipDataReader(ArchiveDataReader):
    def __init__(self, file_path):
        super().__init__(file_path)
        self.file_ctx = zipfile.ZipFile

    @contextlib.contextmanager
    def data_context_manager(self, data_path):
        with self.file_context_manager() as f:
            yield io.TextIOWrapper(f.open(data_path))

    def get_data_list(self, item_filter):
        with self.file_context_manager() as f:
            return [
                x.filename
                for x in f.infolist()
                if item_filter(x)
            ]

    def is_dir(self, item):
        return item.is_dir()



class DataReaderFactory():
    _SUPPORTED_ARCHIVES = PKDict(
        {
            ".h5": HDF5DataReader,
            ".tar": TarDataReader,
            ".tar.gz": TarDataReader,
            ".zip": ZipDataReader
        }
    )

    _SUPPORTED_ARCHIVE_EXTENSIONS = _SUPPORTED_ARCHIVES.keys()

    @classmethod
    def get_archive_extension(cls, file_path):
        x = list(
            filter(
                lambda s: str(file_path).endswith(s),
                cls._SUPPORTED_ARCHIVE_EXTENSIONS,
            )
        )
        return x[0] if x else None

    @classmethod
    def build_reader(cls, file_path):
        return cls._SUPPORTED_ARCHIVES.get(
            cls.get_archive_extension(file_path), DataReader
        )(file_path)

