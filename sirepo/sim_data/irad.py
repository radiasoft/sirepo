# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import simulation_db
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    CT_FILE = "ct.zip"
    DVH_FILE = "dvh-data.json"
    RTDOSE_FILE = "rtdose.zip"
    RTDOSE2_FILE = "rtdose2.zip"
    RTSTRUCT_FILE = "rtstruct-data.json"

    @classmethod
    def _compute_model(cls, analysis_model, data):
        return analysis_model

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        dm = data.models
        cls._init_models(
            dm,
            (
                "dicomSettings",
                "dicomWindow",
                "doseWindow",
                "doseDifferenceWindow",
            ),
        )

    @classmethod
    def lib_file_for_sim(cls, data, filename):
        return "{}-{}".format(
            data.models.simulation.libFilePrefix,
            filename,
        )

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if r == "dvhReport":
            return [r, data.models.dicomSettings.selectedROIs]
        return [r]

    @classmethod
    def _lib_file_basenames(cls, data):
        r = data.get("report")
        res = []
        if not r:
            res += [
                cls.DVH_FILE,
                cls.CT_FILE,
                cls.RTDOSE_FILE,
                cls.RTDOSE2_FILE,
                cls.RTSTRUCT_FILE,
            ]
        elif r == "dvhReport":
            res += [cls.DVH_FILE]
        elif r == "dicom3DReport":
            res += [cls.CT_FILE, cls.RTDOSE_FILE, cls.RTDOSE2_FILE, cls.RTSTRUCT_FILE]
        else:
            assert False, "unknown report: {}".format(r)
        return [cls.lib_file_for_sim(data, v) for v in res]
