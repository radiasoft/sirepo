# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 202 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    @classmethod
    def dagmc_filename(cls, data):
        return cls.lib_file_name_with_model_field(
            "geometryInput",
            "dagmcFile",
            data.models.geometryInput.dagmcFile,
        )

    @classmethod
    def source_filenames(cls, data):
        return [
            cls.lib_file_name_with_model_field("source", "file", x.file)
            for x in data.models.settings.sources
            if x.get("type") == "file" and x.get("file")
        ]

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        def _float_to_j_range(val, field_info):
            pkdp("FL 2 JR {}", val)
            if not isinstance(val, (float, int)):
                return val
            m = field_info[2]
            m.val = val
            return m

        sch = cls.schema()
        dm = data.models
        cls._init_models(
            dm,
            (
                "dagmcAnimation",
                "geometry3DReport",
                "geometryInput",
                "openmcAnimation",
                "reflectivePlanes",
                "settings",
                "tallyReport",
                "volumes",
            ),
        )
        for v in dm.volumes:
            if "material" not in dm.volumes[v]:
                continue
            if not dm.volumes[v].material.get("standardType"):
                dm.volumes[v].material.standardType = "None"
            dm.volumes[v].opacity = _float_to_j_range(dm.volumes[v].opacity, sch.model.geometry3DReport.opacity)
        if "tally" in dm:
            del dm["tally"]
        for t in dm.settings.tallies:
            for i in range(1, sch.constants.maxFilters + 1):
                f = t[f"filter{i}"]
                y = f._type
                if y != "None":
                    cls.update_model_defaults(f, y)
        for (m, f) in (
            ('tallyReport', 'planePos'),
            ('openmcAnimation', 'opacity'),
            ('geometry3DReport', 'opacity',)
        ):
            dm[m][f] = _float_to_j_range(dm[m][f], sch.model[m][f])
        for v in dm.volumes:
            pkdp("CHK OP {}", v)
            dm.volumes[v].opacity = _float_to_j_range(
                dm.volumes[v].opacity,
                [
                    0,
                    0,
                    PKDict(
                        min=0.0,
                        max=1.0,
                        numSteps=100,
                        step=0.01,
                        val=1.0,
                        space="linear"
                    )
                ]
            )

    @classmethod
    def _compute_job_fields(cls, data, *args, **kwargs):
        return []

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model == "geometry3DReport":
            return "dagmcAnimation"
        return analysis_model

    @classmethod
    def _lib_file_basenames(cls, data):
        if data.get("report") == "tallyReport":
            return []
        if data.models.geometryInput.dagmcFile:
            return [
                cls.dagmc_filename(data),
            ] + cls.source_filenames(data)
        return []

    @classmethod
    def _sim_file_basenames(cls, data):
        res = []
        if data.report == "openmcAnimation":
            for v in data.models.volumes:
                res.append(PKDict(basename=f"{data.models.volumes[v].volId}.ply"))
        return res
