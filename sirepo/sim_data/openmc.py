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
    def materials_filename(cls, data):
        return cls.lib_file_name_with_model_field(
            "geometryInput",
            "materialsFile",
            data.models.geometryInput.materialsFile,
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
        def _fix_val(model, field):
            if field in model and isinstance(model[field], dict):
                model[field] = model[field].val

        sch = cls.schema()
        dm = data.models
        cls._init_models(
            dm,
            (
                "dagmcAnimation",
                "energyAnimation",
                "geometry3DReport",
                "geometryInput",
                "openmcAnimation",
                "reflectivePlanes",
                "settings",
                "tallyReport",
                "volumes",
                "survivalBiasing",
                "weightWindows",
                "weightWindowsMesh",
            ),
        )
        if "plane1a" in dm.reflectivePlanes:
            if dm.reflectivePlanes.useReflectivePlanes == "1":
                dm.reflectivePlanes.planesList += [
                    {
                        "inside": "0",
                        "A": dm.reflectivePlanes.plane1a,
                        "B": dm.reflectivePlanes.plane1b,
                        "C": 0,
                        "D": 0,
                    },
                    {
                        "inside": "1",
                        "A": dm.reflectivePlanes.plane2a,
                        "B": dm.reflectivePlanes.plane2b,
                        "C": 0,
                        "D": 0,
                    },
                ]
            for k in ("plane1a", "plane1b", "plane2a", "plane2b"):
                dm.reflectivePlanes.pkdel(k)
        for v in dm.volumes:
            if "material" not in dm.volumes[v]:
                continue
            cls.update_model_defaults(dm.volumes[v].material, "material")
            _fix_val(dm.volumes[v], "opacity")
        if "tally" in dm:
            del dm["tally"]
        if "energyReport" in dm:
            del dm["energyReport"]
        if "tally" in dm.openmcAnimation:
            dm.energyAnimation.tally = dm.openmcAnimation.tally
            dm.energyAnimation.score = dm.openmcAnimation.score
        for t in dm.settings.tallies:
            for i in range(1, sch.constants.maxFilters + 1):
                f = t[f"filter{i}"]
                y = f._type
                if y != "None":
                    cls.update_model_defaults(f, y)
        for s in dm.settings.sources:
            cls.update_model_defaults(s, "source")
        if "threshold" in dm.openmcAnimation:
            del dm["openmcAnimation"]["threshold"]
        for m, f in (
            ("tallyReport", "planePos"),
            ("openmcAnimation", "opacity"),
            ("geometry3DReport", "opacity"),
            ("openmcAnimation", "thresholds"),
            ("openmcAnimation", "energyRangeSum"),
        ):
            _fix_val(dm[m], f)
        if "tally" in dm.weightWindows and not isinstance(dm.weightWindows.tally, str):
            del dm.weightWindows["tally"]

    @classmethod
    def _compute_job_fields(cls, data, *args, **kwargs):
        return []

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model == "geometry3DReport":
            return "dagmcAnimation"
        if analysis_model == "energyAnimation":
            return "openmcAnimation"
        return analysis_model

    @classmethod
    def _lib_file_basenames(cls, data):
        r = []
        if data.get("report") == "tallyReport":
            return r
        if data.models.geometryInput.dagmcFile:
            r = [
                cls.dagmc_filename(data),
            ] + cls.source_filenames(data)
        if data.get("report") == "dagmcAnimation":
            if data.models.geometryInput.materialsFile:
                r.append(cls.materials_filename(data))
        return r

    @classmethod
    def _sim_file_basenames(cls, data):
        res = []
        if data.report == "openmcAnimation":
            for v in data.models.volumes:
                res.append(PKDict(basename=f"{data.models.volumes[v].volId}.ply"))
        return res
