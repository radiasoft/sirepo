# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):

    ANALYSIS_ONLY_FIELDS = frozenset(("colorMap", "notes"))

    @classmethod
    def fixup_old_data(cls, data, **kwargs):
        dm = data.models
        cls._init_models(
            dm,
            (
                "beam",
                "beamAnimation",
                "beamHistogramAnimation",
                "parameterAnimation",
                "particleAnimation",
            ),
        )
        dm.solenoid.setdefault("solenoidFile", "")
        # TODO(robnagler) setdefaults?
        if "beamDefinition" not in dm.beam:
            dm.beam.update(
                beamDefinition="transverse_longitude",
                cstCompress="0",
                transversalFile2d="",
                transversalFile4d="",
                longitudinalFile1d="",
                longitudinalFile2d="",
                cstFile="",
            )
        cls._organize_example(data)

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        return cls._non_analysis_fields(data, r) + [
            "beam",
            "ellipticalDistribution",
            "energyPhaseDistribution",
            "solenoid",
            "sphericalDistribution",
            "twissDistribution",
        ]

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if "bunchReport" in analysis_model:
            return "bunchReport"
        return super()._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        s = data.models.solenoid
        if s.sourceDefinition == "file" and s.solenoidFile:
            res.append(
                cls.lib_file_name_with_model_field(
                    "solenoid", "solenoidFile", s.solenoidFile
                )
            )
        beam = data.models.beam
        if beam.beamDefinition == "cst_pit" or beam.beamDefinition == "cst_pid":
            res.append(
                cls.lib_file_name_with_model_field("beam", "cstFile", beam.cstFile)
            )
        if beam.beamDefinition == "transverse_longitude":
            if beam.transversalDistribution == "file2d":
                res.append(
                    cls.lib_file_name_with_model_field(
                        "beam", "transversalFile2d", beam.transversalFile2d
                    )
                )
            elif beam.transversalDistribution == "file4d":
                res.append(
                    cls.lib_file_name_with_model_field(
                        "beam", "transversalFile4d", beam.transversalFile4d
                    )
                )
            if beam.longitudinalDistribution == "file1d":
                res.append(
                    cls.lib_file_name_with_model_field(
                        "beam", "longitudinalFile1d", beam.longitudinalFile1d
                    )
                )
            if beam.longitudinalDistribution == "file2d":
                res.append(
                    cls.lib_file_name_with_model_field(
                        "beam", "longitudinalFile2d", beam.longitudinalFile2d
                    )
                )
        return res
