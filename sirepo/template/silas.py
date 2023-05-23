# -*- coding: utf-8 -*-
"""SILAS execution template.

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdc, pkdlog
from sirepo import simulation_db
from sirepo.template import template_common
import csv
import h5py
import numpy
import re
import sirepo.sim_data

# TODO(pjm): currently aligned with rslaser version
# git checkout `git rev-list -n 1 --first-parent --before="2023-04-24 13:37" main`

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_CRYSTAL_CSV_FILE = "crystal.csv"
_RESULTS_FILE = "results{}.h5"
_CRYSTAL_FILE = "crystal{}.h5"


def background_percent_complete(report, run_dir, is_running):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    res = PKDict(
        percentComplete=0,
        frameCount=0,
    )
    if report == "beamlineAnimation":
        return _beamline_animation_percent_complete(run_dir, res, data)
    if report in _SIM_DATA.SOURCE_REPORTS:
        return _initial_intensity_percent_complete(
            run_dir, res, data, _SIM_DATA.SOURCE_REPORTS
        )
    return _crystal_animation_percent_complete(run_dir, res, data)


def get_data_file(run_dir, model, frame, options):
    if model in ("plotAnimation", "plot2Animation"):
        return _CRYSTAL_CSV_FILE
    if model == "crystal3dAnimation":
        return "intensity.npy"
    if model == "beamlineAnimation0" or model in _SIM_DATA.SOURCE_REPORTS:
        return _RESULTS_FILE.format(0)
    if "beamlineAnimation" in model:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        for r in _beamline_animation_percent_complete(
            run_dir, PKDict(frameCount=0), data
        ).outputInfo:
            if r.modelKey == model:
                return r.filename
    raise AssertionError("unknown model={}".format(model))


def post_execution_processing(success_exit, run_dir, **kwargs):
    if success_exit:
        return None
    return _parse_silas_log(run_dir)


def python_source_for_model(data, model, qcall, **kwargs):
    if model in ("crystal3dAnimation", "plotAnimation", "plot2Animation"):
        data.report = "crystalAnimation"
    else:
        if model:
            model = re.sub("beamlineAnimation", "watchpointReport", model)
        data.report = model or ""
    return _generate_parameters_file(data)


def sim_frame(frame_args):
    def _crystal_or_watch(frame_args, element):
        if element and element.type == "crystal":
            return frame_args.crystalPlot
        return frame_args.watchpointPlot

    r = frame_args.frameReport
    frame_args.sim_in.report = r
    count, element = _report_to_file_index(frame_args.sim_in, r)
    if "beamlineAnimation" in r or r in _SIM_DATA.SOURCE_REPORTS:
        return _laser_pulse_plot(
            frame_args.run_dir,
            _crystal_or_watch(frame_args, element),
            frame_args.sim_in,
            count,
            element,
            frame_args.frameIndex,
        )
    raise AssertionError("unknown sim_frame report: {}".format(r))


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
    from rslaser.pulse import pulse

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


def _beamline_animation_percent_complete(run_dir, res, data):
    def _output_append(frame_count, filename, count, element, res, total_count):
        total_count += 1
        if run_dir.join(filename).exists():
            res.outputInfo.append(
                PKDict(
                    modelKey="beamlineAnimation{}".format(e.id),
                    filename=filename,
                    id=element.id,
                    frameCount=frame_count,
                )
            )
            if element.type == "watch":
                count.watch += 1
            else:
                count.crystal += 1
            res.frameCount += 1

    def _file(element, count):
        return PKDict(
            watch=_RESULTS_FILE.format(count.watch),
            crystal=_CRYSTAL_FILE.format(count.crystal),
        )[element.type]

    def _frames(element, data):
        if element.type == "watch":
            return data.models.laserPulse.nslice
        return element.nslice

    _initial_intensity_percent_complete(run_dir, res, data, ("beamlineAnimation0",))
    count = PKDict(
        watch=1,
        crystal=1,
    )
    total_count = 1
    for e in data.models.beamline:
        if e.type in ("watch", "crystal"):
            _output_append(
                _frames(e, data),
                _file(e, count),
                count,
                e,
                res,
                total_count,
            )

    res.percentComplete = res.frameCount * 100 / total_count
    return res


def _crystal_animation_percent_complete(run_dir, res, data):
    assert data.report == "crystalAnimation"
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
        summaryData=PKDict(
            crystalLength=_get_crystal(frame_args.sim_in).length,
        ),
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

    state = PKDict(res="(Watchpoint(), []),\n")
    if data.report not in _SIM_DATA.SOURCE_REPORTS:
        _iterate_beamline(state, data, _callback)
    return state.res


def _generate_beamline_indices(data):
    def _callback(state, element, dz):
        if dz:
            state.res.append(str(state.idx))
            state.idx += 1
        if element.get("isDisabled"):
            return
        if element.type == "watch":
            state.res.append("0")
            return
        if element.type == "crystal":
            if element.origin == "new":
                state.id_to_index[element.id] = state.idx
            else:
                state.res.append(str(state.id_to_index[element.reuseCrystal]))
                return
        state.res.append(str(state.idx))
        state.idx += 1

    state = PKDict(res=["0"], idx=1, id_to_index=PKDict())
    if data.report not in _SIM_DATA.SOURCE_REPORTS:
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
                    pump_gaussian_order={crystal.pump_gaussian_order},
                    pump_energy={crystal.pump_energy},
                    pump_type="{crystal.pump_type}",
                ),
            ),
        ),
        ["{crystal.propagationType}", {crystal.calc_gain == "1"}, {crystal.radial_n2 == "1"}],
    ),\n"""


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    if data.report == "crystalAnimation":
        v.crystalLength = _get_crystal(data).length
        v.crystalCSV = _CRYSTAL_CSV_FILE
        return res + template_common.render_jinja(SIM_TYPE, v, "crystal.py")
    if data.report in _SIM_DATA.SOURCE_REPORTS:
        data.models.beamline = []
    v.laserPulse = data.models.laserPulse
    if data.models.laserPulse.distribution == "file":
        for f in ("ccd", "meta", "wfs"):
            v[f"{f}File"] = _SIM_DATA.lib_file_name_with_model_field(
                "laserPulse", f, data.models.laserPulse[f]
            )
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


