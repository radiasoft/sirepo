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
import csv
import h5py
import math
import numpy
import re
import sirepo.sim_data

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_CRYSTAL_CSV_FILE = "crystal.csv"
_RESULTS_FILE = "results.h5"

_DATA_PATHS = PKDict(
    crystalAnimation=(),
    initialIntensityReport=("ranges", "intensity"),
    initialPhaseReport=("ranges", "phase"),
    watchpointReport=("ranges", "intensity", "phase"),
)


def background_percent_complete(report, run_dir, is_running):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
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
    if model in ("plotAnimation", "plot2Animation"):
        return _CRYSTAL_CSV_FILE
    if model == "crystal3dAnimation":
        return "intensity.npy"
    if model in (
        "initialIntensityReport",
        "initialPhaseReport",
    ) or _SIM_DATA.is_watchpoint(model):
        return _RESULTS_FILE
    raise AssertionError("unknown model={}".format(model))


def python_source_for_model(data, model, qcall, **kwargs):
    if model in ("crystal3dAnimation", "plotAnimation", "plot2Animation"):
        data.report = "crystalAnimation"
    else:
        data.report = model or _last_watchpoint(data) or "initialIntensityReport"
    return _generate_parameters_file(data)


def save_sequential_report_data(run_dir, sim_in):
    r = sim_in.report
    if r == "initialIntensityReport":
        _extract_initial_intensity_report(run_dir, sim_in)
    if r == "initialPhaseReport":
        _extract_initial_phase_report(run_dir, sim_in)
    if _SIM_DATA.is_watchpoint(r):
        _extract_watchpoint_report(run_dir, sim_in)


def sim_frame_crystal3dAnimation(frame_args):
    intensity = numpy.load("intensity.npy")
    return PKDict(
        title=" ",
        indices=numpy.load("indices.npy").flatten().tolist(),
        vertices=numpy.load("vertices.npy").flatten().tolist(),
        intensity=intensity.tolist(),
        intensity_range=[numpy.min(intensity), numpy.max(intensity)],
    )


def sim_frame_plotAnimation(frame_args):
    return _crystal_plot(frame_args, "xv", "ux", "[m]", 1e-2)


def sim_frame_plot2Animation(frame_args):
    return _crystal_plot(frame_args, "zv", "uz", "[m]", 1e-2)


def stateful_compute_mesh_dimensions(data, **kwargs):
    f = {
        k: _SIM_DATA.lib_file_abspath(
            _SIM_DATA.lib_file_name_with_model_field("laserPulse", k, data.args[k])
        )
        for k in data.args
    }
    m = pulse.LaserPulse(params=PKDict(nslice=1), files=PKDict(f)).slice_wfr(0).mesh
    return PKDict(numSliceMeshPoints=[m.nx, m.ny])


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


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


def _data_paths(report):
    r = _SIM_DATA.WATCHPOINT_REPORT if _SIM_DATA.is_watchpoint(report) else report
    return _DATA_PATHS[r]


def _extract_initial_intensity_report(run_dir, sim_in):
    template_common.write_sequential_result(
        _laser_pulse_plot(run_dir, "intensity", sim_in),
        run_dir=run_dir,
    )


def _extract_initial_phase_report(run_dir, sim_in):
    template_common.write_sequential_result(
        _laser_pulse_plot(run_dir, "phase", sim_in),
        run_dir=run_dir,
    )


def _extract_watchpoint_report(run_dir, sim_in):
    template_common.write_sequential_result(
        _laser_pulse_plot(
            run_dir,
            sim_in.models[sim_in.report].dataType,
            sim_in,
        ),
        run_dir=run_dir,
    )


def _laser_pulse_plot(run_dir, data_type, sim_in):
    with h5py.File(run_dir.join(_RESULTS_FILE), "r") as f:
        d = template_common.h5_to_dict(f)
        r = d.ranges
        z = d[data_type]
        return PKDict(
            title=data_type.capitalize()
            + " Slice #"
            + str(_slice_number(sim_in, sim_in.report) + 1),
            x_range=[r.x[0], r.x[1], len(z)],
            y_range=[r.y[0], r.y[1], len(z[0])],
            x_label="Horizontal Position [m]",
            y_label="Vertical Position [m]",
            z_matrix=z,
        )


