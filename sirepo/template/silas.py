# -*- coding: utf-8 -*-
"""SILAS execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from scipy import constants
from sirepo import simulation_db
from sirepo.template import template_common
from rslaser.pulse import pulse
from rslaser.utils import srwl_uti_data
import csv
import h5py
import math
import numpy
import re
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_CRYSTAL_CSV_FILE = "crystal.csv"
_SUMMARY_CSV_FILE = "wavefront.csv"
_INITIAL_LASER_FILE = "initial-laser.npy"
_FINAL_LASER_FILE = "final-laser.npy"


def background_percent_complete(report, run_dir, is_running):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    if report == "animation":
        line = template_common.read_last_csv_line(run_dir.join(_SUMMARY_CSV_FILE))
        m = re.search(r"^(\d+)", line)
        if m and int(m.group(1)) > 0:
            res.frameCount = int((int(m.group(1)) + 1) / 2)
            res.wavefrontsFrameCount = _counts_for_beamline(
                res.frameCount, data.models.beamline
            )[0]
            total_count = _total_frame_count(data)
            res.percentComplete = res.frameCount * 100 / total_count
        return res
    assert report == "crystalAnimation"
    count = 0
    path = run_dir.join(_CRYSTAL_CSV_FILE)
    if path.exists():
        with pkio.open_text(str(path)) as f:
            for line in f:
                count += 1
        # first two lines are axis points
        if count > 2:
            plot_count = int((count - 2) / 2)
            res.frameCount = plot_count
            res.percentComplete = (
                plot_count
                * 100
                / (
                    1
                    + data.models.crystalSettings.steps
                    / data.models.crystalSettings.plotInterval
                )
            )
    return res


def post_execution_processing(success_exit, run_dir, **kwargs):
    if success_exit:
        return None
    return _parse_silas_log(run_dir)


def get_data_file(run_dir, model, frame, options):
    if model in ("laserPulseAnimation", "laserPulse2Animation"):
        return _INITIAL_LASER_FILE
    if model in ("laserPulse3Animation", "laserPulse4Animation"):
        return _FINAL_LASER_FILE
    if model == "wavefrontSummaryAnimation":
        return _SUMMARY_CSV_FILE
    if "wavefrontAnimation" in model:
        sim_in = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        return _wavefront_filename_for_index(
            sim_in,
            sim_in.models[model].id,
            frame,
        )
    if "plotAnimation" in model:
        return _CRYSTAL_CSV_FILE
    if model == "crystal3dAnimation":
        return "intensity.npy"
    raise AssertionError("unknown model={}".format(model))


def python_source_for_model(data, model, qcall, **kwargs):
    if model in ("crystal3dAnimation", "plotAnimation", "plot2Animation"):
        data.report = "crystalAnimation"
    else:
        data.report = "animation"
    return _generate_parameters_file(data)


def save_sequential_report_data(run_dir, sim_in):
    if sim_in.report == "initialIntensityReport":
        _extract_laser_pulse_intensity_report(run_dir, sim_in)
    if sim_in.report == "initialPhaseReport":
        _extract_laser_pulse_phase_report(run_dir, sim_in)


def sim_frame(frame_args):
    filename = _wavefront_filename_for_index(
        frame_args.sim_in,
        frame_args.id,
        frame_args.frameIndex,
    )
    with h5py.File(filename, "r") as f:
        wfr = f["wfr"]
        points = numpy.array(wfr)
        return PKDict(
            title="S={}m (E={} eV)".format(
                _format_float(wfr.attrs["pos"]),
                frame_args.sim_in.models.gaussianBeam.photonEnergy,
            ),
            subtitle="",
            x_range=[wfr.attrs["xStart"], wfr.attrs["xFin"], len(points[0])],
            x_label="Horizontal Position [m]",
            y_range=[wfr.attrs["yStart"], wfr.attrs["yFin"], len(points)],
            y_label="Vertical Position [m]",
            z_matrix=points.tolist(),
            summaryData=_summary_data(frame_args),
        )


def sim_frame_crystal3dAnimation(frame_args):
    intensity = numpy.load("intensity.npy")
    return PKDict(
        title=" ",
        indices=numpy.load("indices.npy").flatten().tolist(),
        vertices=numpy.load("vertices.npy").flatten().tolist(),
        intensity=intensity.tolist(),
        intensity_range=[numpy.min(intensity), numpy.max(intensity)],
    )


def sim_frame_laserPulse1Animation(frame_args):
    return _laser_pulse_report(
        1, _INITIAL_LASER_FILE, "Before Propagation", "RMS x [m]"
    )


def sim_frame_laserPulse2Animation(frame_args):
    return _laser_pulse_report(
        3, _INITIAL_LASER_FILE, "Before Propagation", "Pulse Intensity"
    )


def sim_frame_laserPulse3Animation(frame_args):
    return _laser_pulse_report(1, _FINAL_LASER_FILE, "After Propagation", "RMS x [m]")


def sim_frame_laserPulse4Animation(frame_args):
    return _laser_pulse_report(
        3, _FINAL_LASER_FILE, "After Propagation", "Pulse Intensity"
    )


def sim_frame_plotAnimation(frame_args):
    return _crystal_plot(frame_args, "xv", "ux", "[m]", 1e-2)


def sim_frame_plot2Animation(frame_args):
    return _crystal_plot(frame_args, "zv", "uz", "[m]", 1e-2)


def sim_frame_wavefrontSummaryAnimation(frame_args):
    beamline = frame_args.sim_in.models.beamline
    if "element" not in frame_args:
        frame_args.element = "all"
    idx = 0
    title = ""
    if frame_args.element != "all":
        # find the element index from the element id
        for item in beamline:
            if item.id == int(frame_args.element):
                title = item.title
                break
            idx += 1
    # TODO(pjm): use column headings from csv
    cols = ["count", "pos", "sx", "sy", "xavg", "yavg"]
    v = numpy.genfromtxt(
        str(frame_args.run_dir.join(_SUMMARY_CSV_FILE)), delimiter=",", skip_header=1
    )
    if frame_args.element != "all":
        # the wavefront csv include intermediate values, so take every other row
        counts = _counts_for_beamline(int((v[-1][0] + 1) / 2), beamline)[1]
        v2 = []
        for row in counts[idx]:
            v2.append(v[(row - 1) * 2])
        v = numpy.array(v2)
    # TODO(pjm): generalize, use template_common parameter_plot()?
    plots = []
    for col in ("sx", "sy"):
        plots.append(
            PKDict(
                points=v[:, cols.index(col)].tolist(),
                label=f"{col} [m]",
            )
        )
    x = v[:, cols.index("pos")].tolist()
    return PKDict(
        aspectRatio=1 / 5.0,
        title="{} Wavefront Dimensions".format(title),
        x_range=[float(min(x)), float(max(x))],
        y_label="",
        x_label="s [m]",
        x_points=x,
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
        summaryData=_summary_data(frame_args),
    )


def stateful_compute_mesh_dimensions(data):
    f = {
        k: _SIM_DATA.lib_file_abspath(
             _SIM_DATA.lib_file_name_with_model_field("laserPulse", k, data.args[k])
        )
        for k in data.args
    }
    m = pulse.LaserPulse(
        params=PKDict(nslice=1),
        files=PKDict(f)
    ).slice_wfr(0).mesh
    return PKDict(
        numSliceMeshPoints=[m.nx, m.ny]
    )


def stateless_compute_rms_size(data):
    return _compute_rms_size(data.args)


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _build_pulse(model):
    f = PKDict(
        ccd=_SIM_DATA.lib_file_name_with_model_field("laserPulse", "ccd", model.ccd),
        meta=_SIM_DATA.lib_file_name_with_model_field("laserPulse", "meta", model.meta),
        wfs=_SIM_DATA.lib_file_name_with_model_field("laserPulse", "wfs", model.wfs),
    ) if model.geometryFromFiles == "1" else None
    return pulse.LaserPulse(
        params=PKDict(
            chirp=model.chirp,
            dist_waist=model.distFromWaist,
            mx=model.modeOrder[0],
            my=model.modeOrder[1],
            nslice=model.numSlices,
            num_sig_long=model.numSigmas[0],
            num_sig_trans=model.numSigmas[1],
            nx_slice=model.numSliceMeshPoints[0],
            ny_slice=model.numSliceMeshPoints[1],
            pad_factor=model.padFactor,
            photon_e_ev=model.photonEnergy,
            poltype=int(model.polarization),
            pulseE=model.totalEnergy,
            sigx_waist=model.waistSize[0],
            sigy_waist=model.waistSize[1],
            tau_fwhm=model.tauFWHM,
        ),
        files=f,
    )


def _compute_rms_size(data):
    wavefrontEnergy = data.gaussianBeam.photonEnergy
    n0 = data.crystal.refractionIndex
    L_cryst = data.crystal.width * 1e-2
    dfL = data.mirror.focusingError
    L_cav = data.simulationSettings.cavity_length
    L_eff = L_cav + (1 / n0 - 1) * L_cryst
    beta0 = math.sqrt(L_eff * (L_cav / 4 + dfL) - L_eff**2 / 4)
    lam = constants.c * constants.value("Planck constant in eV/Hz") / wavefrontEnergy
    return PKDict(rmsSize=math.sqrt(lam * beta0 / 4 / math.pi))


def _counts_for_beamline(total_frames, beamline):
    # start at 2nd element, loop forward and backward across beamline
    counts = [0 for _ in beamline]
    idx = 1
    direction = 1
    frames = [[] for _ in beamline]

    for i in range(total_frames):
        counts[idx] += 1
        frames[idx].append(i + 1)
        idx += direction
        if idx < 0 or idx > len(counts) - 1:
            direction *= -1
            idx += 2 * direction
    return counts, frames


def _crystal_plot(frame_args, x_column, y_column, x_heading, scale):
    x = None
    plots = []
    with open(str(frame_args.run_dir.join(_CRYSTAL_CSV_FILE))) as f:
        for r in csv.reader(f):
            if x is None and r[0] == x_column:
                r.pop(0)
                r.pop(0)
                x = [float(v) * scale for v in r]
            elif r[0] == y_column:
                r.pop(0)
                t = r.pop(0)
                plots.append(
                    PKDict(
                        points=[float(v) for v in r],
                        label="{:.1f} sec".format(float(t)),
                    )
                )
    return PKDict(
        title="",
        x_range=[min(x), max(x)],
        y_label="Temperature [°C]",
        x_label=x_heading,
        x_points=x,
        plots=plots,
        y_range=template_common.compute_plot_color_and_range(plots),
        summaryData=_summary_data(frame_args),
    )


def _extract_laser_pulse_intensity_report(run_dir, sim_in):
    template_common.write_sequential_result(
        _initial_laser_pulse_intensity_plot(sim_in.models.laserPulse),
        run_dir=run_dir,
    )


def _extract_laser_pulse_phase_report(run_dir, sim_in):
    template_common.write_sequential_result(
        _initial_laser_pulse_phase_plot(sim_in.models.laserPulse),
        run_dir=run_dir,
    )


def _format_float(v):
    return float("{:.4f}".format(v))


def _initial_laser_pulse_intensity_plot(model):
    p = _build_pulse(model)
    w = p.slice_wfr(0)
    m = w.mesh
    z = srwl_uti_data.calc_int_from_elec(w).tolist()

    return PKDict(
        title="Intensity",
        x_range=[m.xStart, m.xFin, m.nx],
        y_range=[m.yStart, m.yFin, m.ny],
        x_label="Horizontal Position [m]",
        y_label="Vertical Position [m]",
        z_matrix=z,
    )


def _initial_laser_pulse_phase_plot(model):
    p = _build_pulse(model)
    z, m = srwl_uti_data.calc_int_from_wfr(
        p.slice_wfr(0),
        _pol=int(model.polarization),
        _int_type=4,
        _pr=False,
    )
    z = numpy.array(z).reshape(m.ny, m.nx).tolist()
    return PKDict(
        title="Phase",
        x_range=[m.xStart, m.xFin, m.nx],
        y_range=[m.yStart, m.yFin, m.ny],
        x_label="Horizontal Position [m]",
        y_label="Vertical Position [m]",
        z_matrix=z,
    )


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    v.report = data.report
    v.laserPulse = data.models.laserPulse
    res += template_common.render_jinja(SIM_TYPE, v, "laserPulse.py")
    if data.report in (
        "initialIntensityReport",
        "initialPhaseReport"
    ):
        return res + template_common.render_jinja(SIM_TYPE, v)
    if data.report == "animation":
        beamline = data.models.beamline
        data.models.crystal = _get_crystal(data)
        v.leftMirrorFocusingError = beamline[0].focusingError
        v.rightMirrorFocusingError = beamline[-1].focusingError
        v.summaryCSV = _SUMMARY_CSV_FILE
        v.initialLaserFile = _INITIAL_LASER_FILE
        v.finalLaserFile = _FINAL_LASER_FILE
        return res + template_common.render_jinja(SIM_TYPE, v)
    if data.report == "crystalAnimation":
        v.crystalCSV = _CRYSTAL_CSV_FILE
        return res + template_common.render_jinja(SIM_TYPE, v, "crystal.py")
    assert False, "invalid param report: {}".format(data.report)


def _get_crystal(data):
    return data.models.beamline[1]


def _laser_pulse_report(value_index, filename, title, label):
    values = numpy.load(filename)
    return template_common.parameter_plot(
        values[0].tolist(),
        [
            PKDict(
                points=values[value_index].tolist(),
                label=label,
            ),
        ],
        PKDict(),
        PKDict(
            title=title,
            y_label="",
            x_label="s [m]",
        ),
    )


def _parse_silas_log(run_dir):
    res = ""
    path = run_dir.join(template_common.RUN_LOG)
    if not path.exists():
        return res
    with pkio.open_text(str(path)) as f:
        for line in f:
            m = re.search(r"^\s*\*+\s+Error:\s+(.*)$", line)
            if m:
                err = m.group(1)
                if re.search("Unable to evaluate function at point", err):
                    return "Point evaulated outside of mesh boundary. Consider increasing Mesh Density or Boundary Tolerance."
                res += err + "\n"
    if res:
        return res
    return "An unknown error occurred"


def _summary_data(frame_args):
    return PKDict(
        crystalWidth=frame_args.sim_in.models.beamline[1].width,
    )


def _total_frame_count(data):
    return (
        data.models.simulationSettings.n_reflections
        * 2
        * (len(data.models.beamline) - 1)
        + 1
    )


def _wavefront_filename_for_index(sim_in, item_id, frame):
    idx = 0
    beamline = sim_in.models.beamline
    for item in beamline:
        if str(item_id) == str(item.id):
            break
        idx += 1
    total_count = _total_frame_count(sim_in)
    counts = _counts_for_beamline(total_count, beamline)[1]
    counts = counts[idx]
    file_index = counts[frame]
    return f"wfr{file_index:05d}.h5"