def _initial_intensity_percent_complete(run_dir, res, data, model_names):
    res.outputInfo = []
    if run_dir.join(_RESULTS_FILE.format(0)).exists():
        for n in model_names:
            res.outputInfo.append(
                PKDict(
                    modelKey=n,
                    filename=_RESULTS_FILE.format(0),
                    id=0,
                    frameCount=data.models.laserPulse.nslice,
                )
            )
        res.frameCount += 1
    return res


def _iterate_beamline(state, data, callback):
    prev = 0
    for e in data.models.beamline:
        dz = e.position - prev
        prev = e.position
        callback(state, e, dz)


def _laser_pulse_plot(run_dir, plot_type, sim_in, element_index, element, slice_index):
    def _cell_volume(element):
        if _is_crystal(element):
            return (
                ((2 * element.inversion_mesh_extent) / element.inversion_n_cells) ** 2
                * element.length
                / element.nslice
            )
        return None

    def _fname(element):
        if _is_crystal(element):
            return _CRYSTAL_FILE
        return _RESULTS_FILE

    def _is_crystal(element):
        return element and element.type == "crystal"

    def _is_longitudinal_plot(plot_type):
        return "longitudinal" in plot_type

    def _label(plot_type):
        if plot_type == "longitudinal_intensity":
            return "Intensity"
        if plot_type == "longitudinal_photons":
            return "Total Number of Photons"
        return "Excited States"

    def _nslice(element, file):
        if _is_crystal(element):
            return element.nslice
        return len(file)

    def _title(plot_type, slice_index):
        if plot_type in ("total_intensity", "total_phase", "excited_states"):
            return plot_type.replace("_", " ").title()
        return plot_type.capitalize() + " Slice #" + str(slice_index + 1)

    def _y_value(element, index, file, cell_volume):
        if _is_crystal(element):
            return numpy.sum(numpy.array(file[f"{index}/excited_states"]) * cell_volume)
        y = numpy.array(file[f"{index}/{plot_type}"])
        if plot_type == "longitudinal_intensity":
            return y
        return numpy.sum(y)

    with h5py.File(run_dir.join(_fname(element).format(element_index)), "r") as f:
        if _is_longitudinal_plot(plot_type):
            x = []
            y = []
            nslice = _nslice(element, f)
            if element:
                element.nslice = nslice
            for idx in range(nslice):
                x.append(idx)
                y.append(_y_value(element, idx, f, _cell_volume(element)))
            return template_common.parameter_plot(
                x,
                [
                    PKDict(
                        points=y,
                        label=_label(plot_type),
                    ),
                ],
                PKDict(),
            )
        d = template_common.h5_to_dict(f, str(slice_index))
        r = d.ranges
        z = d[plot_type]
        return PKDict(
            title=_title(plot_type, slice_index),
            x_range=[r.x[0], r.x[1], len(z)],
            y_range=[r.y[0], r.y[1], len(z[0])],
            x_label="Horizontal Position [m]",
            y_label="Vertical Position [m]",
            z_matrix=z,
        )


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


def _report_to_file_index(sim_in, report):
    if report in _SIM_DATA.SOURCE_REPORTS:
        return 0, None
    m = re.search(r"beamlineAnimation(\d+)", report)
    if not m:
        raise AssertionError("invalid watch report: {}".format(report))
    i = int(m.group(1))
    if i == 0:
        return 0, None
    count_by_type = PKDict()
    for e in sim_in.models.beamline:
        if not e.type in count_by_type:
            count_by_type[e.type] = 1
        if e.id == i:
            return count_by_type[e.type], e
        count_by_type[e.type] += 1
    raise AssertionError("{} report not found: {}".format(element_type, report))


def _slice_n_field(crystal, field):
    return (
        crystal[field][0 : crystal.nslice]
        if crystal.nslice <= 6
        else f"interpolate_across_slice({crystal.length * 1e-2}, {crystal.nslice}, {crystal[field]})"
    )
