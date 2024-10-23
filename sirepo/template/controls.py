# -*- coding: utf-8 -*-
"""Controls execution template.

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from sirepo.sim_data.controls import AmpConverter
from sirepo.template import template_common
from sirepo.template import madx_parser
from sirepo.template.lattice import LatticeUtil
import copy
import csv
import re
import sirepo.sim_data
import sirepo.simulation_db
import sirepo.template.madx

_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_SUMMARY_CSV_FILE = "summary.csv"
_PTC_TRACK_COLUMNS_FILE = "ptc_track_columns.txt"
_PTC_TRACK_FILE = "track.tfs"


def background_percent_complete(report, run_dir, is_running):
    if is_running:
        e, mt = read_summary_line(run_dir)
        return PKDict(
            percentComplete=100,
            frameCount=mt if mt else 0,
            elementValues=e,
            ptcTrackColumns=_get_ptc_track_columns(run_dir),
            twissColumns=sirepo.template.madx.PTC_OBSERVE_TWISS_COLS,
        )
    e, mt = read_summary_line(
        run_dir,
        SCHEMA.constants.maxBPMPoints,
    )
    return PKDict(
        percentComplete=100,
        frameCount=mt if mt else 0,
        elementValues=e,
        ptcTrackColumns=_get_ptc_track_columns(run_dir),
        twissColumns=sirepo.template.madx.PTC_OBSERVE_TWISS_COLS,
    )


def extract_beam_position_report(data, run_dir):
    def _y_range(points):
        ymin = 1e24
        ymax = -1e24
        for i in range(len(points.s)):
            for dim in ("x", "y"):
                # convert values to float
                if points[dim][i] is not None:
                    points[dim][i] = float(points[dim][i])
                if dim == "y" and points.y[i] is not None:
                    if points.y[i] < ymin:
                        ymin = points.y[i]
                    elif points.y[i] > ymax:
                        ymax = points.y[i]
        return [ymin, ymax]

    points = PKDict(
        s=[],
        x=[],
        y=[],
        log_x=[],
        log_y=[],
    )
    p = 0
    elmap = _get_element_positions(data, run_dir)
    for el in _SIM_DATA.beamline_elements(data.models.externalLattice.models):
        if "l" in el:
            p += el.l
        if el._id in elmap:
            points.s.append(p)
            points.x.append(elmap[el._id].get("x", None))
            points.y.append(elmap[el._id].get("y", None))
            points.log_x.append(elmap[el._id].get("log_x", None))
            points.log_y.append(elmap[el._id].get("log_y", None))
    res = PKDict(
        y_label="",
        x_label="s [m]",
        dynamicYLabel=True,
        x_points=points.s,
        x_range=[points.s[0], points.s[-1]],
        plots=[
            PKDict(
                field="x",
                points=points.x,
                label="x [m]",
                color="#1f77b4",
                circleRadius=10,
            ),
            PKDict(
                field="y",
                points=points.y,
                label="y [m]",
                color="#ff7f0e",
                circleRadius=10,
            ),
        ],
        y_range=_y_range(points),
    )
    if is_viewing_log_file(data):
        res.plots[0].label = "sim x [m]"
        res.plots[1].label = "sim y [m]"
        res.plots.insert(
            0,
            PKDict(
                field="log_y",
                points=points.log_y,
                label="y [m]",
                color="#d62728",
                circleRadius=10,
            ),
        )
        res.plots.insert(
            0,
            PKDict(
                field="log_x",
                points=points.log_x,
                label="x [m]",
                color="#2ca02c",
                circleRadius=10,
            ),
        )
    return res


def is_viewing_log_file(data):
    return (
        data.models.controlSettings.operationMode == "madx"
        and data.models.controlSettings.inputLogFile
    )


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def read_summary_line(run_dir, line_count=None):
    path = run_dir.join(_SUMMARY_CSV_FILE)
    if not path.exists():
        return None, None
    header = None
    rows = []
    with open(str(path)) as f:
        reader = csv.reader(f)
        for row in reader:
            if header == None:
                header = row
                if not line_count:
                    break
            else:
                rows.append(row)
                if len(rows) > line_count:
                    rows.pop(0)
    res = None
    if line_count:
        res = []
        for row in rows:
            if len(header) == len(row):
                res.append(PKDict(zip(header, row)))
    else:
        line = template_common.read_last_csv_line(path)
        if header and line:
            line = line.split(",")
            if len(header) == len(line):
                res = [PKDict(zip(header, line))]
    return res, int(path.mtime() * 1000)


def sim_frame(frame_args):
    return _extract_report_elementAnimation(
        frame_args, frame_args.run_dir, _PTC_TRACK_FILE
    )


def stateful_compute_get_madx_sim_list(data, **kwargs):
    res = []
    for f in pkio.sorted_glob(
        _SIM_DATA.controls_madx_dir().join(
            "*",
            sirepo.simulation_db.SIMULATION_DATA_FILE,
        ),
    ):
        m = sirepo.simulation_db.read_json(f).models
        res.append(
            PKDict(
                name=m.simulation.name,
                simulationId=m.simulation.simulationId,
                invalidMsg=(
                    None
                    if _has_kickers(m)
                    else "No beamlines" if not _has_beamline(m) else "No kickers"
                ),
            )
        )
    return PKDict(simList=res)


def stateful_compute_get_external_lattice(data, **kwargs):
    madx = sirepo.simulation_db.read_json(
        _SIM_DATA.controls_madx_dir().join(
            data.args.simulationId,
            sirepo.simulation_db.SIMULATION_DATA_FILE,
        ),
    )
    _delete_unused_madx_models(madx)
    sirepo.template.madx.eval_code_var(madx)
    beam = _delete_unused_madx_commands(madx)
    _uniquify_elements(madx)
    _add_monitor(madx)
    madx.models.simulation.computeTwissFromParticles = "1"
    _SIM_DATA.update_beam_gamma(beam)
    madx.models.bunch.beamDefinition = "gamma"
    _SIM_DATA.init_currents(beam, madx.models)
    _SIM_DATA.add_ptc_track_commands(madx)
    return _SIM_DATA.init_process_variables(
        PKDict(
            externalLattice=madx,
            optimizerSettings=_SIM_DATA.default_optimizer_settings(madx.models),
            command_beam=beam,
            bunch=madx.models.bunch,
        )
    )


def stateful_compute_get_log_file_time_list(data, **kwargs):
    import h5py

    with h5py.File(_log_file_path(data.lib_file), "r") as f:
        return PKDict(
            timeValues=list(f["monitor/ubh1L"]),
        )


def stateful_compute_get_log_file_values_at_index(data, **kwargs):
    return PKDict(values=_log_file_values(data.models, data.index, data.lib_file))


def stateless_compute_current_to_kick(data, **kwargs):
    return PKDict(
        kick=AmpConverter(
            data.args.command_beam, data.args.amp_table, data.args.default_factor
        ).current_to_kick(data.args.current),
    )


def stateless_compute_kick_to_current(data, **kwargs):
    return PKDict(
        current=AmpConverter(
            data.args.command_beam, data.args.amp_table, data.args.default_factor
        ).kick_to_current(data.args.kick),
    )


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _add_monitor(data):
    for i, e in enumerate(data.models.elements):
        if e.type == "MARKER":
            data.models.elements[i] = PKDict(
                _id=e._id,
                name=e.name,
                type="MONITOR",
            )
    if not list(filter(lambda el: el.type == "MONITOR", data.models.elements)):
        m = PKDict(
            _id=LatticeUtil.max_id(data) + 1,
            name="M1",
            type="MONITOR",
        )
        data.models.elements.append(m)
        assert (
            len(data.models.beamlines) == 1
        ), f"expecting 1 beamline={data.models.beamlines}"
        data.models.beamlines[0]["items"].append(m._id)


def _delete_unused_madx_commands(data):
    # remove all commands except first beam
    beam = None
    for c in data.models.commands:
        if c._type == "beam":
            beam = c
            _SIM_DATA.update_model_defaults(c, "command_beam")
            break
    data.models.commands = [
        PKDict(
            _type="option",
            _id=LatticeUtil.max_id(data) + 1,
            echo="0",
        ),
        beam,
    ]
    return beam


def _delete_unused_madx_models(data):
    for m in list(data.models.keys()):
        if m not in [
            "beamlines",
            "commands",
            "elements",
            "report",
            "rpnVariables",
            "simulation",
            "bunch",
        ]:
            data.models.pkdel(m)


def _extract_report_elementAnimation(frame_args, run_dir, filename):
    data = frame_args.sim_in
    if frame_args.frameReport == "instrumentAnimationTwiss":
        data.report = frame_args.frameReport
        data.models[data.report] = frame_args
        return sirepo.template.madx.extract_report_twissFromParticlesAnimation(
            data, run_dir, _PTC_TRACK_FILE
        )
    if frame_args.frameReport == "beamPositionAnimation":
        return extract_beam_position_report(data, run_dir)
    a = madx_parser.parse_tfs_page_info(run_dir.join(filename))
    if frame_args.x == "x" and frame_args.y1 == "y":
        frame_args.plotRangeType = "fixed"
        frame_args.verticalSize = frame_args.particlePlotSize
        frame_args.verticalOffset = 0
        frame_args.horizontalSize = frame_args.particlePlotSize
        frame_args.horizontalOffset = 0
    i, x = _get_target_info(a, frame_args)
    t = madx_parser.parse_tfs_file(run_dir.join(filename), want_page=x)
    data.models[frame_args.frameReport] = frame_args
    return template_common.heatmap(
        [
            sirepo.template.madx.to_floats(t[frame_args.x]),
            sirepo.template.madx.to_floats(t[frame_args.y1]),
        ],
        frame_args,
        PKDict(
            x_label=sirepo.template.madx.field_label(frame_args.x),
            y_label=sirepo.template.madx.field_label(frame_args.y1),
            title="{}-{} at {:.3f}m, {}".format(
                frame_args.x,
                frame_args.y1,
                float(i.s),
                i.name,
            ),
            global_min=0,
            global_max=2,
        ),
    )


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    _generate_parameters(v, data)
    if data.models.controlSettings.operationMode == "DeviceServer":
        _validate_process_variables(v, data)
    v.optimizerTargets = data.models.optimizerSettings.targets
    v.summaryCSV = _SUMMARY_CSV_FILE
    v.ptcTrackColumns = _PTC_TRACK_COLUMNS_FILE
    v.ptcTrackFile = _PTC_TRACK_FILE
    if data.get("report") == "initialMonitorPositionsReport":
        if data.models.initialMonitorPositionsReport.readOnly == "1":
            v.controlSettings_readOnly = "1"
        v.optimizerSettings_method = "runOnce"
    elif data.models.controlSettings.operationMode == "DeviceServer":
        if v.controlSettings_readOnly == "1":
            v.optimizerSettings_method = "monitor"
    return (
        res
        + template_common.render_jinja(SIM_TYPE, v, "base.py")
        + template_common.render_jinja(
            SIM_TYPE,
            v,
            "{}.py".format(
                (
                    "device-server"
                    if v.controlSettings_operationMode == "DeviceServer"
                    else "madx"
                ),
            ),
        )
    )


def _generate_parameters(v, data):
    def _format_header(el_id, field):
        return f"el_{el_id}.{field}"

    v.ampTableNames = []
    v.ampTables = data.models.get("ampTables", PKDict())

    def _set_opt(el, field, all_correctors):
        all_correctors.header.append(
            _format_header(el._id, _SIM_DATA.current_field(field))
        )
        if data.models.controlSettings.operationMode == "DeviceServer":
            if not _is_enabled(data, el):
                return
        count = len(all_correctors.corrector)
        all_correctors.corrector.append(el[_SIM_DATA.current_field(field)])
        el[field] = "{" + f"sr_opt{count}" + "}"
        v.ampTableNames.append(el.ampTable if "ampTable" in el else None)

    c = PKDict(
        header=[],
        corrector=[],
    )
    madx = data.models.externalLattice.models
    header = []
    monitors = PKDict()
    for el in _SIM_DATA.beamline_elements(madx):
        if data.models.controlSettings.operationMode != "DeviceServer":
            if not _is_enabled(data, el):
                continue
        if el.type == "KICKER":
            _set_opt(el, "hkick", c)
            _set_opt(el, "vkick", c)
        elif el.type in ("HKICKER", "VKICKER"):
            _set_opt(el, "kick", c)
        elif el.type == "QUADRUPOLE":
            _set_opt(el, "k1", c)
        elif el.type == "MONITOR":
            header += [_format_header(el._id, x) for x in ("x", "y")]
            monitors[el.name] = el.type
        elif el.type == "HMONITOR":
            header += [_format_header(el._id, "x")]
            monitors[el.name] = el.type
        elif el.type == "VMONITOR":
            header += [_format_header(el._id, "y")]
            monitors[el.name] = el.type
    v.monitorNames = ",\n".join([f'    "{k}": "{v}"' for k, v in monitors.items()])
    v.summaryCSVHeader = ",".join(c.header + header + ["cost"])
    v.initialCorrectors = "[{}]".format(",".join([str(x) for x in c.corrector]))
    v.correctorCount = len(c.corrector)
    v.monitorCount = len(header)
    v.mc2 = SCHEMA.constants.particleMassAndCharge.proton[0]
    if data.models.controlSettings.operationMode == "madx":
        data.models.externalLattice.models.simulation.computeTwissFromParticles = "1"
        v.madxSource = sirepo.template.madx.generate_parameters_file(
            data.models.externalLattice
        )


def _get_element_positions(data, run_dir):
    summary = read_summary_line(run_dir)[0][0]
    log_summary = None
    if is_viewing_log_file(data):
        log_summary = _log_file_values(
            data.models.externalLattice.models,
            data.models.controlSettings.selectedTimeIndex,
            data.models.controlSettings.inputLogFile,
        )
    elmap = PKDict()
    for k in summary:
        m = re.search(r"el_(\d+)\.(x|y)", k)
        if not m:
            continue
        el_id = int(m.group(1))
        dim = m.group(2)
        if el_id not in elmap:
            elmap[el_id] = PKDict()
        elmap[el_id][dim] = summary[k]
        if log_summary and k in log_summary:
            elmap[el_id][f"log_{dim}"] = log_summary[k]
    return elmap


def _get_ptc_track_columns(run_dir):
    if run_dir.join(_PTC_TRACK_COLUMNS_FILE).exists():
        return pkio.read_text(_PTC_TRACK_COLUMNS_FILE).split(",")
    return []


def _get_target_info(info_all, frame_args):
    data = frame_args.sim_in
    i = data.models[frame_args.frameReport].id
    name = None
    for el in frame_args.sim_in.models.externalLattice.models.elements:
        if el._id == i:
            name = el.name
    if not name:
        raise AssertionError(f"Missing instrument for id: {i}")
    page = -1
    for rec in info_all:
        page += 1
        if rec.name == name:
            return rec, page
    raise AssertionError(f"Missing instrument for name: {name}")


def _has_beamline(model):
    return model.elements and model.beamlines


def _has_kickers(model):
    if not _has_beamline(model):
        return False
    k_ids = [e._id for e in model.elements if "KICKER" in e.type]
    if not k_ids:
        return False
    for b in model.beamlines:
        if any([item in k_ids for item in b["items"]]):
            return True
    return False


def _is_enabled(data, el):
    if "KICKER" in el.type:
        return data.models.optimizerSettings.inputs.kickers[str(el._id)]
    if el.type == "QUADRUPOLE":
        return data.models.optimizerSettings.inputs.quads[str(el._id)]
    return True


def _log_file_path(lib_file):
    return _SIM_DATA.lib_file_abspath(
        _SIM_DATA.lib_file_name_with_model_field(
            "controlSettings", "inputLogFile", lib_file
        )
    )


def _log_file_values(models, index, lib_file):
    import h5py

    def log_field_to_element():
        res = PKDict()
        for el in _SIM_DATA.beamline_elements(models):
            n = el.name.lower()
            if "current_kick" in el:
                res[n] = f"el_{el._id}.current_kick"
            elif "current_k1" in el:
                res[n] = f"el_{el._id}.current_k1"
            else:
                if "x" in el:
                    n2 = n if "h" in n else re.sub(r"(\d)", r"h\1", n)
                    res[n2] = f"el_{el._id}.x"
                if "y" in el:
                    n2 = n if "v" in n else re.sub(r"(\d)", r"v\1", n)
                    res[n2] = f"el_{el._id}.y"
        return res

    with h5py.File(_log_file_path(lib_file), "r") as f:
        values = PKDict()
        for section in ("monitor", "power"):
            idx = index if section == "monitor" else index * 2
            for k in f[section]:
                values[k] = f[section][k][idx]

        f_to_e = log_field_to_element()
        res = PKDict()
        for f in values:
            if f in f_to_e:
                res[f_to_e[f]] = values[f] * (1e-6 if "b" in f else 1)
        return res


def _uniquify_elements(data):
    def _do_unique(elem_ids):
        element_map = PKDict({e._id: e for e in data.models.elements})
        names = set([e.name for e in data.models.elements])
        max_id = LatticeUtil.max_id(data)
        res = []
        for el_id in elem_ids:
            if el_id not in res:
                res.append(el_id)
                continue
            el = copy.deepcopy(element_map[el_id])
            el.name = _unique_name(el.name, names)
            max_id += 1
            el._id = max_id
            data.models.elements.append(el)
            res.append(el._id)
        return res

    def _remove_unused_elements(items):
        res = []
        for el in data.models.elements:
            if el._id in items:
                res.append(el)
        data.models.elements = res

    def _unique_name(name, names):
        assert name in names
        count = 2
        m = re.search(r"(\d+)$", name)
        if m:
            count = int(m.group(1))
            name = re.sub(r"\d+$", "", name)
        while f"{name}{count}" in names:
            count += 1
        names.add(f"{name}{count}")
        return f"{name}{count}"

    util = LatticeUtil(data, sirepo.sim_data.get_class("madx").schema())
    b = util.get_item(data.models.simulation.visualizationBeamlineId)
    b["items"] = util.explode_beamline(b.id)
    _remove_unused_elements(b["items"])
    b["items"] = _do_unique(b["items"])
    data.models.beamlines = [b]


def _validate_process_variables(v, data):
    settings = data.models.controlSettings
    if not settings.deviceServerURL:
        raise AssertionError("Missing DeviceServer URL value")
    elmap = PKDict({e._id: e for e in data.models.externalLattice.models.elements})
    properties = PKDict(
        read=[],
    )
    if v.controlSettings_readOnly == "0":
        properties.write = []
    for pv in settings.processVariables:
        el = elmap[pv.elId]
        name = el.name
        if not pv.pvName:
            raise AssertionError(
                f"Missing Process Variable Name for beamline element {name}"
            )
        values = re.split(r":", pv.pvName)
        if len(values) != 2:
            raise AssertionError(
                f"Beamline element {name} Process Variable must contain one : separator"
            )
        idx = None
        if pv.isWritable == "0":
            m = re.search(r"\[(\d+)\]", values[1])
            if m:
                idx = int(m.group(1))
                values[1] = re.sub(r"\[.*$", "", values[1])
        if pv.isWritable == "1" and not _is_enabled(data, el):
            continue
        k = "write" if pv.isWritable == "1" else "read"
        if k in properties:
            properties[k].append(
                PKDict(
                    device=values[0],
                    name=values[1],
                    index=idx,
                    type=el.type,
                )
            )
    v.properties = properties
    v.property_types = properties.keys()
    config = PKDict()
    for k in ("user", "procName", "procId", "machine"):
        f = "deviceServer" + k[0].upper() + k[1:]
        if not settings[f]:
            raise AssertionError(f"Missing DeviceServer field: {k}")
        config[k] = settings[f]
    v.deviceServerSetContext = "&".join([f"{k}={config[k]}" for k in config])
