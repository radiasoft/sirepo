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
import time

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()

_CRYSTAL_CSV_FILE = "crystal.csv"
_RESULTS_FILE = "results{}.h5"
_CRYSTAL_FILE = "crystal{}.h5"
_MAX_H5_READ_TRIES = 3


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
        return _LaserPulsePlot(
            run_dir=frame_args.run_dir,
            plot_type=_crystal_or_watch(frame_args, element),
            sim_in=frame_args.sim_in,
            element_index=count,
            element=element,
            slice_index=frame_args.frameIndex,
        ).gen()
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


def stateful_compute_n0n2_plot(data, **kwargs):
    import matplotlib.pyplot as plt
    from rslaser.optics import Crystal
    from pykern import pkcompat
    from base64 import b64encode

    def _data_url(path):
        with open(path, "rb") as f:
            return "data:image/jpeg;base64," + pkcompat.from_bytes(b64encode(f.read()))

    n = Crystal(
        params=PKDict(
            l_scale=data.model.l_scale,
            length=data.model.length * 1e-2,
            nslice=data.model.nslice,
            A=data.model.A,
            B=data.model.B,
            C=data.model.C,
            D=data.model.D,
            pop_inversion_n_cells=data.model.inversion_n_cells,
            pop_inversion_mesh_extent=data.model.inversion_mesh_extent,
            pop_inversion_crystal_alpha=data.model.crystal_alpha,
            pop_inversion_pump_waist=data.model.pump_waist,
            pop_inversion_pump_wavelength=data.model.pump_wavelength,
            pop_inversion_pump_gaussian_order=data.model.pump_gaussian_order,
            pop_inversion_pump_energy=data.model.pump_energy,
            pop_inversion_pump_type=data.model.pump_type,
            pop_inversion_pump_rep_rate=data.model.pump_rep_rate,
            pop_inversion_pump_offset_x=data.model.pump_offset_x,
            pop_inversion_pump_offset_y=data.model.pump_offset_y,
        )
    ).calc_n0n2(set_n=True, mesh_density=data.model.mesh_density)
    p = pkio.py_path("n0n2_plot.png")
    plt.clf()
    fig, axes = plt.subplots(2)
    fig.suptitle(f"N0 N2 Plot")
    axes[0].plot(range(len(n[0])), n[0])
    axes[1].plot(range(len(n[0])), n[1])
    axes[0].set_ylabel("N0")
    axes[1].set_ylabel("N2")
    plt.xlabel("Slice")
    plt.savefig(p)
    return PKDict(
        uri=_data_url(p),
        A=round(n[2][0][0], 9),
        B=round(n[2][0][1], 9),
        C=round(n[2][1][0], 9),
        D=round(n[2][1][1], 9),
    )


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _beamline_animation_percent_complete(run_dir, res, data):
    def _output_append(frame_count, filename, count, element, res):
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
            total_count += 1
            _output_append(
                _frames(e, data),
                _file(e, count),
                count,
                e,
                res,
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
            state.res += f'(Drift_srw({round(dz, 9)}), ["default"]),\n'
        if element.type == "watch" or element.get("isDisabled"):
            return
        if element.type == "lens":
            state.res += f'(Lens_srw({element.focalLength}), ["default"]),\n'
        elif element.type == "mirror2":
            state.res += "(Mirror(), []),\n"
        elif element.type == "crystal":
            if element.origin == "reuse":
                return
            state.res += _generate_crystal(element)
        elif element.type == "telescope":
            state.res += f"(Telescope_lct({element.focal_length_1}, {element.focal_length_2}, {element.drift_length_1}, {element.drift_length_2}, {element.drift_length_3}, l_scale=numpy.sqrt(2) * pulse.sigx_waist), []),\n"
        elif element.type == "splitter":
            state.res += f"(Beamsplitter({element.transmitted_fraction}), []),\n"
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
                nslice={crystal.nslice},
                A={crystal.A},
                B={crystal.B},
                C={crystal.C},
                D={crystal.D},
                pop_inversion_n_cells={crystal.inversion_n_cells},
                pop_inversion_mesh_extent={crystal.inversion_mesh_extent},
                pop_inversion_crystal_alpha={crystal.crystal_alpha},
                pop_inversion_pump_waist={crystal.pump_waist},
                pop_inversion_pump_wavelength={crystal.pump_wavelength},
                pop_inversion_pump_gaussian_order={crystal.pump_gaussian_order},
                pop_inversion_pump_energy={crystal.pump_energy},
                pop_inversion_pump_type="{crystal.pump_type}",
                pop_inversion_pump_rep_rate={crystal.pump_rep_rate},
                pop_inversion_pump_offset_x={crystal.pump_offset_x},
                pop_inversion_pump_offset_y={crystal.pump_offset_y},
            ),
        ),
        ["{crystal.propagationType}", True, False],
        {crystal.mesh_density},
        "{crystal.pump_pulse_profile}",
    ),\n"""


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    if data.report == "crystalAnimation":
        v.crystalLength = _get_crystal(data).length
        v.crystalCSV = _CRYSTAL_CSV_FILE
        return res + template_common.render_jinja(SIM_TYPE, v, "crystal.py")
    if data.report in _SIM_DATA.SOURCE_REPORTS:
        data.models.beamline = []
    v.laserPulse = _convert_laser_pulse_units(data.models.laserPulse)
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


class _LaserPulsePlot(PKDict):
    _SCALAR_PLOTS = (
        "longitudinal_intensity",
        "longitudinal_frequency",
        "longitudinal_wavelength",
    )

    _PLOT_LABELS = PKDict(
        longitudinal_intensity="Intensity",
        total_intensity="Total Intensity",
        total_phase="Total Phase",
        longitudinal_frequency="Frequency [Rad/s]",
        longitudinal_wavelength="Wavelength [nm]",
        longitudinal_photons="Total Number of Photons",
        excited_states_longitudinal="Excited States",
        excited_states="Excited States Slice #{slice_index}",
        phase="Phase Slice #{slice_index}",
        intensity="Intensity Slice #{slice_index}",
        photons="Photons Slice #{slice_index}",
    )

    _X_LABELS = PKDict(
        excited_states_longitudinal="Crystal Slice",
        longitudinal_photons="Crystal width [cm]",
        longitudinal_intensity="Pulse Slice",
        longitudinal_frequency="Pulse Slice",
        longitudinal_wavelength="Pulse Slice",
    )

    _Z_LABELS = PKDict(
        total_phase="Phase [rad]",
        total_intensity="",
        intensity="",
        phase="Phase [rad]",
        photons="Photons [1/m³]",
        excited_states="Number [1/m³]",
    )

    def _cell_volume(self):
        if self._is_crystal():
            return (
                (
                    (2 * self.element.inversion_mesh_extent)
                    / self.element.inversion_n_cells
                )
                ** 2
                * self.element.length
                / self.element.nslice
            )
        return None

    def _fname(self):
        if self._is_crystal():
            return _CRYSTAL_FILE
        return _RESULTS_FILE

    def _index(self, index):
        if self.plot_type == "longitudinal_photons":
            return index
        return index + 1

    def _is_crystal(self):
        return self.element and self.element.type == "crystal"

    def _is_longitudinal_plot(self):
        return "longitudinal" in self.plot_type

    def _plot_label(self):
        return self._PLOT_LABELS[self.plot_type].format(
            slice_index=self.slice_index + 1
        )

    def _nslice(self, file):
        if self._is_crystal():
            return self.element.nslice
        return len(file)

    def _x_label(self):
        return self._X_LABELS[self.plot_type]

    def _y_value(self, index, file):
        if self._is_crystal():
            return numpy.sum(
                numpy.array(file[f"{index}/excited_states"]) * self._cell_volume()
            )
        y = numpy.array(file[f"{index}/{self.plot_type}"])
        if self.plot_type in self._SCALAR_PLOTS:
            return y
        return numpy.sum(y)

    def _z_label(self):
        return self._Z_LABELS[self.plot_type]

    def _gen_longitudinal(self, element_file):
        x = []
        y = []
        nslice = self._nslice(element_file)
        if self.element:
            self.element.nslice = nslice
        for idx in range(nslice):
            x.append(self._index(idx))
            y.append(self._y_value(idx, element_file))
        return template_common.parameter_plot(
            x,
            [
                PKDict(
                    points=y,
                    label=self._plot_label(),
                ),
            ],
            PKDict(),
            PKDict(
                x_label=self._x_label(),
            ),
        )

    def gen(self):
        for _ in range(_MAX_H5_READ_TRIES):
            try:
                with h5py.File(
                    self.run_dir.join(self._fname().format(self.element_index)), "r"
                ) as f:
                    if self._is_longitudinal_plot():
                        return self._gen_longitudinal(f)
                    d = template_common.h5_to_dict(f, str(self.slice_index))
                    r = d.ranges
                    z = d[self.plot_type]
                    return PKDict(
                        title=self._plot_label(),
                        x_range=[r.x[0], r.x[1], len(z)],
                        y_range=[r.y[0], r.y[1], len(z[0])],
                        x_label="Horizontal Position [m]",
                        y_label="Vertical Position [m]",
                        z_label=self._z_label(),
                        z_matrix=z,
                    )
            except BlockingIOError as e:
                time.sleep(3)
        raise AssertionError("Report is unavailable")


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


def _convert_laser_pulse_units(laserPulse):
    laserPulse.tau_0 = laserPulse.tau_0 / 1e12
    laserPulse.tau_fwhm = laserPulse.tau_fwhm / 1e12
    laserPulse.num_sig_long = laserPulse.num_sig_long / 2
    laserPulse.num_sig_trans = laserPulse.num_sig_trans / 2
    return laserPulse


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
