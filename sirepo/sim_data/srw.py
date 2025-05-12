"""simulation data operations

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import math
import numpy
import re
import sirepo.sim_data


class SimData(sirepo.sim_data.SimDataBase):
    ANALYSIS_ONLY_FIELDS = frozenset(
        (
            "aspectRatio",
            "colorMap",
            "copyCharacteristic",
            "horizontalOffset",
            "horizontalSize",
            "intensityPlotsWidth",
            "maxIntensityLimit",
            "minIntensityLimit",
            "notes",
            "plotAxisX",
            "plotAxisY",
            "plotAxisY2",
            "plotScale",
            "rotateAngle",
            "rotateReshape",
            "showPlotSize",
            "useIntensityLimits",
            "usePlotRange",
            "verticalOffset",
            "verticalSize",
        )
    )

    EXPORT_RSOPT = "exportRsOpt"
    ML_REPORT = "machineLearningAnimation"
    ML_OUTPUT = "results.h5"

    SRW_RUN_ALL_MODEL = "simulation"

    __EXAMPLE_FOLDERS = PKDict(
        {
            "Bending Magnet Radiation": "/SR Calculator",
            "Diffraction by an Aperture": "/Wavefront Propagation",
            "Ellipsoidal Undulator Example": "/Examples",
            "Focusing Bending Magnet Radiation": "/Examples",
            "Gaussian X-ray Beam Through Perfect CRL": "/Examples",
            "Gaussian X-ray beam through a Beamline containing Imperfect Mirrors": "/Examples",
            "Idealized Free Electron Laser Pulse": "/SR Calculator",
            "LCLS SXR beamline - Simplified": "/Light Source Facilities/LCLS",
            "LCLS SXR beamline": "/Light Source Facilities/LCLS",
            "NSLS-II CHX beamline": "/Light Source Facilities/NSLS-II/NSLS-II CHX beamline",
            "Polarization of Bending Magnet Radiation": "/Examples",
            "Soft X-Ray Undulator Radiation Containing VLS Grating": "/Examples",
            "Tabulated Undulator Example": "/Examples",
            "Undulator Radiation": "/SR Calculator",
            "Young's Double Slit Experiment (green laser)": "/Wavefront Propagation",
            "Young's Double Slit Experiment (green laser, no lens)": "/Wavefront Propagation",
            "Young's Double Slit Experiment": "/Wavefront Propagation",
        }
    )

    _MATERIAL_FIELDS = PKDict(
        crl=["material"],
        fiber=["externalMaterial", "coreMaterial"],
        mask=["material"],
        sample=["material"],
        zonePlate=["mainMaterial", "complementaryMaterial"],
    )

    SRW_FILE_TYPE_EXTENSIONS = PKDict(
        {
            "mirror": ["dat", "txt"],
            "sample": ["tif", "tiff", "png", "bmp", "gif", "jpg", "jpeg"],
            "undulatorTable": ["zip"],
            "arbitraryField": ["dat", "txt"],
            "multiElectronAnimation-coherentModesFile": ["h5"],
        }
    )

    @classmethod
    def _compute_model(cls, analysis_model, *args, **kwargs):
        if analysis_model in ("coherenceXAnimation", "coherenceYAnimation"):
            # degree of coherence reports are calculated out of the multiElectronAnimation directory
            return "multiElectronAnimation"
        if "beamlineAnimation" in analysis_model:
            return "beamlineAnimation"
        if analysis_model == cls.EXPORT_RSOPT:
            return cls.EXPORT_RSOPT
        # SRW is different: it doesn't translate *Animation into animation
        return analysis_model

    @classmethod
    def does_api_reply_with_file(cls, api, method):
        # TODO(robnagler) move this to the schema so Javascript can use
        return api in "api_statefulCompute" and method == "sample_preview"

    @classmethod
    def fixup_old_data(cls, data, qcall, **kwargs):
        """Fixup data to match the most recent schema."""
        dm = data.models
        has_electron_beam_position = "electronBeamPosition" in dm
        x = (
            "arbitraryMagField",
            "beamline3DReport",
            "brillianceReport",
            "coherenceXAnimation",
            "coherenceYAnimation",
            "coherentModesAnimation",
            "electronBeamPosition",
            "fluxAnimation",
            "fluxReport",
            "gaussianBeam",
            "initialIntensityReport",
            "intensityReport",
            "machineLearningAnimation",
            "mirrorReport",
            "multipole",
            "exportRsOpt",
            "powerDensityReport",
            "simulation",
            "sourceIntensityReport",
            "tabulatedUndulator",
            "trajectoryReport",
        )
        cls._init_models(dm, x)
        for m in x:
            if "intensityPlotsScale" in dm[m]:
                dm[m].plotScale = dm[m].intensityPlotsScale
                del dm[m]["intensityPlotsScale"]
        for m in list(dm):
            if cls.is_watchpoint(m):
                cls.update_model_defaults(dm[m], cls.WATCHPOINT_REPORT)
                n = "beamlineAnimation{}".format(cls.watchpoint_id(m))
                if n not in dm:
                    dm[n] = dm[m]
            if m == "initialIntensityReport" and "beamlineAnimation0" not in dm:
                dm.beamlineAnimation0 = dm[m]
                if "fieldUnits" in dm[m]:
                    dm.simulation.fieldUnits = dm[m].fieldUnits
                    del dm[m]["fieldUnits"]
            if "beamlineAnimation" in m:
                cls.update_model_defaults(dm[m], cls.WATCHPOINT_REPORT)
        # default sourceIntensityReport.method based on source type
        if "method" not in dm.sourceIntensityReport:
            if cls.srw_is_undulator_source(dm.simulation):
                dm.sourceIntensityReport.method = "1"
            elif cls.srw_is_dipole_source(dm.simulation):
                dm.sourceIntensityReport.method = "2"
            elif cls.srw_is_arbitrary_source(dm.simulation):
                dm.sourceIntensityReport.method = "2"
            else:
                dm.sourceIntensityReport.method = "0"
        if "method" not in dm.simulation:
            dm.simulation.method = dm.sourceIntensityReport.method
        cls.update_model_defaults(dm.multiElectronAnimation, "multiElectronAnimation")
        cls.__fixup_old_data_beamline(data, qcall)
        cls.__fixup_old_data_by_template(data, qcall)
        hv = (
            "horizontalPosition",
            "horizontalRange",
            "verticalPosition",
            "verticalRange",
        )
        if "name" not in dm["tabulatedUndulator"]:
            u = dm.tabulatedUndulator
            u.name = u.undulatorSelector = "Undulator"
        if dm.tabulatedUndulator.get("id", "1") == "1":
            dm.tabulatedUndulator.id = "{} 1".format(dm.simulation.simulationId)
        if cls.srw_is_gaussian_source(dm.simulation):
            cls.__fixup_gaussian_divergence(dm.gaussianBeam)
        if "distribution" in dm.multipole:
            dm.multipole.bx = (
                dm.multipole.field if dm.multipole.distribution == "s" else 0
            )
            dm.multipole.by = (
                dm.multipole.field if dm.multipole.distribution == "n" else 0
            )
            del dm.multipole["distribution"]
            del dm.multipole["field"]
        if "distanceFromSource" not in dm.coherentModesAnimation:
            cs = cls.schema().model.coherentModesAnimation
            si = dm.sourceIntensityReport
            for f in cs:
                if f not in dm.coherentModesAnimation and f in si:
                    dm.coherentModesAnimation[f] = si[f]
        cls._organize_example(data)

    @classmethod
    def lib_file_name_with_type(cls, filename, file_type):
        return filename

    @classmethod
    def lib_file_name_without_type(cls, filename):
        return filename

    @classmethod
    def lib_file_names_for_type(cls, file_type, qcall=None):
        return sorted(
            cls.srw_lib_file_paths_for_type(
                file_type,
                lambda f: cls.srw_is_valid_file(file_type, f) and f.basename,
                want_user_lib_dir=True,
                qcall=qcall,
            ),
        )

    @classmethod
    def is_for_ml(cls, report):
        return report == cls.ML_REPORT

    @classmethod
    def is_for_rsopt(cls, report):
        return report == cls.EXPORT_RSOPT or cls.is_for_ml(report)

    @classmethod
    def is_run_mpi(cls, data):
        return (
            cls.is_parallel(data)
            and data.report != "beamlineAnimation"
            and not cls.is_for_ml(data.report)
        )

    @classmethod
    def _organize_example(cls, data):
        dm = data.models
        if dm.simulation.get("isExample"):
            f = cls.__EXAMPLE_FOLDERS.get(dm.simulation.name)
            if f:
                dm.simulation.folder = f
        elif not dm.simulation.get("folder"):
            dm.simulation.folder = "/"

    @classmethod
    def srw_compute_crystal_grazing_angle(cls, model):
        model.grazingAngle = math.acos(math.sqrt(1 - model.tvx**2 - model.tvy**2)) * 1e3

    @classmethod
    def srw_find_closest_angle(cls, angle, allowed_angles):
        """Find closest string value from the input list to
        the specified angle (in radians).
        """

        def _wrap(a):
            """Convert an angle to constraint it between -pi and pi.
            See https://stackoverflow.com/a/29237626/4143531 for details.
            """
            return numpy.arctan2(numpy.sin(a), numpy.cos(a))

        angles = numpy.array([float(x) for x in allowed_angles])
        threshold = numpy.min(numpy.diff(angles))
        return allowed_angles[
            numpy.where(numpy.abs(_wrap(angle) - angles) < threshold / 2.0)[0][0]
        ]

    @classmethod
    def srw_format_float(cls, v):
        return float("{:.8f}".format(v))

    @classmethod
    def srw_is_arbitrary_source(cls, sim):
        return sim.sourceType == "a"

    @classmethod
    def srw_is_background_report(cls, report):
        return "Animation" in report

    @classmethod
    def srw_is_beamline_report(cls, report):
        return (
            not report
            or cls.is_watchpoint(report)
            or report in ("multiElectronAnimation", cls.SRW_RUN_ALL_MODEL)
            or report == "beamline3DReport"
            or cls.is_for_rsopt(report)
        )

    @classmethod
    def srw_is_dipole_source(cls, sim):
        return sim.sourceType == "m"

    @classmethod
    def srw_is_gaussian_source(cls, sim):
        return sim.sourceType == "g"

    @classmethod
    def srw_is_idealized_undulator(cls, source_type, undulator_type):
        return source_type == "u" or (source_type == "t" and undulator_type == "u_i")

    @classmethod
    def srw_is_tabulated_undulator_source(cls, sim):
        return sim.sourceType == "t"

    @classmethod
    def srw_is_tabulated_undulator_with_magnetic_file(cls, source_type, undulator_type):
        return source_type == "t" and undulator_type == "u_t"

    @classmethod
    def srw_is_undulator_source(cls, sim):
        return sim.sourceType in ("u", "t")

    @classmethod
    def srw_is_user_defined_model(cls, model):
        return not model.get("isReadOnly", False)

    @classmethod
    def srw_is_valid_file(cls, file_type, path):
        # special handling for mirror and arbitraryField - scan for first data row and count columns
        if file_type not in ("mirror", "arbitraryField"):
            return True

        _ARBITRARY_FIELD_COL_COUNT = 3

        with pkio.open_text(path) as f:
            for line in f:
                if re.search(r"^\s*#", line):
                    continue
                c = len(line.split())
                if c > 0:
                    if file_type == "arbitraryField":
                        return c == _ARBITRARY_FIELD_COL_COUNT
                    return c != _ARBITRARY_FIELD_COL_COUNT
        return False

    @classmethod
    def srw_is_valid_file_type(cls, file_type, path):
        return path.ext[1:] in cls.SRW_FILE_TYPE_EXTENSIONS.get(file_type, tuple())

    @classmethod
    def srw_lib_file_paths_for_type(cls, file_type, op, want_user_lib_dir, qcall=None):
        """Search for files of type"""
        res = []
        for e in cls.SRW_FILE_TYPE_EXTENSIONS[file_type]:
            for f in cls._lib_file_list(
                f"*.{e}",
                want_user_lib_dir=want_user_lib_dir,
                qcall=qcall,
            ):
                x = op(f)
                if x:
                    res.append(x)
        return res

    @classmethod
    def srw_uses_tabulated_zipfile(cls, data):
        return cls.srw_is_tabulated_undulator_with_magnetic_file(
            data.models.simulation.sourceType,
            data.models.tabulatedUndulator.undulatorType,
        )

    @classmethod
    def want_browser_frame_cache(cls, report):
        if "beamlineAnimation" in report:
            return True
        return False

    @classmethod
    def _compute_job_fields(cls, data, r, compute_model):
        if r == "mirrorReport":
            return [
                "mirrorReport.heightProfileFile",
                "mirrorReport.orientation",
                "mirrorReport.grazingAngle",
                "mirrorReport.heightAmplification",
            ]
        res = []
        if r == "beamline3DReport":
            res.append("beamline")
        else:
            res += cls._non_analysis_fields(data, r)
        res += [
            "electronBeam",
            "electronBeamPosition",
            "gaussianBeam",
            "multipole",
            "simulation.sourceType",
            "tabulatedUndulator",
            "undulator",
            "arbitraryMagField",
        ]
        watchpoint = cls.is_watchpoint(r)
        if watchpoint or r == "initialIntensityReport" or r == "beamline3DReport":
            res.extend(
                [
                    "simulation.horizontalPointCount",
                    "simulation.horizontalPosition",
                    "simulation.horizontalRange",
                    "simulation.photonEnergy",
                    "simulation.sampleFactor",
                    "simulation.samplingMethod",
                    "simulation.verticalPointCount",
                    "simulation.verticalPosition",
                    "simulation.verticalRange",
                    "simulation.distanceFromSource",
                ]
            )
        if r == "initialIntensityReport":
            beamline = data["models"]["beamline"]
            res.append([beamline[0]["position"] if beamline else 0])
        if watchpoint:
            wid = cls.watchpoint_id(r)
            beamline = data["models"]["beamline"]
            propagation = data["models"]["propagation"]
            for item in beamline:
                item_copy = item.copy()
                del item_copy["title"]
                res.append(item_copy)
                res.append(propagation[str(item["id"])])
                if item["type"] == "watch" and item["id"] == wid:
                    break
            if beamline[-1]["id"] == wid:
                res.append("postPropagation")
        return res

    @classmethod
    def _lib_file_basenames(cls, data):
        res = []
        dm = data.models
        # the mirrorReport.heightProfileFile may be different than the file in the beamline
        r = data.get("report")
        if r == "mirrorReport":
            res.append(dm.mirrorReport.heightProfileFile)
        elif r == "multiElectronAnimation" and dm[r].wavefrontSource == "cmd":
            if dm[r].coherentModesFile:
                res.append(dm[r].coherentModesFile)
        if cls.srw_uses_tabulated_zipfile(data):
            if "tabulatedUndulator" in dm and dm.tabulatedUndulator.get("magneticFile"):
                res.append(dm.tabulatedUndulator.magneticFile)
        if cls.srw_is_arbitrary_source(dm.simulation):
            res.append(dm.arbitraryMagField.magneticFile)
        if cls.srw_is_beamline_report(r) or r == "beamlineAnimation":
            s = cls.schema()
            for m in dm.beamline:
                for k, v in s.model[m.type].items():
                    if k not in m:
                        # field may be missing and fixups are not applied
                        # until sim is loaded in prepare_for_client()
                        continue
                    t = v[1]
                    if m[k] and t in ("MirrorFile", "ImageFile"):
                        res.append(m[k])
        return res

    @classmethod
    def __fixup_gaussian_divergence(cls, beam):
        # TODO(pjm): keep in sync with srw.js convertGBSize()
        def convert_gb_size(field, energy):
            energy = float(energy)
            value = float(beam[field])
            if not value or not energy:
                return 0
            waveLength = (1239.84193e-9) / energy
            factor = waveLength / (4 * math.pi)
            return factor / (value * 1e-6) * 1e6

        if beam.sizeDefinition == "1" and not beam.rmsDivergenceX:
            beam.rmsDivergenceX = convert_gb_size("rmsSizeX", beam.photonEnergy)
            beam.rmsDivergenceY = convert_gb_size("rmsSizeY", beam.photonEnergy)

    @classmethod
    def __fixup_old_data_by_template(cls, data, qcall):
        import sirepo.template.srw_fixup
        import sirepo.template.srw

        sirepo.template.srw_fixup.do(sirepo.template.srw, data, qcall=qcall)

    @classmethod
    def __fixup_old_data_beamline(cls, data, qcall):
        dm = data.models
        e = float(dm.simulation.photonEnergy)
        er = cls.schema().constants.materialEnergyRange
        for i in dm.beamline:
            t = i.type
            if t == "crl":
                for k, v in PKDict(
                    material="User-defined",
                    method="server",
                    absoluteFocusPosition=None,
                    focalDistance=None,
                    tipRadius=float(i.get("radius", 0)) * 1e6,  # m -> um
                    tipWallThickness=float(i.get("wallThickness", 0)) * 1e6,  # m -> um
                ).items():
                    if k not in i:
                        i[k] = v
                if i.method == "calculation" and i.method != "file":
                    i.method = "file"
            if t == "crystal":
                # this is a hack for existing bad data
                for k in [
                    "outframevx",
                    "outframevy",
                    "outoptvx",
                    "outoptvy",
                    "outoptvz",
                    "tvx",
                    "tvy",
                ]:
                    i[k] = float(i.get(k, 0))
                if "transmissionImage" not in i:
                    i.transmissionImage = cls.schema().model.sample.transmissionImage[2]
            if t == "grating":
                if not i.get("energyAvg"):
                    i.energyAvg = dm.simulation.photonEnergy
            if t in cls._MATERIAL_FIELDS and (e < er[0] or e > er[1]):
                for f in cls._MATERIAL_FIELDS[t]:
                    i[f] = cls.schema().enum.CRLMaterial[0][0]
            cls.update_model_defaults(i, t)
