"""SRW execution template.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import crystal
from sirepo import simulation_db
from sirepo.template import srw_common
from sirepo.template import template_common
import array
import copy
import glob
import math
import numpy as np
import os
import pickle
import re
import sirepo.mpi
import sirepo.sim_data
import sirepo.sim_run
import sirepo.util
import srwpy.srwl_bl
import srwpy.srwlib
import srwpy.srwlpy
import srwpy.uti_io
import srwpy.uti_math
import srwpy.uti_plot_com
import time
import traceback
import zipfile

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

PARSED_DATA_ATTR = "srwParsedData"

_CANVAS_MAX_SIZE = 65535
_LOG_DIR = "__srwl_logs__"
_MAX_REPORT_POINTS = 20000000
_MIN_CORES = 3

_OUTPUT_FOR_MODEL = PKDict(
    coherenceXAnimation=PKDict(
        title="",
        filename="res_int_pr_me_dcx.dat",
        dimensions=3,
        labels=["(X1 + X2) / 2", "(X1 - X2) / 2", "Degree of Coherence"],
        units=["m", "m", ""],
    ),
    coherenceYAnimation=PKDict(
        title="",
        filename="res_int_pr_me_dcy.dat",
        dimensions=3,
        labels=["(Y1 + Y2) / 2", "(Y1 - Y2) / 2", "Degree of Coherence"],
        units=["m", "m", ""],
    ),
    coherentModesAnimation=PKDict(
        title="Coherent Modes, {position} (E={photonEnergyWithUnits}) Modes {plotModesStart} - {plotModesEnd}",
        basename="res_csd",
        filename="res_csd_cm.h5",
        dimensions=3,
        labels=["Horizontal Position", "Vertical Position", "Intensity"],
        units=["m", "m", "ph/s/.1%bw/mm^2"],
    ),
    fluxReport=PKDict(
        title="Flux through Finite Aperture, {position}",
        subtitle="{polarization} Polarization",
        filename="res_spec_me.dat",
        dimensions=2,
    ),
    initialIntensityReport=PKDict(
        title="Initial Intensity, {position} (E={photonEnergyWithUnits})",
        subtitle="{characteristic}",
        filename="res_int_se.dat",
        dimensions=3,
        special_z_units=True,
    ),
    intensityReport=PKDict(
        title="On-Axis Spectrum from Filament Electron Beam, {position}",
        subtitle="{polarization} Polarization",
        filename="res_spec_se.dat",
        dimensions=2,
    ),
    mirrorReport=PKDict(
        title="Optical Path Difference",
        filename="res_mirror.dat",
        dimensions=3,
        labels=["Horizontal Position", "Vertical Position", "Optical Path Difference"],
        units=["m", "m", "m"],
    ),
    multiElectronAnimation=PKDict(
        title="Intensity {name}, {position} (E={photonEnergyWithUnits})",
        filename="res_int_pr_me.dat",
        dimensions=3,
    ),
    powerDensityReport=PKDict(
        title="Power Density, {position}",
        filename="res_pow.dat",
        dimensions=3,
    ),
    brillianceReport=PKDict(
        filename="res_brilliance.dat",
        dimensions=2,
    ),
    trajectoryReport=PKDict(
        filename="res_trj.dat",
        dimensions=2,
    ),
    beamline3DReport=PKDict(
        filename="beamline_orient.dat",
        dimensions=2,
    ),
    watchpointReport=PKDict(
        title="Intensity {name}, {position} (E={photonEnergyWithUnits})",
        subtitle="{characteristic}",
        filename="res_int_pr_se.dat",
        dimensions=3,
        special_z_units=True,
    ),
)
_OUTPUT_FOR_MODEL[f"{_SIM_DATA.EXPORT_RSOPT}"] = PKDict(
    filename=f"{_SIM_DATA.EXPORT_RSOPT}.zip",
)
_OUTPUT_FOR_MODEL.machineLearningAnimation = PKDict(
    filename=_SIM_DATA.ML_OUTPUT,
)
_OUTPUT_FOR_MODEL.fluxAnimation = copy.deepcopy(_OUTPUT_FOR_MODEL.fluxReport)
_OUTPUT_FOR_MODEL.beamlineAnimation = copy.deepcopy(_OUTPUT_FOR_MODEL.watchpointReport)
_OUTPUT_FOR_MODEL.beamlineAnimation.filename = "res_int_pr_se{watchpoint_id}.dat"
_OUTPUT_FOR_MODEL.sourceIntensityReport = copy.deepcopy(
    _OUTPUT_FOR_MODEL.initialIntensityReport
)
_OUTPUT_FOR_MODEL.sourceIntensityReport.title = (
    "Intensity, {position} (E={sourcePhotonEnergyWithUnits})"
)

_PREPROCESS_PREFIX = "preproc-"

_RSOPT_PARAMS = {
    i
    for sublist in [
        v
        for v in [
            list(SCHEMA.constants.rsOptElements[k].keys())
            for k in SCHEMA.constants.rsOptElements
        ]
    ]
    for i in sublist
}
_RSOPT_PARAMS_NO_ROTATION = [p for p in _RSOPT_PARAMS if p != "rotation"]

_PROGRESS_LOG_DIR = "__srwl_logs__"

_TABULATED_UNDULATOR_DATA_DIR = "tabulatedUndulator"

_USER_MODEL_LIST_FILENAME = PKDict(
    electronBeam="_user_beam_list.json",
    tabulatedUndulator="_user_undulator_list.json",
)

_IMPORT_PYTHON_POLLS = 60

_PREDEFINED_BEAMS = None


class MagnMeasZip:
    def __init__(self, archive_name):
        """The class for convenient operation with an archive with the magnetic measurements.

        Args:
            archive_name: the name of the archive.
        """
        self.z = zipfile.ZipFile(archive_name)
        self.index_dir = None
        self.index_file = None
        self.gaps = None
        self.dat_files = None
        self._find_index_file()
        self._find_dat_files_from_index_file()

    def find_closest_gap(self, gap):
        gap = float(gap)
        indices_previous = []
        indices_next = []
        for i in range(len(self.gaps)):
            if self.gaps[i] <= gap:
                indices_previous.append(i)
            else:
                indices_next.append(i)
        assert indices_previous or indices_next
        idx_previous = indices_previous[-1] if indices_previous else indices_next[0]
        idx_next = indices_next[0] if indices_next else indices_previous[-1]
        idx = (
            idx_previous
            if abs(self.gaps[idx_previous] - gap) <= abs(self.gaps[idx_next] - gap)
            else idx_next
        )
        dat_file = self.dat_files[idx]
        dat_content = self._get_file_content(dat_file)
        dat_file_step = float(dat_content[8].split("#")[1].strip())
        dat_file_number_of_points = int(dat_content[9].split("#")[1].strip())
        return round(dat_file_step * dat_file_number_of_points, 6)

    def _find_dat_files_from_index_file(self):
        self.gaps = []
        self.dat_files = []
        for row in self._get_file_content(self.index_file):
            v = row.strip()
            if v:
                v = v.split()
                self.gaps.append(float(v[0]))
                self.dat_files.append(v[3])

    def _find_index_file(self):
        # finds an index file (``*.txt``) in the provided zip-object.
        for f in self.z.namelist():
            if re.search(r"\.txt", f):
                self.index_file = os.path.basename(f)
                self.index_dir = os.path.dirname(f)
                break
        assert self.index_file is not None

    def _get_file_content(self, file_name):
        with self.z.open(os.path.join(self.index_dir, file_name)) as f:
            return self._normalize_eol(f)

    def _normalize_eol(self, file_desc):
        s = file_desc.read().decode().replace("\r\n", "\n").replace("\r", "\n")
        content = s.split("\n")
        return content


def background_percent_complete(report, run_dir, is_running):
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    if report == "beamlineAnimation":
        return _beamline_animation_percent_complete(run_dir, res)
    if _SIM_DATA.is_for_ml(report):
        return _machine_learning_percent_complete(run_dir, res)
    status = PKDict(
        progress=0,
        particle_number=0,
        total_num_of_particles=0,
    )
    filename = run_dir.join(get_filename_for_model(report))
    if filename.exists():
        status.progress = 100
        t = int(filename.mtime())
        if not is_running and report == "fluxAnimation":
            # let the client know which flux method was used for the output
            data = simulation_db.read_json(
                run_dir.join(template_common.INPUT_BASE_NAME)
            )
            res.method = data.models.fluxAnimation.method
        if report == "multiElectronAnimation":
            # let client know that degree of coherence reports are also available
            res.calcCoherence = run_dir.join(
                get_filename_for_model("coherenceXAnimation")
            ).exists()
        res.update(
            PKDict(
                frameCount=t + 1,
                frameIndex=t,
                lastUpdateTime=t,
            )
        )
    status_files = pkio.sorted_glob(run_dir.join(_LOG_DIR, "srwl_*.json"))
    if status_files:  # Read the status file if SRW produces the multi-e logs
        progress_file = pkio.py_path(status_files[-1])
        if progress_file.exists():
            status = simulation_db.read_json(progress_file)
            res.update(
                PKDict(
                    percentComplete=status.progress,
                    particleNumber=status.particle_number,
                    particleCount=status.total_num_of_particles,
                )
            )
    return res


def calculate_beam_drift(
    ebeam_position, source_type, undulator_type, undulator_length, undulator_period
):
    if ebeam_position.driftCalculationMethod == "auto":
        """Calculate drift for ideal undulator."""
        if _SIM_DATA.srw_is_idealized_undulator(source_type, undulator_type):
            # initial drift = 1/2 undulator length + 2 periods
            return -0.5 * float(undulator_length) - 2 * float(undulator_period)
        return 0
    return ebeam_position.drift


def compute_undulator_length(model, qcall=None):
    if model.undulatorType == "u_i":
        return PKDict()
    if qcall and _SIM_DATA.lib_file_exists(model.magneticFile, qcall=qcall):
        z = _SIM_DATA.lib_file_abspath(model.magneticFile, qcall=qcall)
        return PKDict(
            length=_SIM_DATA.srw_format_float(
                MagnMeasZip(str(z)).find_closest_gap(model.gap),
            ),
        )
    return PKDict()


def clean_run_dir(run_dir):
    zip_dir = run_dir.join(_TABULATED_UNDULATOR_DATA_DIR)
    if zip_dir.exists():
        zip_dir.remove()


def export_filename(sim_filename, filename):
    if filename not in ("run.py", "sirepo-data.json"):
        return f"{sim_filename.replace('.zip', '')}/{filename}"
    return filename


def extract_report_data(sim_in):
    r = sim_in.report
    out = copy.deepcopy(_OUTPUT_FOR_MODEL[re.sub(r"\d+$", "", r)])
    dm = sim_in.models
    if r == "beamline3DReport":
        return _extract_beamline_orientation(out.filename)
    if r == "brillianceReport":
        return _extract_brilliance_report(dm.brillianceReport, out.filename)
    if r == "trajectoryReport":
        return _extract_trajectory_report(dm.trajectoryReport, out.filename)
    if r == _SIM_DATA.EXPORT_RSOPT:
        return out
    if r in ("coherenceXAnimation", "coherenceYAnimation", "multiElectronAnimation"):
        out.filename = _best_data_file(out.filename)
    # TODO(pjm): remove fixup after dcx/dcy files can be read by srwpy.uti_plot_com
    if r in ("coherenceXAnimation", "coherenceYAnimation"):
        _fix_file_header(out.filename)
    if r == "coherentModesAnimation":
        out.filename = _extract_coherent_modes(dm[r], out)
    wid = dm[r].get("id", 0)
    _update_report_labels(
        out,
        PKDict(
            name=_element_name(sim_in, wid),
            position=_element_position(sim_in, wid),
            photonEnergyWithUnits=_format_energy(dm.simulation.photonEnergy),
            sourcePhotonEnergyWithUnits=_format_energy(
                dm.sourceIntensityReport.photonEnergy
            ),
            photonEnergy=dm.simulation.photonEnergy,
            sourcePhotonEnergy=dm.sourceIntensityReport.photonEnergy,
            polarization=_enum_text("Polarization", dm[r], "polarization"),
            characteristic=_enum_text("Characteristic", dm[r], "characteristic"),
            watchpoint_id=wid,
            plotModesStart=dm[r].get("plotModesStart", ""),
            plotModesEnd=dm[r].get("plotModesEnd", ""),
        ),
    )
    points, _, allrange, labels, units = srwpy.uti_plot_com.file_load(out.filename)
    if (
        r == "multiElectronAnimation"
        and dm.multiElectronAnimation.photonEnergyBandWidth > 0
    ):
        # SRW sometimes reports this units wrong in this case
        units[3] = "ph/s/mm^2"

    if "labels" not in out:
        if out.dimensions == 3:
            out.labels = labels[1:]
            out.units = units[1:]
            if not out.labels[2]:
                out.labels[2] = "Intensity"
        elif out.dimensions == 2:
            out.labels = [labels[0], labels[3] or "Intensity"]
            out.units = [units[0], units[3]]

    if out.get("special_z_units"):
        out.units[2] = _intensity_units(sim_in)

    if out.units[1] in ("m", "rad"):
        out.units[1] = f"[{out.units[1]}]"
    else:
        out.units[1] = "({})".format(out.units[1])

    res = PKDict(
        title=out.title,
        subtitle=out.get("subtitle", ""),
        x_range=[allrange[0], allrange[1]],
        y_label=_superscript(out.labels[1] + " " + out.units[1]),
        x_label=out.labels[0] + " [" + out.units[0] + "]",
        x_units=out.units[0],
        y_units=out.units[1],
        points=points,
        z_range=[np.min(points), np.max(points)],
        # send the full plot ranges as summaryData
        summaryData=PKDict(
            fieldRange=allrange,
            fieldIntensityRange=dm[r]
            .get("summaryData", {})
            .get(
                "fieldIntensityRange",
                [0, 0] if np.isnan(points).all() else [np.min(points), np.max(points)],
            ),
        ),
    )
    if out.dimensions == 3:
        res.report = r
        res = _remap_3d(res, allrange, out, dm[r])
        res.z_footer = _plot_z_footer(res.z_label, allrange, points)
    return res


def get_data_file(run_dir, model, frame, options):
    if options.suffix == template_common.RUN_LOG:
        return template_common.text_data_file(options.suffix, run_dir)
    if options.suffix == _PROGRESS_LOG_DIR:
        d = run_dir.join(_PROGRESS_LOG_DIR)
        return template_common.text_data_file(
            _get_most_recent_log_file(pkio.sorted_glob(d.join("*.log"))), d
        )
    return _best_data_file(get_filename_for_model(model))


def get_filename_for_model(model):
    if _SIM_DATA.is_watchpoint(model):
        model = _SIM_DATA.WATCHPOINT_REPORT
    if model == "beamlineAnimation0":
        model = "initialIntensityReport"
    m = re.search(r"(beamlineAnimation)(\d+)", model)
    if m:
        return _OUTPUT_FOR_MODEL[m.group(1)].filename.format(watchpoint_id=m.group(2))
    return _OUTPUT_FOR_MODEL[model].filename


def get_predefined_beams():
    global _PREDEFINED_BEAMS

    def _calc():
        import srwpy.srwl_uti_src

        return [_calc_one(*x) for x in srwpy.srwl_uti_src.srwl_uti_src_e_beam_predef()]

    def _calc_one(name, info):
        return srw_common.process_beam_parameters(
            # info is:
            # _Iavg _e _sig_e _emit_x _beta_x _alpha_x _eta_x _eta_x_pr _emit_y _beta_y _alpha_y
            PKDict(
                name=name,
                current=info[0],
                energy=info[1],
                rmsSpread=info[2],
                horizontalEmittance=_SIM_DATA.srw_format_float(info[3] * 1e9),
                horizontalBeta=info[4],
                horizontalAlpha=info[5],
                horizontalDispersion=info[6],
                horizontalDispersionDerivative=info[7],
                verticalEmittance=_SIM_DATA.srw_format_float(info[8] * 1e9),
                verticalBeta=info[9],
                verticalAlpha=info[10],
                verticalDispersion=0,
                verticalDispersionDerivative=0,
                energyDeviation=0,
                horizontalPosition=0,
                verticalPosition=0,
                drift=0.0,
                isReadOnly=True,
            )
        )

    if not _PREDEFINED_BEAMS:
        _PREDEFINED_BEAMS = _calc()
    return _PREDEFINED_BEAMS


def sim_frame(frame_args):
    r = frame_args.frameReport
    frame_args.sim_in.report = r
    if r == "multiElectronAnimation":
        m = frame_args.sim_in.models[r]
        m.intensityPlotsWidth = frame_args.intensityPlotsWidth
        if frame_args.get("rotateAngle", 0):
            m.rotateAngle = float(frame_args.rotateAngle)
            m.rotateReshape = frame_args.rotateReshape
        else:
            m.rotateAngle = 0
    elif r == "coherentModesAnimation":
        _copy_frame_args_into_model(frame_args, r)
    elif "beamlineAnimation" in r:
        wid = int(re.search(r".*?(\d+)$", r)[1])
        fn = _wavefront_pickle_filename(wid, is_processed=True)
        with open(fn, "rb") as f:
            wfr = pickle.load(f)
        m = _copy_frame_args_into_model(frame_args, "watchpointReport")
        if wid:
            m.id = wid
            frame_args.sim_in.report = "beamlineAnimation"
            frame_args.sim_in.models.beamlineAnimation = m
            data_file = _OUTPUT_FOR_MODEL.beamlineAnimation.filename.format(
                watchpoint_id=wid
            )
        else:
            frame_args.sim_in.report = "initialIntensityReport"
            frame_args.sim_in.models.initialIntensityReport = m
            data_file = _OUTPUT_FOR_MODEL.initialIntensityReport.filename
        detector = None
        m = frame_args.sim_in.models[r]
        if str(m.get("useDetector", "0")) == "1":
            detector = srwpy.srwl_bl.SRWLBeamline().set_detector(
                _x=float(m.d_x),
                _y=float(m.d_y),
                _nx=int(m.d_nx),
                _ny=int(m.d_ny),
                _rx=float(m.d_rx),
                _ry=float(m.d_ry),
            )
        srwpy.srwl_bl.SRWLBeamline().calc_int_from_wfr(
            wfr,
            _pol=int(frame_args.polarization),
            _int_type=int(frame_args.characteristic),
            _fname=data_file,
            _pr=False,
            _det=detector,
        )
    if "beamlineAnimation" not in r:
        # some reports may be written at the same time as the reader
        # if the file is invalid, wait a bit and try again
        for i in (1, 2, 3):
            try:
                return extract_report_data(frame_args.sim_in)
            except Exception:
                # sleep and retry to work-around concurrent file read/write
                pkdlog("sleep and retry simulation frame read: {} {}", i, r)
                # Not asyncio.sleep: not in coroutine (job_cmd)
                time.sleep(2)
    return extract_report_data(frame_args.sim_in)


def new_simulation(data, new_simulation_data, qcall=None, **kwargs):
    def _sim_from_radia(models, d):
        for m in ("simulation", "tabulatedUndulator", "electronBeamPosition"):
            models[m].pkupdate(d[m])
        f = d.tabulatedUndulator.magneticFile
        t_basename = f"{d.sourceSimType}-{d.sourceSimId}-{f}"
        models.tabulatedUndulator.magneticFile = t_basename
        t = simulation_db.simulation_lib_dir(_SIM_DATA.sim_type(), qcall=qcall).join(
            t_basename
        )
        simulation_db.simulation_dir(
            d.sourceSimType, sid=d.sourceSimId, qcall=qcall
        ).join(f).copy(t)

    sim = data.models.simulation
    sim.sourceType = new_simulation_data.sourceType
    if new_simulation_data.get("sourceSimType") == "radia":
        _sim_from_radia(data.models, new_simulation_data)
    if _SIM_DATA.srw_is_dipole_source(sim) or _SIM_DATA.srw_is_arbitrary_source(sim):
        for m in (
            "coherentModesAnimation",
            "intensityReport",
            "simulation",
            "sourceIntensityReport",
        ):
            data.models[m].method = "2"
    elif _SIM_DATA.srw_is_tabulated_undulator_source(sim):
        data.models.undulator.length = compute_undulator_length(
            data.models.tabulatedUndulator,
            qcall=qcall,
        ).length
        data.models.electronBeamPosition.driftCalculationMethod = "manual"


def post_execution_processing(
    compute_model,
    run_dir,
    sim_id,
    success_exit,
    **kwargs,
):
    for f in glob.glob(str(run_dir.join(_PREPROCESS_PREFIX + "*"))):
        os.remove(f)
    if success_exit:
        if _SIM_DATA.is_for_ml(compute_model):
            f = _SIM_DATA.ML_OUTPUT
            _SIM_DATA.put_sim_file(sim_id, run_dir.join(f), f)
        return None
    return template_common.LogParser(run_dir).parse_for_errors()


def prepare_for_client(data, qcall, **kwargs):
    save = False
    for model_name in _USER_MODEL_LIST_FILENAME.keys():
        if (
            model_name == "tabulatedUndulator"
            and not _SIM_DATA.srw_is_tabulated_undulator_source(data.models.simulation)
        ):
            # don't add a named undulator if tabulated is not the current source type
            continue
        model = data.models[model_name]
        if _SIM_DATA.srw_is_user_defined_model(model):
            user_model_list = _load_user_model_list(model_name, qcall=qcall)
            search_model = None
            models_by_id = _user_model_map(user_model_list, "id")
            if "id" in model and model.id in models_by_id:
                search_model = models_by_id[model.id]
            if search_model:
                data.models[model_name] = search_model
                if model_name == "tabulatedUndulator":
                    del data.models[model_name]["undulator"]
            else:
                pkdc("adding model: {}", model.name)
                if model.name in _user_model_map(user_model_list, "name"):
                    model.name = _unique_name(
                        user_model_list, "name", model.name + " {}"
                    )
                    selectorName = (
                        "beamSelector"
                        if model_name == "electronBeam"
                        else "undulatorSelector"
                    )
                    model[selectorName] = model.name
                model.id = _unique_name(
                    user_model_list, "id", data.models.simulation.simulationId + " {}"
                )
                user_model_list.append(_create_user_model(data, model_name))
                _save_user_model_list(model_name, user_model_list, qcall=qcall)
                save = True
    if save:
        pkdc(
            "save simulation json with sim_data_template_fixup={}",
            data.get("sim_data_template_fixup", None),
        )
        simulation_db.save_simulation_json(data, fixup=True, qcall=qcall)
    return data


def prepare_for_save(data, qcall):
    for model_name in _USER_MODEL_LIST_FILENAME.keys():
        if (
            model_name == "tabulatedUndulator"
            and not _SIM_DATA.srw_is_tabulated_undulator_source(data.models.simulation)
        ):
            # don't add a named undulator if tabulated is not the current source type
            continue
        model = data.models[model_name]
        if _SIM_DATA.srw_is_user_defined_model(model):
            user_model_list = _load_user_model_list(model_name, qcall=qcall)
            models_by_id = _user_model_map(user_model_list, "id")

            if "id" not in model or model.id not in models_by_id:
                pkdc("adding new model: {}", model.name)
                if model.name in _user_model_map(user_model_list, "name"):
                    model.name = _unique_name(
                        user_model_list, "name", model.name + " {}"
                    )
                    selectorName = (
                        "beamSelector"
                        if model_name == "electronBeam"
                        else "undulatorSelector"
                    )
                    model[selectorName] = model.name
                model.id = _unique_name(
                    user_model_list, "id", data.models.simulation.simulationId + " {}"
                )
                user_model_list.append(_create_user_model(data, model_name))
                _save_user_model_list(model_name, user_model_list, qcall=qcall)
            elif models_by_id[model.id] != model:
                pkdc("replacing beam: {}: {}", model.id, model.name)
                for i, m in enumerate(user_model_list):
                    if m.id == model.id:
                        pkdc("found replace beam, id: {}, i: {}", m.id, i)
                        user_model_list[i] = _create_user_model(data, model_name)
                        _save_user_model_list(model_name, user_model_list, qcall=qcall)
                        break
    return data


def prepare_sequential_output_file(run_dir, sim_in):
    m = sim_in.report
    if m in ("brillianceReport", "mirrorReport"):
        return
    # TODO(pjm): only need to rerun extract_report_data() if report style fields have changed
    fn = simulation_db.json_filename(template_common.OUTPUT_BASE_NAME, run_dir)
    if fn.exists():
        fn.remove()
        output_file = run_dir.join(get_filename_for_model(m))
        if output_file.exists():
            res = extract_report_data(sim_in)
            template_common.write_sequential_result(res, run_dir=run_dir)


def process_undulator_definition(model):
    """Convert K -> B and B -> K."""
    try:
        if model.undulator_definition == "B":
            # Convert B -> K:
            und = srwpy.srwlib.SRWLMagFldU(
                [srwpy.srwlib.SRWLMagFldH(1, "v", float(model.amplitude), 0, 1)],
                float(model.undulator_period),
            )
            model.undulator_parameter = _SIM_DATA.srw_format_float(und.get_K())
        elif model.undulator_definition == "K":
            # Convert K to B:
            und = srwpy.srwlib.SRWLMagFldU([], float(model.undulator_period))
            model.amplitude = _SIM_DATA.srw_format_float(
                und.K_2_B(float(model.undulator_parameter)),
            )
        return model
    except Exception:
        return model


def process_watch(wid=0):
    def _resize_wavefront(wfr):
        mesh = wfr.mesh
        nx, ny = _resize_mesh_dimensions(mesh.nx, mesh.ny)
        pkdc("resized mesh: {}x{}", nx, ny)
        # resize the electic fields in the wavefront mesh - note it modifies wfr
        srwpy.srwlpy.ResizeElecFieldMesh(
            wfr,
            srwpy.srwlib.SRWLRadMesh(
                _eStart=mesh.eStart,
                _eFin=mesh.eFin,
                _ne=mesh.ne,
                _xStart=mesh.xStart,
                _xFin=mesh.xFin,
                _nx=nx,
                _yStart=mesh.yStart,
                _yFin=mesh.yFin,
                _ny=ny,
                _zStart=mesh.zStart,
                _nvx=mesh.nvx,
                _nvy=mesh.nvy,
                _nvz=mesh.nvz,
                _hvx=mesh.hvx,
                _hvy=mesh.hvy,
                _hvz=mesh.hvz,
                _arSurf=mesh.arSurf,
            ),
            [0, 1],
        )
        return wfr

    def _op():
        sim_in = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        report = sim_in.models[f"beamlineAnimation{wid}"]
        p = _wavefront_pickle_filename(wid)
        with open(p, "rb") as f:
            wfr = pickle.load(f)
        pkdc("original mesh: {}x{}", wfr.mesh.nx, wfr.mesh.ny)
        if (
            wfr.mesh.nx < _CANVAS_MAX_SIZE
            and wfr.mesh.ny < _CANVAS_MAX_SIZE
            and wfr.mesh.nx * wfr.mesh.ny <= _MAX_REPORT_POINTS
        ):
            pkio.py_path(p).copy(
                pkio.py_path(_wavefront_pickle_filename(wid, is_processed=True))
            )
        else:
            with open(_wavefront_pickle_filename(wid, is_processed=True), "wb") as f:
                pickle.dump(_resize_wavefront(wfr), f)

    sirepo.mpi.restrict_op_to_first_rank(_op)


def python_source_for_model(data, model, qcall, plot_reports=True, **kwargs):
    data.report = model or _SIM_DATA.SRW_RUN_ALL_MODEL
    data.report = re.sub("beamlineAnimation0", "initialIntensityReport", data.report)
    data.report = re.sub("beamlineAnimation", "watchpointReport", data.report)
    if not _SIM_DATA.is_for_ml(data.report):
        data.fdir = sirepo.util.secure_filename(data.models.simulation.name) + "/"
    return _generate_parameters_file(data, plot_reports=plot_reports, qcall=qcall)


def run_epilogue():
    # POSIT: only called from template.run_epilogue
    def _op():
        sim_in = simulation_db.read_json(template_common.INPUT_BASE_NAME)
        if sim_in.report == "coherentModesAnimation":
            # this sim creates _really_ large intermediate files which should get removed
            for p in pkio.sorted_glob("*_mi.h5"):
                p.remove()

    sirepo.mpi.restrict_op_to_first_rank(_op)


def stateful_compute_create_shadow_simulation(data, **kwargs):
    from sirepo.template.srw_shadow import Convert

    return Convert().to_shadow(data)


def stateful_compute_delete_user_models(data, **kwargs):
    """Remove the beam and undulator user model list files"""

    def _delete(model_name, model):
        if model and "id" in model:
            # optimistic: model is very likely to be there
            _save_user_model_list(
                model_name,
                list(
                    filter(
                        lambda m: m.id != model.id,
                        _load_user_model_list(model_name),
                    ),
                ),
            )

    _delete("electronBeam", data.args.get("electron_beam"))
    _delete("tabulatedUndulator", data.args.get("tabulated_undulator"))
    return PKDict()


def stateful_compute_import_file(data, **kwargs):
    from sirepo.template import srw_importer

    with sirepo.sim_run.tmp_dir():
        return PKDict(
            imported_data=srw_importer.import_python(
                code=data.args.file_as_str,
                user_filename=data.args.basename,
                arguments=data.args.import_file_arguments,
            ),
        )


def stateful_compute_model_list(data, **kwargs):
    res = []
    m = data.args.model_name
    if m == "electronBeam":
        res.extend(get_predefined_beams())
    res.extend(_load_user_model_list(m))
    if m == "electronBeam":
        for beam in res:
            srw_common.process_beam_parameters(beam)
    return PKDict(modelList=res)


def stateless_compute_PGM_value(data, **kwargs):
    return _compute_PGM_value(data.optical_element)


def stateful_compute_sample_preview(data, **kwargs):
    """Process image and return

    Args:
        data (dict): description of simulation
    Returns:
        JobCmdFile: file to be returned
    """
    import srwpy.srwl_uti_smp

    def _input_file(data):
        """This should just be a basename, but secure_filename ensures it."""
        return str(
            _SIM_DATA.lib_file_abspath(sirepo.util.secure_filename(data.baseImage)),
        )

    def _obj_par1(m):
        if m.obj_type in ("1", "2", "3"):
            return m.obj_size_ratio
        elif m.obj_type == "4":
            return m.poly_sides
        else:
            return m.rand_shapes

    def _obj_par2(m):
        if m.obj_type in ("1", "2", "3"):
            m.rand_obj_size == "1"
        elif m.obj_type == "4":
            m.rand_poly_side == "1"
        else:
            return None

    m = data.model
    d = pkio.py_path()
    if m.sampleSource == "file":
        s = srwpy.srwl_uti_smp.SRWLUtiSmp(
            file_path=_input_file(data),
            area=(
                None
                if not int(m.cropArea)
                else (m.areaXStart, m.areaXEnd, m.areaYStart, m.areaYEnd)
            ),
            rotate_angle=float(m.rotateAngle),
            rotate_reshape=int(m.rotateReshape),
            cutoff_background_noise=float(m.cutoffBackgroundNoise),
            background_color=int(m.backgroundColor),
            invert=int(m.invert),
            tile=None if not int(m.tileImage) else (m.tileRows, m.tileColumns),
            shift_x=m.shiftX,
            shift_y=m.shiftY,
            is_save_images=True,
            prefix=str(d),
            output_image_format=m.outputImageFormat,
        )
        p = pkio.py_path(s.processed_image_name)
    else:
        assert m.sampleSource == "randomDisk"
        s = srwpy.srwl_uti_smp.srwl_opt_setup_smp_rnd_obj2d(
            _thickness=0,
            _delta=0,
            _atten_len=0,
            _dens=m.dens,
            _rx=m.rx,
            _ry=m.ry,
            _obj_type=int(m.obj_type),
            _r_min_bw_obj=m.r_min_bw_obj,
            _obj_size_min=m.obj_size_min,
            _obj_size_max=m.obj_size_max,
            _size_dist=int(m.size_dist),
            _ang_min=m.ang_min,
            _ang_max=m.ang_max,
            _ang_dist=int(m.ang_dist),
            _rand_alg=int(m.rand_alg),
            _obj_par1=_obj_par1(m),
            _obj_par2=_obj_par2(m),
            _ret="img",
        )
        p = d.join(f"sample_processed.{m.outputImageFormat}")
        s.save(p.basename)
    return template_common.JobCmdFile(reply_path=p)


def stateful_compute_undulator_length(data, **kwargs):
    return compute_undulator_length(data.args["tabulated_undulator"])


def stateless_compute_crl_characteristics(data, **kwargs):
    import bnlcrl.pkcli.simulate

    m = _compute_material_characteristics(
        data.optical_element,
        data.photon_energy,
    )
    if (
        float(m.refractiveIndex) > 0
        and float(m.tipRadius) > 0
        and float(m.numberOfLenses) > 0
        and float(m.position) > 0
    ):
        d = bnlcrl.pkcli.simulate.calc_ideal_focus(
            radius=float(m.tipRadius) * 1e-6,  # um -> m
            n=m.numberOfLenses,
            delta=m.refractiveIndex,
            p0=m.position,
        )
        m.focalDistance = d["ideal_focus"]
        m.absoluteFocusPosition = d["p1_ideal_from_source"]
    return m


def stateless_compute_crystal_init(data, **kwargs):
    return _compute_crystal_init(data.optical_element)


def stateless_compute_crystal_orientation(data, **kwargs):
    return _compute_crystal_orientation(data.optical_element)


def stateless_compute_delta_atten_characteristics(data, **kwargs):
    return _compute_material_characteristics(
        data.optical_element,
        data.photon_energy,
    )


def stateless_compute_dual_characteristics(data, **kwargs):
    return _compute_material_characteristics(
        _compute_material_characteristics(
            data.optical_element,
            data.photon_energy,
            prefix=data.prefix1,
        ),
        data.photon_energy,
        prefix=data.prefix2,
    )


def stateless_compute_compute_grazing_orientation(data, **kwargs):
    return _compute_grazing_orientation(data.optical_element)


def stateless_compute_process_beam_parameters(data, **kwargs):
    data.ebeam = srw_common.process_beam_parameters(data.ebeam)
    data.ebeam.drift = calculate_beam_drift(
        data.ebeam_position,
        data.source_type,
        data.undulator_type,
        data.undulator_length,
        data.undulator_period,
    )
    return data.ebeam


def stateless_compute_process_undulator_definition(data, **kwargs):
    return process_undulator_definition(data)


def validate_file(file_type, path):
    """Ensure the data file contains parseable rows data"""
    import srwpy.srwl_uti_smp

    if not _SIM_DATA.srw_is_valid_file_type(file_type, path):
        return "invalid file type: {}".format(path.ext)
    if file_type == "mirror":
        # mirror file
        try:
            count = 0
            with open(str(path)) as f:
                for line in f.readlines():
                    parts = line.split("\t")
                    if len(parts) > 0:
                        float(parts[0])
                    if len(parts) > 1:
                        float(parts[1])
                        count += 1
            if count == 0:
                return "no data rows found in file"
        except ValueError as e:
            return "invalid file format: {}".format(e)
    elif file_type == "undulatorTable":
        # undulator magnetic data file
        try:
            _validate_safe_zip(str(path), ".", validate_magnet_data_file)
        except AssertionError as err:
            return str(err)
    elif file_type == "sample":
        srwpy.srwl_uti_smp.SRWLUtiSmp(
            file_path=str(path),
            # srw processes the image so we save to tmp location
            is_save_images=True,
            prefix=path.purebasename,
        )
    if not _SIM_DATA.srw_is_valid_file(file_type, path):
        return "Column count is incorrect for file type: {}".format(file_type)
    return None


def validate_magnet_data_file(zf):
    """Validate a zip file containing tabulated magentic data

    Performs the following checks:

        - Only .txt and .dat files are allowed
        - Zip file must contain one and only one .txt file to use as an index
        - The index file must list the data files with the name in the 4th column
        - Zip file must contain only the index file and the data files it lists

    Args:
        zf (zipfile.ZipFile): the zip file to examine
    Returns:
        True if all conditions are met, False otherwise
        A string for debugging purposes
    """
    import collections

    def index_file_name(zf):
        # Apparently pkio.has_file_extension will return true for any extension if fed a directory path ('some_dir/')
        text_files = [
            f
            for f in zf.namelist()
            if not f.endswith("/") and pkio.has_file_extension(f, "txt")
        ]
        if len(text_files) != 1:
            return None
        return text_files[0]

    # Check against whitelist
    for f in zf.namelist():
        # allow directories
        if f.endswith("/"):
            continue
        if not template_common.file_extension_ok(f, white_list=["txt", "dat"]):
            return False, "File {} has forbidden type".format(f)

    file_name_column = 3

    # Assure unique index exists
    if index_file_name(zf) is None:
        return False, "Zip file has no unique index"

    # Validate correct number of columns (plus other format validations if needed)
    index_file = zf.open(index_file_name(zf))
    lines = index_file.readlines()
    file_names_in_index = []
    for line in lines:
        cols = line.split()
        if not cols:
            continue
        if len(cols) <= file_name_column:
            return False, "Index file {} has bad format".format(index_file_name(zf))
        file_names_in_index.append(cols[file_name_column].decode())

    # Compare index and zip contents
    # Does not include the index itself, nor any directories
    # also extract the filename since the index does not include path info
    file_names_in_zip = list(
        map(
            lambda path: os.path.basename(path),
            [
                f
                for f in zf.namelist()
                if not f.endswith("/") and f != index_file_name(zf)
            ],
        )
    )
    files_match = collections.Counter(file_names_in_index) == collections.Counter(
        file_names_in_zip
    )
    return (
        files_match,
        (
            ""
            if files_match
            else "Files in index {} do not match files in zip {}".format(
                file_names_in_index, file_names_in_zip
            )
        ),
    )


def write_parameters(data, run_dir, is_parallel):
    """Write the parameters file

    Args:
        data (dict): input
        run_dir (py.path): where to write
        is_parallel (bool): run in background?
    """
    p = ""
    if _SIM_DATA.is_for_rsopt(data.report):
        _export_rsopt_config(data, run_dir=run_dir)
        if _SIM_DATA.is_for_ml(data.report):
            pkio.unchecked_remove(_SIM_DATA.ML_OUTPUT)
            p = f"""import subprocess