def _generate_beamline_elements(data):
    def _callback(state, element, dz):
        if dz:
            state.res += f'(Drift({round(dz, 9)}), ["default"]),\n'
        if element.type == "watch" or element.get("isDisabled"):
            return
        if element.type == "lens":
            state.res += f'(Lens({element.focalLength}), ["default"]),\n'
        elif element.type == "mirror":
            state.res += "(Mirror(), []),\n"
        elif element.type == "crystal":
            if element.origin == "reuse":
                return
            state.res += _generate_crystal(element)
        else:
            raise AssertionError("unknown element type={}".format(element.type))

    state = PKDict(res="")
    _iterate_beamline(state, data, _callback)
    return state.res


def _generate_beamline_indices(data):
    def _callback(state, element, dz):
        if dz:
            state.res.append(str(state.idx))
            state.idx += 1
        if element.get("isDisabled") or element.type == "watch":
            return
        if element.type == "crystal":
            if element.origin == "new":
                state.id_to_index[element.id] = state.idx
            else:
                state.res.append(str(state.id_to_index[element.reuseCrystal]))
                return
        state.res.append(str(state.idx))
        state.idx += 1

    state = PKDict(res=[], idx=0, id_to_index=PKDict())
    _iterate_beamline(state, data, _callback)
    return ", ".join(state.res)


def _generate_crystal(crystal):
    return f"""(
        Crystal(
            params=PKDict(
                l_scale={crystal.l_scale},
                length={crystal.length * 1e-2},
                n0={_slice_n_field(crystal, 'n0')},
                n2={_slice_n_field(crystal, 'n2')},
                nslice={crystal.nslice},
                A={crystal.A},
                B={crystal.B},
                C={crystal.C},
                D={crystal.D},
                population_inversion=PKDict(
                    n_cells={crystal.inversion_n_cells},
                    mesh_extent={crystal.inversion_mesh_extent},
                    crystal_alpha={crystal.crystal_alpha},
                    pump_waist={crystal.pump_waist},
                    pump_wavelength={crystal.pump_wavelength},
                    pump_energy={crystal.pump_energy},
                    pump_type="{crystal.pump_type}",
                ),
            ),
        ),
        ["{crystal.propagationType}", {crystal.calc_gain == "1"}, {crystal.radial_n2 == "1"}],
    ),\n"""


def _generate_parameters_file(data):
    r = data.report
    res, v = template_common.generate_parameters_file(data)
    v.simId = data.models.simulation.simulationId
    v.report = r
    v.dataPaths = _data_paths(r)
    v.laserPulse = data.models.laserPulse
    v.resultsFile = _RESULTS_FILE
    v.sliceNumber = _slice_number(data, r)
    if r == "crystalAnimation":
        v.crystalLength = _get_crystal(data).length
        v.crystalCSV = _CRYSTAL_CSV_FILE
        return res + template_common.render_jinja(SIM_TYPE, v, "crystal.py")
    if data.models.laserPulse.distribution == "file":
        for f in ("ccd", "meta", "wfs"):
            v[f"{f}File"] = _SIM_DATA.lib_file_name_with_model_field(
                "laserPulse", f, data.models.laserPulse[f]
            )
    if _SIM_DATA.is_watchpoint(r):
        v.beamlineElements = _generate_beamline_elements(data)
        v.beamlineIndices = _generate_beamline_indices(data)
    return res + template_common.render_jinja(SIM_TYPE, v)


def _get_crystal(data):
    crystals = [
        x for x in data.models.beamline if x.type == "crystal" and x.origin == "new"
    ]
    for e in crystals:
        if e.id == data.models.crystalCylinder.crystal:
            return e
    return crystals[0]


def _iterate_beamline(state, data, callback):
    prev = 0
    for e in data.models.beamline:
        dz = e.position - prev
        prev = e.position
        callback(state, e, dz)
        if e.id == _SIM_DATA.watchpoint_id(data.report):
            break


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


def _last_watchpoint(data):
    res = None
    for b in data.models.beamline:
        if b.type == "watch":
            res = b
    return f"watchpointReport{b.id}" if res else None


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


def _slice_n_field(crystal, field):
    return (
        crystal[field][0 : crystal.nslice]
        if crystal.nslice <= 6
        else f"interpolate_across_slice({crystal.length * 1e-2}, {crystal.nslice}, {crystal[field]})"
    )


def _slice_number(data, report_name):
    n = (
        data.models[report_name].sliceNumber
        if report_name in data.models
        and "sliceNumber" in data.models[report_name]
        and data.models[report_name].sliceNumber
        else 0
    )
    if n + 1 > data.models.laserPulse.nslice:
        n = 0
    return n


def _summary_data(frame_args):
    return PKDict(
        crystalLength=_get_crystal(frame_args.sim_in).length,
    )
