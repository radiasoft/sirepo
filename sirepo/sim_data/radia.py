# -*- coding: utf-8 -*-
"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import copy
import os.path
import re
import pykern.pkio
import sirepo.sim_data
import sirepo.util


class SimData(sirepo.sim_data.SimDataBase):
    ANALYSIS_ONLY_FIELDS = frozenset(
        (
            "alpha",
            "bgColor",
            "color",
            "colorMap",
            "name",
            "notes",
            "scaling",
        )
    )

    @classmethod
    def prepare_import_file_args(cls, req):
        res = cls._prepare_import_file_name_args(req)
        if res.ext_lower != ".dat":
            raise sirepo.util.UserAlert(f"invalid file extension='{res.ext_lower}'")
        p = cls.lib_file_name_with_type(
            res.basename,
            cls.schema().constants.fileTypeRadiaDmp,
        )
        if cls.lib_file_exists(p, qcall=req.qcall):
            raise sirepo.util.UserAlert(
                f"dump file='{res.basename}' already exists; import another file name"
            )
        cls.lib_file_write(p, req.form_file.as_bytes(), qcall=req.qcall)
        # radia doesn't use import_file_arguments
        return res

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        res = cls._non_analysis_fields(data, r) + []
        return res

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model == "fieldLineoutAnimation":
            return "fieldLineoutAnimation"
        elif analysis_model in ("solverAnimation", "reset"):
            return "solverAnimation"
        elif analysis_model == "optimizerAnimation":
            return "optimizerAnimation"
        return super(SimData, cls)._compute_model(analysis_model, *args, **kwargs)

    @classmethod
    def __dynamic_defaults(cls, data, model):
        """defaults that depend on the current data"""
        return PKDict()

    @classmethod
    def _fixup_box_to_cuboid(cls, model, field):
        if model.get(field) == "box":
            model[field] = "cuboid"

    @classmethod
    def _fixup_examples(cls, models):
        sim = models.simulation
        if not sim.get("exampleName"):
            sim.exampleName = sim.name
        if sim.name in ("Parameterized C-Bend Dipole",):
            sim.beamAxis = "x"
            sim.heightAxis = "z"
            sim.widthAxis = "y"
        if sim.name == "Wiggler":
            models.geometryReport.isSolvable = "0"
            if not len(models.fieldPaths.paths):
                models.fieldPaths.paths.append(
                    PKDict(
                        _super="fieldPath",
                        begin=[0, -225, 0],
                        end=[0, 225, 0],
                        id=0,
                        name="y axis",
                        numPoints=101,
                        type="line",
                    )
                )

    @classmethod
    def _fixup_obj_types(cls, dm):
        if dm.get("box"):
            dm.cuboid = dm.box.copy()
            del dm["box"]
        for m in dm:
            for f in (
                "magnetObjType",
                "poleObjType",
                "type",
            ):
                if not hasattr(dm[m], "get"):
                    continue
                cls._fixup_box_to_cuboid(dm[m], f)
        for m in (
            "axisPath",
            "circlePath",
            "fieldMapPath",
            "filePath",
            "linePath",
            "manualPath",
        ):
            if dm.get(m):
                dm[m].type = m
        for o in dm.geometryReport.objects:
            if o.get("model") and not o.get("type"):
                o.type = o.get("model")
            for f in (
                "model",
                "type",
            ):
                cls._fixup_box_to_cuboid(o, f)

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        import sirepo.util

        sch = cls.schema()

        def _delete_old_fields(model):
            for f in ("divisions",):
                if model.get(f):
                    del model[f]

        def _fixup_array(model, model_type_field, model_field):
            for o in model.get(model_field, []):
                if model_type_field not in o:
                    continue
                _fixup_number_string_fields(o[model_type_field], o)
                _fixup_array(o, model_type_field, model_field)

        def _fixup_boolean_fields(model_name, model):
            s_m = sch.model[model_name]
            for f in [
                f for f in s_m if f in model and s_m[f][1] == "Boolean" and not model[f]
            ]:
                model[f] = "0"

        def _fixup_field_paths(paths):
            for p in paths:
                if not p.type.endswith("Path"):
                    p.type = f"{p.type}Path"
                for f in (
                    "begin",
                    "end",
                ):
                    _fixup_number_string_field(p, f)
                if p.type == "fieldMapPath":
                    if p.numPoints < sch.model.fieldMapPath.numPoints[4]:
                        p.numPoints = sch.model.fieldMapPath.numPoints[4]
                    if p.numPoints > sch.model.fieldMapPath.numPoints[5]:
                        p.numPoints = sch.model.fieldMapPath.numPoints[5]

        def _fixup_number_string_field(model, field, to_type=float):
            if field not in model:
                return
            if isinstance(model[field], str):
                model[field] = sirepo.util.split_comma_delimited_string(
                    model[field], to_type
                )

        def _fixup_number_string_fields(model_name, model):
            if not model_name or not model:
                return
            s_m = sch.model.get(model_name)
            if not s_m:
                return
            for f in model:
                if f not in s_m:
                    continue
                sf = s_m[f][1]
                if sf == "FloatArray":
                    _fixup_number_string_field(model, f)
                    continue
                if sf == "IntArray":
                    _fixup_number_string_field(model, f, to_type=int)
                    continue
                if sf.startswith("model."):
                    _fixup_number_string_fields(sf.split(".")[-1], model[f])
                    _fixup_transforms(model[f])
            sc = [x for x in s_m.get("_super", []) if x != "_" and x != "model"]
            if sc:
                _fixup_number_string_fields(sc[0], model)

        def _fixup_geom_objects(objects):
            for o in objects:
                o.name = re.sub(r"\s", "_", o.name)
                if o.get("points") is not None and not o.get("triangulationLevel"):
                    o.triangulationLevel = 0.5
                if not o.get("bevels"):
                    o.bevels = []
                for b in o.bevels:
                    if not b.get("cutRemoval"):
                        b["cutRemoval"] = "1"
                if not o.get("fillets"):
                    o.fillets = []
                if not o.get("materialFormula"):
                    o.materialFormula = [0, 0, 0, 0, 0, 0]
                if not o.get("modifications"):
                    o.modifications = o.bevels + o.fillets
                for m in o.modifications:
                    if m.get("amountHoriz") is not None:
                        m.type = "objectBevel"
                    if m.get("radius") is not None:
                        m.type = "objectFillet"
                    for d in ("heightDir", "widthDir"):
                        if d in m:
                            del m[d]
                for f in (
                    "type",
                    "model",
                ):
                    _fixup_number_string_fields(o.get(f), o)
                # fix "orphan" fields
                for f in (
                    "center",
                    "magnetization",
                    "segments",
                    "size",
                ):
                    _fixup_number_string_field(o, f)
                _fixup_segmentation(o)
                _fixup_terminations(o)
                _fixup_transforms(o)
                _delete_old_fields(o)

        def _fixup_segmentation(model):
            if not model.get("segments"):
                model.segments = model.get("division", [1, 1, 1])
            if not model.get("segmentation"):
                if model.get("type") == "cylinder":
                    model.segmentation = "cyl"
                    model.segmentationCylAxis = model.extrusionAxis
                    model.segmentationCylPoint = model.center
                    model.segmentationCylRadius = model.radius
                else:
                    model.segmentation = "pln"
            if not model.get("segmentationCylAxis"):
                model.segmentationCylAxis = "z"
            if not model.get("segmentationCylPoint"):
                model.segmentationCylPoint = [0, 0, 0]
            if not model.get("segmentationCylRadius"):
                model.segmentationCylRadius = 5.0
            if not model.get("segmentationCylRatio"):
                model.segmentationCylRatio = 1.0
            if not model.get("segmentationCylUseObjectCenter"):
                model.segmentationCylUseObjectCenter = "0"

        def _fixup_terminations(model):
            for t in filter(
                lambda x: x,
                map(lambda x: x.get("object"), model.get("terminations", [])),
            ):
                _fixup_number_string_fields(t.get("type"), t)

        def _fixup_transforms(model):
            _fixup_array(model, "model", "transforms")
            for t in model.get("transforms", []):
                if "model" in t:
                    t.type = t.model
                for c in t.get("transforms", []):
                    for ct in ("rotate", "translate"):
                        if c.get("model") == f"{ct}Clone":
                            c.type = ct

        dm = data.models
        cls._init_models(dm, None, dynamic=lambda m: cls.__dynamic_defaults(data, m))
        if dm.simulation.get("dmpImportFile"):
            dm.simulation.appMode = "imported"
        if dm.get("geometry"):
            dm.geometryReport = dm.geometry.copy()
            del dm["geometry"]
        if dm.get("solver"):
            dm.solverAnimation = dm.solver.copy()
            del dm["solver"]
        if "fieldPaths" not in dm:
            dm.fieldPaths = cls.update_model_defaults(PKDict(), "fieldPaths")
        if not dm.fieldPaths.get("paths"):
            dm.fieldPaths.paths = []
        if dm.fieldPaths.get("path"):
            dm.fieldPaths.selectedPath = dm.fieldPaths.path
            del dm.fieldPaths["path"]
        if dm.simulation.get("isExample"):
            cls._fixup_examples(dm)
        dm.simulation.areObjectsUnlockable = dm.simulation.magnetType == "freehand"
        if dm.simulation.magnetType == "undulator":
            cls._fixup_undulator(dm)
        cls._fixup_obj_types(dm)
        _fixup_geom_objects(dm.geometryReport.objects)
        _fixup_field_paths(dm.fieldPaths.paths)
        for name in [name for name in dm if name in sch.model]:
            _delete_old_fields(dm[name])
            _fixup_boolean_fields(name, dm[name])
            _fixup_number_string_fields(name, dm[name])
            _fixup_terminations(dm[name])
            _fixup_transforms(dm[name])
        cls._organize_example(data)

    @classmethod
    def _fixup_undulator(cls, dm):
        import sirepo.util

        if not dm.simulation.get("heightAxis"):
            dm.simulation.heightAxis = "z"

        if not dm.simulation.get("coordinateSystem"):
            dm.simulation.coordinateSystem = "beam"

        if "hybridUndulator" in dm:
            dm.undulatorHybrid = copy.deepcopy(dm.hybridUndulator)
            del dm["hybridUndulator"]
            dm.simulation.undulatorType = "undulatorHybrid"
            dm.undulatorHybrid.undulatorType = "undulatorHybrid"

        if dm.undulatorHybrid._super == "undulator":
            dm.undulatorHybrid._super = "undulatorBasic"

        if dm.simulation.undulatorType == "undulatorBasic":
            return

        u = dm.undulatorHybrid
        g = dm.geometryReport

        for k, v in PKDict(
            halfPole="Half Pole",
            magnet="Magnet Block",
            pole="Pole",
            corePoleGroup="Magnet-Pole Pair",
            terminationGroup="Termination",
            octantGroup="Octant",
        ).items():
            if k not in u:
                u[k] = sirepo.util.find_obj(g.objects, "name", v)

        if not u.get("terminations"):
            u.terminations = [PKDict() for _ in range(len(u.terminationGroup.members))]
        for i, t_id in enumerate(u.terminationGroup.members):
            t = u.terminations[i]
            cls.update_model_defaults(t, "termination")
            t.object = sirepo.util.find_obj(g.objects, "id", t_id)

    @classmethod
    def sim_files_to_run_dir(cls, data, run_dir, post_init=False):
        try:
            super().sim_files_to_run_dir(data, run_dir)
        except Exception as e:
            if not pykern.pkio.exception_is_not_found(e):
                raise
            if post_init:
                raise e

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        if "dmpImportFile" in data.models.simulation:
            res.append(
                f"{cls.schema().constants.fileTypeRadiaDmp}.{data.models.simulation.dmpImportFile}"
            )
        if "fieldType" in data:
            res.append(
                cls.lib_file_name_with_model_field(
                    "fieldPath", data.fieldType, data.name + "." + data.fileType
                )
            )
        for o in filter(
            lambda x: "pointsFile" in x, data.models.geometryReport.objects
        ):
            res.append(
                cls.lib_file_name_with_model_field(
                    "extrudedPoints", "pointsFile", o.pointsFile
                )
            )
        for o in filter(
            lambda x: x.get("type") == "stl" and "file" in x,
            data.models.geometryReport.objects,
        ):
            res.append(cls.lib_file_name_with_model_field("stl", "file", o.file))

        return res

    @classmethod
    def _sim_file_basenames(cls, data):
        # TODO(e-carlin): share filename with template
        return [
            PKDict(basename="geometry.dat"),
            PKDict(basename="geometryReport.h5"),
        ]