subprocess.call(['bash', '{_SIM_DATA.EXPORT_RSOPT}.sh'])
"""
    if data.report not in (
        "samplePreviewReport",
        _SIM_DATA.EXPORT_RSOPT,
        _SIM_DATA.ML_REPORT,
    ):
        p = _trim(_generate_parameters_file(data, run_dir=run_dir))
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        p,
    )
    if is_parallel:
        return template_common.get_exec_parameters_cmd(_SIM_DATA.is_run_mpi(data))
    return None


def _beamline_animation_percent_complete(run_dir, res):
    res.outputInfo = [
        PKDict(
            modelKey="beamlineAnimation0",
            id=0,
        ),
    ]
    dm = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME)).models
    for item in dm.beamline:
        if _is_item_disabled(item):
            continue
        if item.type == "watch":
            res.outputInfo.append(
                PKDict(
                    waitForData=True,
                    modelKey=f"beamlineAnimation{item.id}",
                    id=item.id,
                )
            )
    count = 0
    for info in res.outputInfo:
        try:
            with open(
                pkio.py_path(_wavefront_pickle_filename(info.id, is_processed=True)),
                "rb",
            ) as f:
                f.seek(-1, os.SEEK_END)
                if f.read(1) == pickle.STOP:
                    count += 1
                    info.waitForData = False
        except Exception as e:
            break
    res.frameCount = count
    res.percentComplete = 100 * count / len(res.outputInfo)
    return res


def _best_data_file(primary):
    def _lines(path):
        return len(pkio.open_text(path).readlines())

    p = pkio.py_path(primary)
    s = p.new(ext="dat.bkp")
    if not s.check():
        return p.basename
    if s.mtime() > p.mtime():
        p, s = s, p
    if _lines(s) >= _lines(p):
        p, s = s, p
    return p.basename


def _compute_material_characteristics(model, photon_energy, prefix=""):
    import bnlcrl.pkcli.simulate

    fields_with_prefix = PKDict(
        material="material",
        refractiveIndex="refractiveIndex",
        attenuationLength="attenuationLength",
    )
    if prefix:
        for k in fields_with_prefix.keys():
            fields_with_prefix[k] = "{}{}{}".format(
                prefix,
                fields_with_prefix[k][0].upper(),
                fields_with_prefix[k][1:],
            )

    if model[fields_with_prefix.material] == "User-defined":
        return model

    # Index of refraction:
    kwargs = PKDict(
        energy=photon_energy,
    )
    if model.method == "server":
        kwargs.precise = True
        kwargs.formula = model[fields_with_prefix.material]
    elif model.method == "file":
        kwargs.precise = True
        kwargs.data_file = "{}_delta.dat".format(model[fields_with_prefix.material])
    else:
        kwargs.calc_delta = True
        kwargs.formula = model[fields_with_prefix.material]
    delta = bnlcrl.pkcli.simulate.find_delta(**kwargs)
    model[fields_with_prefix.refractiveIndex] = delta["characteristic_value"]

    # Attenuation length:
    kwargs.characteristic = "atten"
    if model.method == "file":
        kwargs.precise = True
        kwargs.data_file = "{}_atten.dat".format(model[fields_with_prefix.material])
    if model.method == "calculation":
        # The method 'calculation' in bnlcrl library is not supported yet for attenuation length calculation.
        pass
    else:
        atten = bnlcrl.pkcli.simulate.find_delta(**kwargs)
        model[fields_with_prefix.attenuationLength] = atten["characteristic_value"]

    return model


def _compute_PGM_value(model):
    if model.computeParametersFrom == "3":
        return model
    parms_list = ["energyAvg", "cff", "grazingAngle"]
    try:
        mirror = srwpy.srwlib.SRWLOptMirPl(
            _size_tang=model.tangentialSize,
            _size_sag=model.sagittalSize,
            _nvx=model.nvx,
            _nvy=model.nvy,
            _nvz=model.nvz,
            _tvx=model.tvx,
            _tvy=model.tvy,
            _x=model.horizontalOffset,
            _y=model.verticalOffset,
        )
        # existing data may have photonEnergy as a string
        model.energyAvg = float(model.energyAvg)
        if model.computeParametersFrom == "1":
            opGr = srwpy.srwlib.SRWLOptG(
                _mirSub=mirror,
                _m=model.diffractionOrder,
                _grDen=model.grooveDensity0,
                _grDen1=model.grooveDensity1,
                _grDen2=model.grooveDensity2,
                _grDen3=model.grooveDensity3,
                _grDen4=model.grooveDensity4,
                _e_avg=model.energyAvg,
                _cff=model.cff,
                _ang_graz=0,
                _ang_roll=model.rollAngle,
            )
            grAng, defAng = opGr.cff2ang(_en=model.energyAvg, _cff=model.cff)
            model.grazingAngle = grAng * 1000.0
        elif model.computeParametersFrom == "2":
            opGr = srwpy.srwlib.SRWLOptG(
                _mirSub=mirror,
                _m=model.diffractionOrder,
                _grDen=model.grooveDensity0,
                _grDen1=model.grooveDensity1,
                _grDen2=model.grooveDensity2,
                _grDen3=model.grooveDensity3,
                _grDen4=model.grooveDensity4,
                _e_avg=model.energyAvg,
                _cff=None,
                _ang_graz=model.grazingAngle / 1000.0,
                _ang_roll=model.rollAngle,
            )
            cff, defAng = opGr.ang2cff(
                _en=model.energyAvg, _ang_graz=model.grazingAngle / 1000.0
            )
            model.cff = cff
        else:
            raise AssertionError(
                f"invalid computeParametersFrom: {model.computeParametersFrom}",
            )
        angroll = model.rollAngle
        if abs(angroll) < np.pi / 4 or abs(angroll - np.pi) < np.pi / 4:
            model.orientation = "y"
        else:
            model.orientation = "x"
        _compute_grating_orientation(model)
    except Exception as e:
        if type(e) not in (ZeroDivisionError, ValueError, TypeError):
            pkdlog("\n{}", traceback.format_exc())
        if model.computeParametersFrom == "1":
            model.grazingAngle = None
        elif model.computeParametersFrom == "2":
            model.cff = None

    return model


def _compute_grating_orientation(model):
    if not model.grazingAngle:
        pkdlog("grazingAngle is missing, return old data")
        return model
    parms_list = [
        "nvx",
        "nvy",
        "nvz",
        "tvx",
        "tvy",
        "outoptvx",
        "outoptvy",
        "outoptvz",
        "outframevx",
        "outframevy",
    ]
    try:
        mirror = srwpy.srwlib.SRWLOptMirPl(
            _size_tang=model.tangentialSize,
            _size_sag=model.sagittalSize,
            _nvx=model.nvx,
            _nvy=model.nvy,
            _nvz=model.nvz,
            _tvx=model.tvx,
            _tvy=model.tvy,
            _x=model.horizontalOffset,
            _y=model.verticalOffset,
        )
        cff = model.cff
        grazingAngle = model.grazingAngle / 1000
        if model.computeParametersFrom == "1":
            grazingAngle = 0
        elif model.computeParametersFrom == "2":
            cff = None
        opGr = srwpy.srwlib.SRWLOptG(
            _mirSub=mirror,
            _m=model.diffractionOrder,
            _grDen=model.grooveDensity0,
            _grDen1=model.grooveDensity1,
            _grDen2=model.grooveDensity2,
            _grDen3=model.grooveDensity3,
            _grDen4=model.grooveDensity4,
            _e_avg=model.energyAvg,
            _cff=cff,
            _ang_graz=grazingAngle,
            _ang_roll=model.rollAngle,
        )
        pkdc(
            "updating nvz from {} to {} with grazingAngle= {}mrad",
            model.nvz,
            opGr.mirSub.nvz,
            model.grazingAngle,
        )
        model.nvx = opGr.mirSub.nvx
        model.nvy = opGr.mirSub.nvy
        model.nvz = opGr.mirSub.nvz
        model.tvx = opGr.mirSub.tvx
        model.tvy = opGr.mirSub.tvy
        orientDataGr_pp = opGr.get_orient(_e=model.energyAvg)[1]
        tGr_pp = orientDataGr_pp[0]  # Tangential Vector to Grystal surface
        nGr_pp = orientDataGr_pp[2]  # Normal Vector to Grystal surface
        model.outoptvx = nGr_pp[0]
        model.outoptvy = nGr_pp[1]
        model.outoptvz = nGr_pp[2]
        model.outframevx = tGr_pp[0]
        model.outframevy = tGr_pp[1]

    except Exception:
        pkdlog("\n{}", traceback.format_exc())
        for key in parms_list:
            model[key] = None
    return model


def _compute_crystal_init(model):
    import srwpy.srwl_uti_cryst

    parms_list = ["dSpacing", "psi0r", "psi0i", "psiHr", "psiHi", "psiHBr", "psiHBi"]
    try:
        material_raw = model.material  # name contains either "(SRW)" or "(X0h)"
        material = material_raw.split()[
            0
        ]  # short name for SRW (e.g., Si), long name for X0h (e.g., Silicon)
        h = int(model.h)
        k = int(model.k)
        l = int(model.l)
        millerIndices = [h, k, l]
        energy = model.energy
        if re.search("(X0h)", material_raw):
            crystal_parameters = crystal.get_crystal_parameters(
                material, energy, h, k, l
            )
            dc = crystal_parameters["d"]
            xr0 = crystal_parameters["xr0"]
            xi0 = crystal_parameters["xi0"]
            xrh = crystal_parameters["xrh"]
            xih = crystal_parameters["xih"]
        elif re.search("(SRW)", material_raw):
            dc = srwpy.srwl_uti_cryst.srwl_uti_cryst_pl_sp(millerIndices, material)
            xr0, xi0, xrh, xih = srwpy.srwl_uti_cryst.srwl_uti_cryst_pol_f(
                energy, millerIndices, material
            )
        else:
            dc = xr0 = xi0 = xrh = xih = None

        model.dSpacing = dc
        model.psi0r = xr0
        model.psi0i = xi0
        model.psiHr = xrh
        model.psiHi = xih
        model.psiHBr = xrh
        model.psiHBi = xih
        if (
            model.diffractionAngle == "-1.57079632"
            or model.diffractionAngle == "1.57079632"
        ):
            model.orientation = "x"
        else:
            model.orientation = "y"
    except Exception as e:
        pkdlog("material_raw={} exception={}", material_raw, e)
        for key in parms_list:
            model[key] = None
    return model


def _compute_crystal_orientation(model):
    if not model.dSpacing:
        return model
    parms_list = [
        "nvx",
        "nvy",
        "nvz",
        "tvx",
        "tvy",
        "outoptvx",
        "outoptvy",
        "outoptvz",
        "outframevx",
        "outframevy",
    ]
    try:
        opCr = srwpy.srwlib.SRWLOptCryst(
            _d_sp=model.dSpacing,
            _psi0r=model.psi0r,
            _psi0i=model.psi0i,
            _psi_hr=model.psiHr,
            _psi_hi=model.psiHi,
            _psi_hbr=model.psiHBr,
            _psi_hbi=model.psiHBi,
            _tc=model.crystalThickness,
            _uc=float(model.useCase),
            _ang_as=model.asymmetryAngle,
            _e_avg=model.energy,
            _ang_roll=float(model.diffractionAngle),
        )
        model.nvx = opCr.nvx
        model.nvy = opCr.nvy
        model.nvz = opCr.nvz
        model.tvx = opCr.tvx
        model.tvy = opCr.tvy
        orientDataCr_pp = opCr.get_orient(_e=model.energy)[1]
        tCr_pp = orientDataCr_pp[0]  # Tangential Vector to Crystal surface
        nCr_pp = orientDataCr_pp[2]  # Normal Vector to Crystal surface
        model.outoptvx = nCr_pp[0]
        model.outoptvy = nCr_pp[1]
        model.outoptvz = nCr_pp[2]
        model.outframevx = tCr_pp[0]
        model.outframevy = tCr_pp[1]
        _SIM_DATA.srw_compute_crystal_grazing_angle(model)
    except Exception:
        pkdlog("\n{}", traceback.format_exc())
        for key in parms_list:
            model[key] = None
    return model


def _compute_grazing_orientation(model):
    def preserve_sign(item, field, new_value):
        old_value = item[field] if field in item else 0
        was_negative = float(old_value) < 0
        item[field] = float(new_value)
        if (was_negative and item[field] > 0) or item[field] < 0:
            item[field] = -item[field]

    grazing_angle = float(model.grazingAngle) / 1000.0
    # z is always negative
    model.normalVectorZ = -abs(math.sin(grazing_angle))
    if model.autocomputeVectors == "horizontal":
        preserve_sign(model, "normalVectorX", math.cos(grazing_angle))
        preserve_sign(model, "tangentialVectorX", math.sin(grazing_angle))
        model.normalVectorY = 0
        model.tangentialVectorY = 0
    elif model.autocomputeVectors == "vertical":
        preserve_sign(model, "normalVectorY", math.cos(grazing_angle))
        preserve_sign(model, "tangentialVectorY", math.sin(grazing_angle))
        model.normalVectorX = 0
        model.tangentialVectorX = 0
    return model


def _copy_frame_args_into_model(frame_args, name):
    m = frame_args.sim_in.models[frame_args.frameReport]
    m_schema = SCHEMA.model[name]
    for f in frame_args:
        if f in m and f in m_schema:
            m[f] = frame_args[f]
    return m


def _core_error(cores):
    raise sirepo.util.UserAlert(f"cores={cores} when cores must be >= {_MIN_CORES}")


def _create_user_model(data, model_name):
    model = data.models[model_name]
    if model_name == "tabulatedUndulator":
        model = model.copy()
        model.undulator = data.models.undulator
    return model


def _element_name(sim_in, watchpoint_id):
    if sim_in.report == "multiElectronAnimation":
        watchpoint_id = sim_in.models.multiElectronAnimation.get("watchpointId", 0)
    for e in sim_in.models.beamline:
        if e.id == watchpoint_id:
            # use "at {title}" unless the watchpoint name contains a common preposition
            if re.search(
                r"\b(after|at|before|in|near)\b", e.title, re.IGNORECASE
            ) or re.search(r"\b(pre|post)", e.title, re.IGNORECASE):
                return e.title
            return f"at {e.title}"
    return ""


def _element_position(sim_in, watchpoint_id):
    if sim_in.report == "initialIntensityReport":
        return f"{_format_amount(sim_in.models.simulation.distanceFromSource)} m"
    if sim_in.report == "multiElectronAnimation":
        watchpoint_id = sim_in.models.multiElectronAnimation.get("watchpointId", 0)
    for e in sim_in.models.beamline:
        if e.id == watchpoint_id:
            return f"{_format_amount(e.position)} m"
    if (
        sim_in.models[sim_in.report]
        and "distanceFromSource" in sim_in.models[sim_in.report]
    ):
        return f"{_format_amount(sim_in.models[sim_in.report].distanceFromSource)} m"
    return ""


def _enum_text(name, model, field):
    if field in model:
        return template_common.enum_text(SCHEMA, name, model[field])
    return ""


def _export_rsopt_config(data, run_dir):
    ctx = _rsopt_jinja_context(data)
    if _SIM_DATA.is_for_ml(data.report):
        _write_rsopt_files(data, run_dir, ctx)
    else:
        _write_rsopt_zip(data, ctx)


def _export_rsopt_files():
    files = PKDict()
    for t in (
        "py",
        "sh",
        "yml",
    ):
        files[f"{t}FileName"] = f"{_SIM_DATA.EXPORT_RSOPT}.{t}"
    files.postProcFileName = f"{_SIM_DATA.EXPORT_RSOPT}_post.py"
    files.readmeFileName = "README.txt"
    return files


def _extend_plot(
    ar2d, x_range, y_range, horizontalStart, horizontalEnd, verticalStart, verticalEnd
):
    x_step = (x_range[1] - x_range[0]) / x_range[2]
    y_step = (y_range[1] - y_range[0]) / y_range[2]

    if horizontalStart < x_range[0]:
        b = np.zeros((np.shape(ar2d)[0], int((x_range[0] - horizontalStart) / x_step)))
        ar2d = np.hstack((b, ar2d))
        x_range[0] = horizontalStart
    if horizontalEnd > x_range[1]:
        b = np.zeros((np.shape(ar2d)[0], int((horizontalEnd - x_range[1]) / x_step)))
        ar2d = np.hstack((ar2d, b))
        x_range[1] = horizontalEnd
    if verticalStart < y_range[0]:
        b = np.zeros((int((y_range[0] - verticalStart) / y_step), np.shape(ar2d)[1]))
        ar2d = np.vstack((ar2d, b))
        y_range[0] = verticalStart
    if verticalEnd > y_range[1]:
        b = np.zeros((int((verticalEnd - y_range[1]) / y_step), np.shape(ar2d)[1]))
        ar2d = np.vstack((b, ar2d))
        y_range[1] = verticalEnd
    y_range[2], x_range[2] = np.shape(ar2d)
    return (ar2d, x_range, y_range)


def _extract_beamline_orientation(filename):
    cols = np.array(
        srwpy.uti_io.read_ascii_data_cols(
            filename, "\t", _i_col_start=1, _n_line_skip=1
        )
    )
    rows = list(reversed(np.rot90(cols).tolist()))
    rows = np.reshape(rows, (len(rows), 4, 3))
    res = []
    for row in rows:
        # the vtk client renders x axis flipped, so update x position and rotation
        p = row[0].tolist()
        p[0] = -p[0]
        orient = row[1:].tolist()
        orient[1][0] = -orient[1][0]
        orient[1][1] = -orient[1][1]
        orient[1][2] = -orient[1][2]
        res.append(
            PKDict(
                point=p,
                orient=orient,
            )
        )
    return PKDict(
        x_range=[],
        elements=res,
    )


def _extract_brilliance_report(model, filename):
    data, _, _, _, _ = srwpy.uti_plot_com.file_load(filename, multicolumn_data=True)
    label = _enum_text("BrillianceReportType", model, "reportType")
    if model.reportType in ("3", "4"):
        label += " [rad]"
    elif model.reportType in ("5", "6"):
        label += " [m]"
    x_points = []
    points = []
    scale_adjustment = 1000.0
    if (
        "brightnessComponent" in model
        and model.brightnessComponent == "spectral-detuning"
    ):
        scale_adjustment = 1.0
    for f in data:
        m = re.search(r"^f(\d+)", f)
        if m:
            x_points.append((np.array(data[f]["data"]) * scale_adjustment).tolist())
            points.append(data["e{}".format(m.group(1))]["data"])
    title = _enum_text("BrightnessComponent", model, "brightnessComponent")
    if model.brightnessComponent == "k-tuning":
        if model.initialHarmonic == model.finalHarmonic:
            title += ", Harmonic {}".format(model.initialHarmonic)
        else:
            title += ", Harmonic {} - {}".format(
                model.initialHarmonic, model.finalHarmonic
            )
    else:
        title += ", Harmonic {}".format(model.harmonic)

    return PKDict(
        title=title,
        y_label=label,
        x_label="Photon Energy [eV]",
        x_range=[np.amin(x_points), np.amax(x_points)],
        y_range=[np.amin(points), np.amax(points)],
        x_points=x_points,
        points=points,
    )


def _extract_coherent_modes(model, out_info):
    out_file = "combined-modes.dat"
    wfr = srwpy.srwlib.srwl_uti_read_wfr_cm_hdf5(_file_path=out_info.filename)
    if model.plotModesEnd > len(wfr):
        model.plotModesEnd = len(wfr)
    if model.plotModesStart > model.plotModesEnd:
        model.plotModesStart = model.plotModesEnd
    if model.plotModesStart == model.plotModesEnd:
        out_info.title = "E={photonEnergyWithUnits} Mode {plotModesStart}"
    mesh = wfr[0].mesh
    arI = array.array("f", [0] * mesh.nx * mesh.ny)
    for i in range(model.plotModesStart, model.plotModesEnd + 1):
        srwpy.srwlib.srwl.CalcIntFromElecField(
            arI,
            wfr[i - 1],
            int(model.polarization),
            int(model.characteristic),
            3,
            mesh.eStart,
            0,
            0,
            [2],
        )
    srwpy.srwlib.srwl_uti_save_intens_ascii(
        arI,
        mesh,
        out_file,
        _arLabels=[
            "Photon Energy",
            "Horizontal Position",
            "Vertical Position",
            "Intensity",
        ],
        _arUnits=["eV", "m", "m", "ph/s/.1%bw/mm^2"],
    )
    return out_file


def _extract_trajectory_report(model, filename):
    data, _, _, _, _ = srwpy.uti_plot_com.file_load(filename, multicolumn_data=True)
    available_axes = PKDict()
    for s in SCHEMA.enum.TrajectoryPlotAxis:
        available_axes[s[0]] = s[1]
    x_points = data[model.plotAxisX]["data"]
    plots = []
    y_range = []

    for f in ("plotAxisY", "plotAxisY2"):
        if model[f] != "None":
            points = data[model[f]]["data"]
            if y_range:
                y_range = [min(y_range[0], min(points)), max(y_range[1], max(points))]
            else:
                y_range = [min(points), max(points)]
            plots.append(
                PKDict(
                    points=points,
                    label=available_axes[model[f]],
                    # TODO(pjm): refactor with template_common.compute_plot_color_and_range()
                    color="#ff7f0e" if plots else "#1f77b4",
                )
            )
    return PKDict(
        title="Electron Trajectory",
        x_range=[min(x_points), max(x_points)],
        x_points=x_points,
        y_label="[{}]".format(data[model.plotAxisY]["units"]),
        x_label=available_axes[model.plotAxisX]
        + " ["
        + data[model.plotAxisX]["units"]
        + "]",
        y_range=y_range,
        plots=plots,
    )


def _fix_file_header(filename):
    # fixes file header for coherenceXAnimation and coherenceYAnimation reports
    rows = []
    pkdc("fix header filename: {}", filename)
    with pkio.open_text(filename) as f:
        for line in f:
            rows.append(line)
            if len(rows) == 11:
                pkdc("before header changed rows4: {}", rows[4])
                pkdc("before header changed rows5: {}", rows[5])
                pkdc("before header changed rows6: {}", rows[6])
                pkdc("before header changed rows7: {}", rows[7])
                pkdc("before header changed rows8: {}", rows[8])
                pkdc("before header changed rows9: {}", rows[9])
                # if rows[4] == rows[7]:
                if rows[6].split()[0] == rows[9].split()[0] and rows[6].split()[0] != 1:
                    # already fixed up
                    return
                col4 = rows[4].split()
                col5 = rows[5].split()
                col6 = rows[6].split()
                col7 = rows[7].split()
                col8 = rows[8].split()
                col9 = rows[9].split()
                # if re.search(r'^\#0 ', rows[4]):
                if re.search(r"^\#1 ", rows[6]):
                    col4[0] = col7[0]
                    rows[4] = " ".join(col4) + "\n"
                    col5[0] = col8[0]
                    rows[5] = " ".join(col5) + "\n"
                    col6[0] = col9[0]
                    rows[6] = " ".join(col6) + "\n"
                else:
                    col7[0] = col4[0]
                    rows[7] = " ".join(col7) + "\n"
                    col8[0] = col5[0]
                    rows[8] = " ".join(col8) + "\n"
                    col9[0] = col6[0]
                    rows[9] = " ".join(col9) + "\n"
                Vmin = float(rows[7].split()[0][1:])
                Vmax = float(rows[8].split()[0][1:])
                rows[7] = (
                    "#"
                    + str((Vmin - Vmax) / 2)
                    + " "
                    + " ".join(rows[7].split()[1:])
                    + "\n"
                )
                rows[8] = (
                    "#"
                    + str((Vmax - Vmin) / 2)
                    + " "
                    + " ".join(rows[8].split()[1:])
                    + "\n"
                )
                pkdc("after header changed rows4:{}", rows[4])
                pkdc("after header changed rows5:{}", rows[5])
                pkdc("after header changed rows6:{}", rows[6])
                pkdc("after header changed rows7:{}", rows[7])
                pkdc("after header changed rows8:{}", rows[8])
                pkdc("after header changed rows9:{}", rows[9])
    pkio.write_text(filename, "".join(rows))


def _format_amount(value):
    return f"{float(value):.4f}".rstrip("0").rstrip(".")


def _format_energy(energy):
    energy = float(energy)
    u = "eV"
    if energy > 1000:
        energy = energy / 1000
        u = "keV"
    return f"{_format_amount(energy)} {u}"


def _generate_beamline_optics(report, data, qcall=None):
    res = PKDict(names=[], exclude=[], last_id=None, watches=PKDict())
    models = data.models
    # remove trailing disabled items
    while len(models.beamline) and _is_item_disabled(models.beamline[-1]):
        models.beamline.pop()
    if len(models.beamline) == 0 or not (
        _SIM_DATA.srw_is_beamline_report(report) or report == "beamlineAnimation"
    ):
        return "", "", res
    if _SIM_DATA.is_watchpoint(report):
        res.last_id = _SIM_DATA.watchpoint_id(report)
    if report == "multiElectronAnimation":
        res.last_id = models.multiElectronAnimation.watchpointId
    has_beamline_elements = len(models.beamline) > 0
    if has_beamline_elements and not res.last_id:
        res.last_id = models.beamline[-1].id
    items = []
    prev = None
    propagation = models.propagation
    max_name_size = 0
    zero_drift_count = 0

    for item in models.beamline:
        name = _safe_beamline_item_name(item.title, res.names)
        max_name_size = max(max_name_size, len(name))

        if prev:
            size = item.position - prev.position
            if size != 0:
                # add a drift
                drift_name = _safe_beamline_item_name(
                    "{}_{}".format(prev.name, name), res.names
                )
                max_name_size = max(max_name_size, len(drift_name))
                res.names.append(drift_name)
                items.append(
                    PKDict(
                        name=drift_name,
                        type="drift",
                        position=prev.position,
                        propagation=prev.drift_propagation,
                        length=size,
                    )
                )
        pp = propagation[str(item.id)]
        item.propagation = pp[0]
        item.drift_propagation = pp[1]
        item.name = name
        if not _is_item_disabled(item):
            if item.type == "watch" and (
                not items
                or (items[-1].type == "watch" and items[-1].position == item.position)
            ):
                # first item is a watch or no space between watches, insert a 0 length drift
                zero_drift_count += 1
                items.append(
                    PKDict(
                        name=f"zero_drift{zero_drift_count}",
                        type="drift",
                        position=item.position,
                        propagation=item.propagation,
                        length=0,
                    )
                )
                res.names.append(items[-1].name)
            if "heightProfileFile" in item:
                item.heightProfileDimension = _height_profile_dimension(
                    item, data, qcall=qcall
                )
            items.append(item)
            res.names.append(name)
            if item.type == "watch":
                res.watches[name] = item.id
        if int(res.last_id) == int(item.id):
            break
        prev = item
    for item in items:
        if item.type == "watch":
            res.exclude.append(item.name)
    args = PKDict(
        report=report,
        items=items,
        names=[n for n in res.names if n not in res.exclude],
        postPropagation=models.postPropagation,
        maxNameSize=max_name_size,
        fdir=data.get("fdir", ""),
        nameMap=PKDict(
            apertureShape="ap_shape",
            asymmetryAngle="ang_as",
            attenuationLength="atten_len",
            complementaryAttenuationLength="atLen2",
            complementaryRefractiveIndex="delta2",
            coreAttenuationLength="atten_len_core",
            coreDiameter="diam_core",
            coreRefractiveIndex="delta_core",
            crystalThickness="tc",
            dSpacing="d_sp",
            diffractionOrder="m",
            externalAttenuationLength="atten_len_ext",
            externalRefractiveIndex="delta_ext",
            energyAvg="e_avg",
            firstFocusLength="p",
            focalLength="q",
            focalPlane="foc_plane",
            grazingAngle="ang",
            gridShape="grid_sh",
            grooveDensity0="grDen",
            grooveDensity1="grDen1",
            grooveDensity2="grDen2",
            grooveDensity3="grDen3",
            grooveDensity4="grDen4",
            heightAmplification="amp_coef",
            heightProfileFile="hfn",
            horizontalApertureSize="apert_h",
            horizontalCenterCoordinate="xc",
            horizontalCenterPosition="xc",
            horizontalFocalLength="Fx",
            horizontalGridDimension="grid_dx",
            horizontalGridPitch="pitch_x",
            horizontalGridsNumber="grid_nx",
            horizontalMaskCoordinate="mask_x0",
            horizontalOffset="x",
            horizontalPixelsNumber="mask_Nx",
            horizontalSamplingInterval="hx",
            horizontalSize="Dx",
            horizontalTransverseSize="size_x",
            imageFile="file_path",
            length="L",
            mainAttenuationLength="atLen1",
            mainRefractiveIndex="delta1",
            maskThickness="thick",
            normalVectorX="nvx",
            normalVectorY="nvy",
            normalVectorZ="nvz",
            numberOfLenses="n",
            numberOfZones="nZones",
            orientation="dim",
            outerRadius="rn",
            radius="r",
            refractiveIndex="delta",
            sagittalRadius="rs",
            sagittalSize="size_sag",
            tangentialRadius="rt",
            tangentialSize="size_tang",
            tangentialVectorX="tvx",
            tangentialVectorY="tvy",
            thickness="thick",
            tipRadius="r_min",
            tipWallThickness="wall_thick",
            transmissionImage="extTransm",
            useCase="uc",
            verticalApertureSize="apert_v",
            verticalCenterCoordinate="yc",
            verticalCenterPosition="yc",
            verticalFocalLength="Fy",
            verticalGridDimension="grid_dy",
            verticalGridPitch="pitch_y",
            verticalGridsNumber="grid_ny",
            verticalMaskCoordinate="mask_y0",
            verticalOffset="y",
            verticalPixelsNumber="mask_Ny",
            verticalSamplingInterval="hy",
            verticalSize="Dy",
            verticalTransverseSize="size_y",
        ),
    )
    optics = template_common.render_jinja(SIM_TYPE, args, "beamline_optics.py")
    prop = template_common.render_jinja(SIM_TYPE, args, "beamline_parameters.py")
    return optics, prop, res


def _generate_parameters_file(data, plot_reports=False, run_dir=None, qcall=None):
    report = data.report
    is_for_rsopt = _SIM_DATA.is_for_rsopt(report)
    dm = data.models
    # do this before validation or arrays get turned into strings
    if is_for_rsopt:
        rsopt_ctx = _rsopt_jinja_context(data)
    _validate_data(data, SCHEMA)
    _update_model_fields(dm)
    _update_models_for_report(report, dm)
    res, v = template_common.generate_parameters_file(
        data,
        is_run_mpi=_SIM_DATA.is_run_mpi(data),
    )
    v.fdir = data.get("fdir", "")
    v.rs_type = dm.simulation.sourceType
    if v.rs_type == "t" and dm.tabulatedUndulator.undulatorType == "u_i":
        v.rs_type = "u"
    if is_for_rsopt:
        v.update(rsopt_ctx)
        v.runInSirepo = _SIM_DATA.is_for_ml(report)
    # rsopt uses this as a lookup param so want it in one place
    v.ws_fni_desc = "file name for saving propagated single-e intensity distribution vs horizontal and vertical position"
    if report == "mirrorReport":
        v.mirrorOutputFilename = _OUTPUT_FOR_MODEL[report].filename
        return template_common.render_jinja(SIM_TYPE, v, "mirror.py")
    if report == "brillianceReport":
        v.brillianceOutputFilename = _OUTPUT_FOR_MODEL[report].filename
        return template_common.render_jinja(SIM_TYPE, v, "brilliance.py")
    if report == "backgroundImport":
        v.tmp_dir = str(run_dir)
        v.python_file = run_dir.join("user_python.py")
        pkio.write_text(v.python_file, dm.backgroundImport.python)
        return template_common.render_jinja(SIM_TYPE, v, "import.py")
    if report in dm and str(dm[report].get("useDetector", "0")) == "1":
        v.useDetector = "1"
        for f in ("d_x", "d_rx", "d_nx", "d_y", "d_ry", "d_ny"):
            v[f"detector_{f}"] = dm[report][f]
    _set_parameters(v, data, plot_reports, run_dir, qcall=qcall)
    v.in_server = run_dir is not None
    return _trim(res + template_common.render_jinja(SIM_TYPE, v))


def _generate_srw_main(data, plot_reports, beamline_info):
    report = data.report
    is_for_rsopt = _SIM_DATA.is_for_rsopt(report)
    source_type = data.models.simulation.sourceType
    run_all = report == _SIM_DATA.SRW_RUN_ALL_MODEL or is_for_rsopt
    vp_var = "vp" if is_for_rsopt else "varParam"
    prev_watch = 0
    final_watch = None
    content = [
        f"v = srwpy.srwl_bl.srwl_uti_parse_options(srwpy.srwl_bl.srwl_uti_ext_options({vp_var}), use_sys_argv={plot_reports})",
    ]
    if report == "beamlineAnimation":
        content.append("v.si_fn = ''")
        content.append("v.ws_fni = ''")
        if len(beamline_info.watches):
            content.append("v.ws = True")
        else:
            content.append("v.si = True")
            content.append("op = None")
        content.append("v.ws_fne = '{}'".format(_wavefront_pickle_filename(0)))
        prev_wavefront = None
        names = []
        for n in beamline_info.names:
            names.append(n)
            if n in beamline_info.watches:
                final_watch = n
                is_last_watch = n == beamline_info.names[-1]
                content.append("names = ['" + "','".join(names) + "']")
                names = []
                if prev_wavefront:
                    content.append("v.ws_fnei = '{}'".format(prev_wavefront))
                prev_wavefront = _wavefront_pickle_filename(beamline_info.watches[n])
                content.append("v.ws_fnep = '{}'".format(prev_wavefront))
                content.append("op = set_optics(v, names, {})".format(is_last_watch))
                if not is_last_watch:
                    content.append(
                        "srwpy.srwl_bl.SRWLBeamline(_name=v.name).calc_all(v, op)"
                    )
                    content.append(
                        f"sirepo.template.import_module('srw').process_watch(wid={prev_watch})"
                    )
                    prev_watch = beamline_info.watches[n]

    elif run_all or (
        _SIM_DATA.srw_is_beamline_report(report) and len(data.models.beamline)
    ):
        content.append(
            "names = [{}]".format(
                ",".join(
                    [
                        "'{}'".format(name)
                        for name in beamline_info.names
                        if name not in beamline_info.exclude
                    ]
                ),
            )
        )
        content.append(
            "op = set_optics(v, names, {})".format(
                beamline_info.last_id
                and int(beamline_info.last_id) == int(data.models.beamline[-1].id)
            )
        )
        if report != "multiElectronAnimation":
            content.append("v.ws = True")
        if plot_reports and report != "multiElectronAnimation":
            content.append("v.ws_pl = 'xy'")
    else:
        content.append("op = None")
    if is_for_rsopt:
        content.extend(
            [
                "v.ss = False",
                "v.sm = False",
                "v.pw = False",
                "v.si = False",
                "v.tr = False",
            ]
        )
    else:
        if report in (
            "multiElectronAnimation",
            "coherenceXAnimation",
            "coherenceYAnimation",
            "coherentModesAnimation",
        ):
            if not run_all:
                content.append("v.wm = True")
        else:
            content.append("v.wm = False")
        if (run_all and source_type != "g") or report == "intensityReport":
            content.append("v.ss = True")
            if plot_reports:
                content.append("v.ss_pl = 'e'")
        if (run_all and source_type not in ("g", "m", "a")) or report in "fluxReport":
            content.append("v.sm = True")
            if plot_reports:
                content.append("v.sm_pl = 'e'")
        if (run_all and source_type != "g") or report == "powerDensityReport":
            content.append("v.pw = True")
            if plot_reports:
                content.append("v.pw_pl = 'xy'")
        if run_all or report in ["initialIntensityReport", "sourceIntensityReport"]:
            content.append("v.si = True")
            if plot_reports:
                content.append("v.si_pl = 'xy'")
        if (run_all and source_type != "g") or report == "trajectoryReport":
            content.append("v.tr = True")
            if plot_reports:
                content.append("v.tr_pl = 'xz'")
    content.append("srwpy.srwl_bl.SRWLBeamline(_name=v.name).calc_all(v, op)")
    if report == "beamlineAnimation":
        content.append(
            f"sirepo.template.import_module('srw').process_watch(wid={prev_watch})"
        )
        content.append(
            f"sirepo.template.import_module('srw').process_watch(wid={beamline_info.watches.get(final_watch, 0)})"
        )
    return "\n".join(
        [f"    {x}" for x in content] + [""] + ([] if is_for_rsopt else ["main()", ""])
    )


def _get_first_element_position(report, data):
    dm = data.models
    if report in dm and "distanceFromSource" in dm[report]:
        return dm[report].distanceFromSource
    if dm.beamline:
        return dm.beamline[0].position
    if "distanceFromSource" in dm.simulation:
        return dm.simulation.distanceFromSource
    return template_common.DEFAULT_INTENSITY_DISTANCE


def _get_most_recent_log_file(files):
    return sorted(files, key=lambda f: f.mtime())[-1].basename


def _height_profile_dimension(item, data, qcall=None):
    """Find the dimension of the provided height profile .dat file.
    1D files have 2 columns, 2D - 8 columns.
    """
    dimension = 0
    if item.heightProfileFile and item.heightProfileFile != "None":
        with _SIM_DATA.lib_file_abspath(
            item.heightProfileFile, data=data, qcall=qcall
        ).open("r") as f:
            header = f.readline().strip().split()
            dimension = 1 if len(header) == 2 else 2
    return dimension


def _intensity_units(sim_in):
    if "models" in sim_in and _SIM_DATA.srw_is_gaussian_source(
        sim_in.models.simulation
    ):
        if sim_in.get("report", "") == "sourceIntensityReport":
            i = sim_in.models[sim_in.report].fieldUnits
        else:
            i = sim_in.models.simulation.fieldUnits
        return SCHEMA.enum.FieldUnits[int(i)][1]
    return "ph/s/.1%bw/mm^2"


def _is_item_disabled(item):
    return item.get("isDisabled", False)


def _is_for_rsopt(report):
    return report == _SIM_DATA.EXPORT_RSOPT


def _is_true(model, field):
    return str(model.get(field, "0")) == "1"


def _load_user_model_list(model_name, qcall=None):
    b = _USER_MODEL_LIST_FILENAME[model_name]
    try:
        return pkjson.load_any(_SIM_DATA.lib_file_read_text(b, qcall=qcall))
    except Exception as e:
        if not pkio.exception_is_not_found(e):
            pkdlog(
                "resetting model_list={} due to lib_file_read error={} stack={}",
                b,
                e,
                pkdexc(),
            )
    return _save_user_model_list(model_name, [], qcall=qcall)


def _machine_learning_percent_complete(run_dir, res):
    res.outputInfo = [
        PKDict(
            filename=_SIM_DATA.ML_OUTPUT,
        ),
    ]
    dm = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME)).models
    count = len(pkio.walk_tree(run_dir, "values.npy"))
    res.frameCount = count
    res.percentComplete = 100 * count / dm.exportRsOpt.totalSamples
    return res


def _plot_z_footer(z_label, allrange, points):
    m = re.match(r"^(.*?)\[(.*?)/mm.*$", z_label)
    if m:
        l, u = m.group(1), m.group(2)
        if u == "W":
            l = "Total Power"
        elif u == "ph/s":
            l = "Flux"
        else:
            l = "Spectral Flux"
        v = "{:.3e}".format(
            srwpy.uti_math.integ_ar_2d(
                points,
                1,
                allrange[3:6],
                allrange[6:9],
            )
            * 1.0e6
        )
        return f"{l}: {v} {u}"


def _process_rsopt_elements(els):
    x = [e for e in els if e.enabled and e.enabled != "0"]
    names = []
    for e in x:
        e.title = _safe_beamline_item_name(e.title, names)
        names.append(e.title)
        for p in _RSOPT_PARAMS:
            if p in e:
                e[p].offsets = sirepo.util.split_comma_delimited_string(
                    e[f"{p}Offsets"], float
                )
    return x


def _remap_3d(info, allrange, out, report):
    ar2d, x_range, y_range = _reshape_3d(np.array(info.points), allrange, report)
    rotate_angle = report.get("rotateAngle", 0)
    if rotate_angle and info.title != "Power Density":
        info.subtitle = info.subtitle + " Image Rotate {}^0".format(rotate_angle)
    if out.units[2]:
        out.labels[2] = "{} [{}]".format(out.labels[2], out.units[2])
    if _is_true(report, "useIntensityLimits"):
        z_range = [report.minIntensityLimit, report.maxIntensityLimit]
    else:
        z_range = [np.min(ar2d), np.max(ar2d)]
    res = PKDict(
        x_range=x_range,
        y_range=y_range,
        x_label=info.x_label,
        y_label=info.y_label,
        z_label=_superscript(out.labels[2]),
        title=info.title,
        subtitle=_superscript_2(info.subtitle),
        z_matrix=ar2d.tolist(),
        z_range=z_range,
        summaryData=info.summaryData,
    )
    if (
        str(report.get("useDetector", "0")) == "1"
        and str(report.get("useDetectorAspectRatio", "0")) == "1"
        and float(report.d_rx) != 0
    ):
        res.aspectRatio = float(report.d_ry) / float(report.d_rx)
    return res


def _reshape_3d(ar1d, allrange, report):
    x_range = [allrange[3], allrange[4], allrange[5]]
    y_range = [allrange[6], allrange[7], allrange[8]]
    totLen = int(x_range[2] * y_range[2])
    n = len(ar1d) if totLen > len(ar1d) else totLen
    ar2d = np.reshape(ar1d[0:n], (int(y_range[2]), int(x_range[2])))
    if _is_true(report, "usePlotRange"):
        ar2d, x_range, y_range = _update_report_range(report, ar2d, x_range, y_range)
    if _is_true(report, "useIntensityLimits"):
        ar2d[ar2d < report["minIntensityLimit"]] = report["minIntensityLimit"]
        ar2d[ar2d > report["maxIntensityLimit"]] = report["maxIntensityLimit"]
    ar2d, x_range, y_range = _resize_report(report, ar2d, x_range, y_range)
    if report.get("rotateAngle", 0):
        ar2d, x_range, y_range = _rotate_report(report, ar2d, x_range, y_range)
    return ar2d, x_range, y_range


def _resize_mesh_dimensions(num_x, num_y):
    def _max_size(v, v2):
        return min(v, int(_MAX_REPORT_POINTS / v2))

    nx = num_x
    ny = num_y
    _MIN_DIMENSION = int(_MAX_REPORT_POINTS / _CANVAS_MAX_SIZE)
    if nx > _MIN_DIMENSION and ny > _MIN_DIMENSION and nx * ny > _MAX_REPORT_POINTS:
        r = math.sqrt(_MAX_REPORT_POINTS / (nx * ny))
        if r * nx <= _MIN_DIMENSION:
            nx = _MIN_DIMENSION
            ny = _max_size(ny, nx)
        elif r * ny <= _MIN_DIMENSION:
            ny = _MIN_DIMENSION
            nx = _max_size(nx, ny)
        elif r * nx >= _CANVAS_MAX_SIZE:
            nx = _CANVAS_MAX_SIZE
            ny = _max_size(ny, nx)
        elif r * ny >= _CANVAS_MAX_SIZE:
            ny = _CANVAS_MAX_SIZE
            nx = _max_size(nx, ny)
        else:
            nx = int(r * nx)
            ny = int(r * ny)

    return min(nx, _CANVAS_MAX_SIZE), min(ny, _CANVAS_MAX_SIZE)


def _resize_report(report, ar2d, x_range, y_range):
    width_pixels = int(report.get("intensityPlotsWidth", 0))
    if not width_pixels or str(report.get("useDetector", "0")) == "1":
        # upper limit is browser's max html canvas size
        width_pixels = _CANVAS_MAX_SIZE
    # rescale width and height to maximum of width_pixels
    if width_pixels and (width_pixels < x_range[2] or width_pixels < y_range[2]):
        from scipy import ndimage

        x_resize = 1.0
        y_resize = 1.0
        if width_pixels < x_range[2]:
            x_resize = float(width_pixels) / float(x_range[2])
        if width_pixels < y_range[2]:
            y_resize = float(width_pixels) / float(y_range[2])
        pkdc(
            "Size before: {}  Dimensions: {}, Resize: [{}, {}]",
            ar2d.size,
            ar2d.shape,
            y_resize,
            x_resize,
        )
        ar2d = ndimage.zoom(ar2d, [y_resize, x_resize], order=1)
        pkdc("Size after : {}  Dimensions: {}", ar2d.size, ar2d.shape)
        x_range[2] = ar2d.shape[1]
        y_range[2] = ar2d.shape[0]
    return ar2d, x_range, y_range


def _rotate_report(report, ar2d, x_range, y_range):
    from scipy import ndimage

    rotate_angle = report.rotateAngle
    rotate_reshape = _is_true(report, "rotateReshape")
    pkdc("Size before: {}  Dimensions: {}", ar2d.size, ar2d.shape)
    shape_before = list(ar2d.shape)
    ar2d = ndimage.rotate(
        ar2d, float(rotate_angle), reshape=rotate_reshape, mode="constant", order=3
    )
    pkdc("Size after rotate: {}  Dimensions: {}", ar2d.size, ar2d.shape)
    shape_rotate = list(ar2d.shape)

    pkdc(
        "x_range and y_range before rotate is [{},{}] and [{},{}]",
        x_range[0],
        x_range[1],
        y_range[0],
        y_range[1],
    )
    x_range[0] = shape_rotate[0] / shape_before[0] * x_range[0]
    x_range[1] = shape_rotate[0] / shape_before[0] * x_range[1]
    y_range[0] = shape_rotate[1] / shape_before[1] * y_range[0]
    y_range[1] = shape_rotate[1] / shape_before[1] * y_range[1]
    pkdc(
        "x_range and y_range after rotate is [{},{}] and [{},{}]",
        x_range[0],
        x_range[1],
        y_range[0],
        y_range[1],
    )

    x_range[2] = ar2d.shape[1]
    y_range[2] = ar2d.shape[0]
    return ar2d, x_range, y_range


def _rsopt_jinja_context(data):
    import multiprocessing

    model = data.models[_SIM_DATA.EXPORT_RSOPT]
    res = PKDict(
        fileBase=_SIM_DATA.EXPORT_RSOPT,
        forRSOpt=True,
        libFiles=_SIM_DATA.lib_file_basenames(data),
        maxOuputDimension=model.maxOuputDimension,
        numCores=int(model.numCores),
        numWorkers=max(1, multiprocessing.cpu_count() - 1),
        numSamples=int(model.numSamples),
        outFileName=f"{_SIM_DATA.EXPORT_RSOPT}.out",
        randomSeed=model.randomSeed if model.randomSeed is not None else "",
        resultsFileName=_SIM_DATA.ML_OUTPUT,
        rsOptCharacteristic=model.characteristic,
        rsOptElements=_process_rsopt_elements(model.elements),
        rsOptParams=_RSOPT_PARAMS,
        rsOptParamsNoRotation=_RSOPT_PARAMS_NO_ROTATION,
        rsOptOutFileName="scan_results",
        runInSirepo=data.report == _SIM_DATA.ML_REPORT,
        scanType=model.scanType,
        totalSamples=model.totalSamples,
        zipFileName=f"{_SIM_DATA.EXPORT_RSOPT}.zip",
    )
    res.update(_export_rsopt_files())
    return res


def _rsopt_main():
    return [
        "import sys",
        "if len(sys.argv[1:]) > 0:",
        "   set_rsopt_params(*sys.argv[1:])",
        "   del sys.argv[1:]",
        "else:",
        "   exit(0)",
    ]


def _safe_beamline_item_name(name, names):
    name = re.sub(r"\W+", "_", name)
    name = re.sub(r"_+", "_", name)
    name = re.sub(r"^_|_$", "", name)
    name = re.sub(r"^_+", "", name)
    name = re.sub(r"_+$", "", name)
    name = re.sub(r"^op_", "", name)
    if not name or name == "fin":
        name = "element"
    idx = 2
    current = name
    while current in names:
        current = "{}{}".format(name, idx)
        idx += 1
    return current


def _save_user_model_list(model_name, beam_list, qcall=None):
    _SIM_DATA.lib_file_write(
        _USER_MODEL_LIST_FILENAME[model_name],
        pkjson.dump_bytes(beam_list),
        qcall=qcall,
    )
    return beam_list


def _set_parameters(v, data, plot_reports, run_dir, qcall=None):
    report = data.report
    is_for_rsopt = _SIM_DATA.is_for_rsopt(report)
    dm = data.models
    (
        v.beamlineOptics,
        v.beamlineOpticsParameters,
        beamline_info,
    ) = _generate_beamline_optics(report, data, qcall=qcall)
    v.beamlineFirstElementPosition = _get_first_element_position(report, data)
    v[report] = 1
    for k in _OUTPUT_FOR_MODEL:
        v["{}Filename".format(k)] = _OUTPUT_FOR_MODEL[k].filename
    v.srwMain = _generate_srw_main(data, plot_reports, beamline_info)
    if _SIM_DATA.srw_is_background_report(report) and "beamlineAnimation" not in report:
        if sirepo.mpi.cfg().in_slurm:
            v.sbatchBackup = "1"
        if report == "multiElectronAnimation":
            if dm.multiElectronAnimation.calcCoherence == "1":
                v.multiElectronCharacteristic = 41
            if dm.multiElectronAnimation.wavefrontSource == "cmd":
                if not dm.multiElectronAnimation.coherentModesFile:
                    raise AssertionError("No Coherent Modes File selected")
                v.coherentModesFile = dm.multiElectronAnimation.coherentModesFile
        elif report == "coherentModesAnimation":
            c = data.models.coherentModesAnimation
            if sirepo.mpi.cfg().cores < _MIN_CORES and not sirepo.mpi.cfg().in_slurm:
                _core_error(sirepo.mpi.cfg().cores)
            if sirepo.mpi.cfg().in_slurm and c.sbatchCores < _MIN_CORES:
                _core_error(c.sbatchCores)
            v.multiElectronCharacteristic = 61
            v.mpiGroupCount = dm.coherentModesAnimation.mpiGroupCount
            v.multiElectronFileFormat = "h5"
            v.multiElectronAnimationFilename = _OUTPUT_FOR_MODEL[report].basename


def _superscript(val):
    return re.sub(r"\^2", "\u00B2", val)


def _superscript_2(val):
    return re.sub(r"\^0", "\u00B0", val)


def _trim(v):
    res = ""
    for l in v.split("\n"):
        res += l.rstrip() + "\n"
    x = res.rstrip("\n") + "\n"
    return x


def _unique_name(items, field, template):
    # TODO(pjm): this is the same logic as sirepo.js uniqueName()
    values = PKDict()
    for item in items:
        values[item[field]] = True
    index = 1
    while True:
        found_it = False
        id = template.replace("{}", str(index))
        if id in values:
            index += 1
        else:
            return id


def _update_model_fields(models):
    # Ensure method and magnetic field values are valid
    st = models.simulation.sourceType
    ut = models.tabulatedUndulator.undulatorType
    magnetic_field = 1
    if st == "a" or _SIM_DATA.srw_is_tabulated_undulator_with_magnetic_file(st, ut):
        magnetic_field = 2
    models.simulation.magneticField = magnetic_field
    is_ideal_undulator = _SIM_DATA.srw_is_idealized_undulator(st, ut)
    if is_ideal_undulator:
        models.fluxAnimation.magneticField = 1
    elif st == "a":
        models.fluxAnimation.magneticField = 2
    if _SIM_DATA.srw_is_tabulated_undulator_source(models.simulation):
        if is_ideal_undulator:
            models.tabulatedUndulator.gap = 0.0
    if int(models.simulation.samplingMethod) == 2:
        models.simulation.sampleFactor = 0
    if int(models.sourceIntensityReport.samplingMethod) == 2:
        models.sourceIntensityReport.sampleFactor = 0
    # und_g and und_ph API units are mm rather than m
    models.tabulatedUndulator.gap *= 1000
    models.tabulatedUndulator.phase *= 1000


def _update_models_for_report(report, models):
    if report == "fluxAnimation":
        models.fluxReport = models[report].copy()
    elif _SIM_DATA.is_watchpoint(report) or report == "sourceIntensityReport":
        # render the watchpoint report settings in the initialIntensityReport template slot
        models.initialIntensityReport = models[report].copy()
    if report == "sourceIntensityReport":
        models.sourceIntensityReport.magneticField = models.simulation.magneticField
        models.simulation.update(models.sourceIntensityReport)
    elif report == "coherentModesAnimation":
        models.simulation.update(models.coherentModesAnimation)
        models.multiElectronAnimation.numberOfMacroElectrons = (
            models.coherentModesAnimation.numberOfMacroElectrons
        )
    if (
        report == "multiElectronAnimation"
        and models.multiElectronAnimation.photonEnergyBandWidth > 0
    ):
        models.multiElectronAnimation.photonEnergyIntegration = 1
        half_width = float(models.multiElectronAnimation.photonEnergyBandWidth) / 2.0
        models.simulation.photonEnergy = float(models.simulation.photonEnergy)
        models.simulation.finalPhotonEnergy = (
            models.simulation.photonEnergy + half_width
        )
        models.simulation.photonEnergy -= half_width
    else:
        models.multiElectronAnimation.photonEnergyIntegration = 0
        models.simulation.finalPhotonEnergy = -1.0


def _update_report_labels(out, vals):
    def _template_text(text):
        return text.format(**vals)

    for f in ("title", "subtitle", "units", "labels", "filename"):
        if f not in out:
            continue
        if type(out[f]) == list:
            for idx in range(len(out[f])):
                out[f][idx] = _template_text(out[f][idx])
        else:
            out[f] = _template_text(out[f])


def _update_report_range(report, ar2d, x_range, y_range):
    horizontalStart = (report.horizontalOffset - report.horizontalSize / 2) * 1e-3
    horizontalEnd = (report.horizontalOffset + report.horizontalSize / 2) * 1e-3
    verticalStart = (report.verticalOffset - report.verticalSize / 2) * 1e-3
    verticalEnd = (report.verticalOffset + report.verticalSize / 2) * 1e-3
    ar2d, x_range, y_range = _extend_plot(
        ar2d,
        x_range,
        y_range,
        horizontalStart,
        horizontalEnd,
        verticalStart,
        verticalEnd,
    )
    x_left, x_right = np.clip(x_range[:2], horizontalStart, horizontalEnd)
    y_left, y_right = np.clip(y_range[:2], verticalStart, verticalEnd)
    x = np.linspace(x_range[0], x_range[1], int(x_range[2]))
    y = np.linspace(y_range[0], y_range[1], int(y_range[2]))
    xsel = (x >= x_left) & (x <= x_right)
    ysel = (y >= y_left) & (y <= y_right)
    ar2d = np.compress(xsel, np.compress(ysel, ar2d, axis=0), axis=1)
    return (
        ar2d,
        [x_left, x_right, np.shape(ar2d)[1]],
        [y_left, y_right, np.shape(ar2d)[0]],
    )


def _user_model_map(model_list, field):
    res = PKDict()
    for model in model_list:
        res[model[field]] = model
    return res


def _validate_data(data, schema):
    # ensure enums match, convert ints/floats, apply scaling
    template_common.validate_models(data, schema)
    for item_id in data.models.propagation:
        _validate_propagation(data.models.propagation[item_id][0])
        _validate_propagation(data.models.propagation[item_id][1])
    _validate_propagation(data.models.postPropagation)


def _validate_propagation(prop):
    for i in range(len(prop)):
        prop[i] = int(prop[i]) if i in (0, 1, 3, 4) else float(prop[i])


def _validate_safe_zip(zip_file_name, target_dir=".", *args):
    """Determine whether a zip file is safe to extract from

    Performs the following checks:

        - Each file must end up at or below the target directory
        - Files must be 100MB or smaller
        - If possible to determine, disallow "non-regular" and executable files
        - Existing files cannot be overwritten

    Args:
        zip_file_name (str): name of the zip file to examine
        target_dir (str): name of the directory to extract into (default to current directory)
        *args: list of validator functions taking a zip file as argument and returning True or False and a string
    Throws:
        AssertionError if any test fails, otherwise completes silently
    """

    def path_is_sub_path(path, dir_name):
        real_dir = os.path.realpath(dir_name)
        end_path = os.path.realpath(real_dir + "/" + path)
        return end_path.startswith(real_dir)

    def file_exists_in_dir(file_name, dir_name):
        return os.path.exists(os.path.realpath(dir_name + "/" + file_name))

    def file_attrs_ok(attrs):
        # ms-dos attributes only use two bytes and don't contain much useful info, so pass them
        if attrs < 2 << 16:
            return True

        # UNIX file attributes live in the top two bytes
        mask = attrs >> 16
        is_file_or_dir = mask & (0o0100000 | 0o0040000) != 0
        no_exec = mask & (0o0000100 | 0o0000010 | 0o0000001) == 0

        return is_file_or_dir and no_exec

    # 100MB
    max_file_size = 100000000

    zip_file = zipfile.ZipFile(zip_file_name)

    for f in zip_file.namelist():
        i = zip_file.getinfo(f)
        s = i.file_size
        attrs = i.external_attr

        assert path_is_sub_path(
            f, target_dir
        ), "Cannot extract {} above target directory".format(f)
        assert s <= max_file_size, "{} too large ({} > {})".format(
            f, str(s), str(max_file_size)
        )
        assert file_attrs_ok(attrs), "{} not a normal file or is executable".format(f)
        assert not file_exists_in_dir(
            f, target_dir
        ), "Cannot overwrite file {} in target directory {}".format(f, target_dir)

    for validator in args:
        res, err_string = validator(zip_file)
        assert res, "{} failed validator: {}".format(
            os.path.basename(zip_file_name), err_string
        )


def _wavefront_pickle_filename(el_id, is_processed=False):
    f = f"wid-{el_id}" if el_id else "initial"
    if not is_processed:
        f = _PREPROCESS_PREFIX + f
    return f"{f}.pkl"


def _write_rsopt_files(data, run_dir, ctx):
    for f in _export_rsopt_files().values():
        pkio.write_text(
            run_dir.join(f),
            (
                python_source_for_model(data, data.report, None, plot_reports=False)
                if f == f"{_SIM_DATA.EXPORT_RSOPT}.py"
                else template_common.render_jinja(SIM_TYPE, ctx, f)
            ),
        )


def _write_rsopt_zip(data, ctx):
    def _write(zip_file, path):
        zip_file.writestr(
            path,
            (
                python_source_for_model(data, data.report, None, plot_reports=False)
                if path == f"{_SIM_DATA.EXPORT_RSOPT}.py"
                else template_common.render_jinja(SIM_TYPE, ctx, path)
            ),
        )

    filename = f"{_SIM_DATA.EXPORT_RSOPT}.zip"
    with zipfile.ZipFile(
        f"{_SIM_DATA.EXPORT_RSOPT}.zip",
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        allowZip64=True,
    ) as z:
        for f in _export_rsopt_files().values():
            _write(z, f)
        for f in ctx.libFiles:
            z.write(f, f)
    return PKDict(
        content_type="application/zip",
        filename=filename,
    )
