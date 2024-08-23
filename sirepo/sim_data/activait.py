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
    _OLD_NEURAL_NET_FIELDS = [
        "activationActivation",
        "alphaDropoutRate",
        "denseActivation",
        "denseDimensionality",
        "gaussianDropoutRate",
        "gaussianNoiseStddev",
    ]

    @classmethod
    def activait_data_reader(cls, file_path, data_path):
        def _reader():
            for k, v in _DATA_READERS.items():
                if str(file_path).endswith(k):
                    return v
            return DataReader

        return _reader()(file_path, data_path)

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
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
        cls._fixup_neural_net(dm.neuralNet.layers)
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
    def _compute_job_fields(cls, data, report, compute_model):
        res = [
            "columnInfo.header",
            "dataFile.file",
            "dataFile.inputsScaler",
        ]
        if "analysisReport" in report:
            res.append(report)
        if "fileColumnReport" in report:
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
        if "partitionColumnReport" in report:
            res.append("partition")
        return res

    @classmethod
    def _fixup_neural_net(cls, layers):
        def _layer_fields(layer):
            f = []
            n = layer.layer.lower()
            for field in layer:
                if n in field.lower():
                    f.append((field, field.lower().replace(n, "")))
            return f

        def _update(layer, old, new):
            if old in layer:
                layer[new] = layer[old]
                layer.pop(old)

        for l in layers:
            if l.layer == "Add" or l.layer == "Concatenate":
                for c in l.children:
                    if c.layers:
                        cls._fixup_neural_net(c.layers)
            if l.layer == "Conv2D":
                cls.update_model_defaults(l, "conv2D")
            for old, new in _layer_fields(l):
                _update(l, old, new)
            for f in cls._OLD_NEURAL_NET_FIELDS:
                if f in l:
                    del l[f]
            if "rate" in l:
                # special fixup for dropoutRate
                l.dropoutRate = l["rate"]
                del l["rate"]

    @classmethod
    def _lib_file_basenames(cls, data):
        name = data.models.dataFile.get("file")
        if name:
            return [cls.lib_file_name_with_model_field("dataFile", "file", name)]
        return []


class DataReader:
    def __init__(self, file_path, data_path=None):
        self.file_ctx = open
        self.path = pkio.py_path(file_path)
        self.data_path = data_path

    @contextlib.contextmanager
    def data_context_manager(self):
        yield self.file_ctx(self.path, mode="r")

    def csv_generator(self):
        import csv
        import re

        with self.data_context_manager() as f:
            for r in csv.reader(f):
                yield ",".join(map(lambda x: re.sub(r'["\n\r,]', "", x), r))


class ArchiveDataReader(DataReader):
    def __init__(self, file_path, data_path):
        super().__init__(file_path, data_path=data_path)

    @contextlib.contextmanager
    def file_context_manager(self):
        yield self.file_ctx(self.path, mode="r")


class HDF5DataReader(ArchiveDataReader):
    import h5py

    h5py = staticmethod(h5py)

    def __init__(self, file_path, data_path):
        super().__init__(file_path, data_path=data_path)
        self.file_ctx = HDF5DataReader.h5py.File

    @contextlib.contextmanager
    def data_context_manager(self):
        with self.file_context_manager() as f:
            yield f[self.data_path]


class TarDataReader(ArchiveDataReader):
    def __init__(self, file_path, data_path):
        super().__init__(file_path, data_path=data_path)
        self.file_ctx = tarfile.open

    @contextlib.contextmanager
    def data_context_manager(self):
        with self.file_context_manager() as f:
            yield io.TextIOWrapper(f.extractfile(self.data_path))


class ZipDataReader(ArchiveDataReader):
    def __init__(self, file_path, data_path):
        super().__init__(file_path, data_path=data_path)
        self.file_ctx = zipfile.ZipFile

    @contextlib.contextmanager
    def data_context_manager(self):
        with self.file_context_manager() as f:
            yield io.TextIOWrapper(f.open(self.data_path))


_DATA_READERS = PKDict(
    {
        ".h5": HDF5DataReader,
        ".tar": TarDataReader,
        ".tar.gz": TarDataReader,
        ".zip": ZipDataReader,
    }
)
