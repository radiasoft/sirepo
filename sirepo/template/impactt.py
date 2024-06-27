# -*- coding: utf-8 -*-
"""Impact-T execution template.
:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import template_common
import impact
import impact.parsers
import pmd_beamphysics
import sirepo.mpi
import sirepo.sim_data
import sirepo.template.lattice
import time


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_ARCHIVE_FILE = "impact.h5"
_MAX_OUTPUT_ID = 100
_PLOT_TITLE = PKDict(
    {
        "x-px": "Horizontal",
        "y-py": "Vertical",
        "x-y": "Cross-section",
        "z-pz": "Longitudinal",
    },
)
_S_ELEMENTS = set(
    [
        "CHANGE_TIMESTEP",
        "OFFSET_BEAM",
        "ROTATIONALLY_SYMMETRIC_TO_3D",
        "SPACECHARGE",
        "STOP",
        "WAKEFIELD",
        "WRITE_BEAM",
        "WRITE_SLICE_INFO",
    ]
)
_STAT_RETRIES = 5
_TIME_AND_ENERGY_FILE_NO = 18


def code_var(variables):
    return code_variable.CodeVar(variables, code_variable.PurePythonEval())


def background_percent_complete(report, run_dir, is_running):
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    if is_running:
        stop_z = _find_last_stop(data, data.models.simulation.visualizationBeamlineId)
        if stop_z and stop_z >= 0:
            try:
                d = impact.parsers.load_many_fort(
                    str(run_dir), types=[_TIME_AND_ENERGY_FILE_NO]
                )
                if "mean_z" in d and len(d["mean_z"] > 1):
                    return PKDict(
                        frameCount=len(d["mean_z"]),
                        percentComplete=d["mean_z"][-1] * 100.0 / stop_z,
                    )
            except IndexError:
                pass
        return PKDict(
            frameCount=0,
            percentComplete=0,
        )
    r = _output_info(data, run_dir)
    return PKDict(
        percentComplete=100,
        frameCount=1 if len(r) else 0,
        reports=r,
    )


def bunch_plot(model, run_dir, frame_index, filename):
    p = pmd_beamphysics.ParticleGroup(str(run_dir.join(filename)))
    return template_common.heatmap(
        values=[p[model.x], p[model.y]],
        model=model,
        plot_fields=PKDict(
            x_label=f"{model.x} [{p.units(model.x)}]",
            y_label=f"{model.y} [{p.units(model.y)}]",
            title=_PLOT_TITLE.get(f"{model.x}-{model.y}", f"{model.x} - {model.y}"),
        ),
    )


def prepare_for_client(data, qcall, **kwargs):
    code_var(data.models.rpnVariables).compute_cache(data, SCHEMA)
    return data


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def sim_frame(frame_args):
    # elementAnimations
    return bunch_plot(
        frame_args,
        frame_args.run_dir,
        frame_args.frameIndex,
        _file_name_for_element_animation(frame_args),
    )


def sim_frame_statAnimation(frame_args):
    I = impact.Impact(
        use_temp_dir=False,
        workdir=str(frame_args.run_dir),
    )
    for _ in range(_STAT_RETRIES):
        try:
            I.load_output()
        except ValueError as err:
            time.sleep(1)
    if "stats" not in I.output:
        I.load_output()
    stats = I.output["stats"]
    plots = PKDict()
    if frame_args.x == "none":
        frame_args.x = "mean_z"
    for f in ("x", "y1", "y2", "y3"):
        if frame_args[f] == "none":
            continue
        units = I.units(frame_args[f])
        if units and str(units) != "1":
            units = f" [{units}]"
        else:
            units = ""
        plots[f] = PKDict(
            label=f"{frame_args[f]}{units}",
            dim=f,
            points=stats[frame_args[f]].tolist(),
        )
    return template_common.parameter_plot(
        x=plots.x.points,
        plots=[p for p in plots.values() if p.dim != "x"],
        model=frame_args,
        plot_fields=PKDict(
            dynamicYLabel=True,
            title="",
            y_label="",
            x_label=plots.x.label,
        ),
    )


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )
    if is_parallel:
        return template_common.get_exec_parameters_cmd(False)
    return None


def _file_name_for_element_animation(frame_args):
    r = frame_args.frameReport
    for info in _output_info(frame_args.sim_in, frame_args.run_dir):
        if info.modelKey == r:
            return info.filename
    raise AssertionError(f"no output for frameReport={r}")


def _find_last_stop(data, beamline_id):
    util = sirepo.template.lattice.LatticeUtil(data, SCHEMA)
    beamline = util.id_map[abs(beamline_id)]
    for idx, item_id in reversed(list(enumerate(beamline["items"]))):
        item = util.id_map[abs(item_id)]
        if "type" in item:
            if item.type == "STOP":
                # TODO(pjm): eval var
                return beamline.positions[idx].elemedge
        else:
            res = _find_last_stop(data, item_id)
            if res:
                return res
    return 0


def _format_field(name, field, field_type, value):
    if field == "_super":
        return ""
    if field == "l":
        field = "L"
    if field_type == "InputFile":
        if name == "WAKEFIELD":
            # TODO(pjm): handle wakefield filename
            return ""
        value = f'prep_input_file("{_SIM_DATA.lib_file_name_with_model_field(name, field, value)}")'
    else:
        value = f'"{value}"'
    return f"{field}={value},\n"


def _generate_header(data):
    dm = data.models
    res = PKDict()
    for m in ("beam", "distribution", "simulationSettings"):
        for k in dm[m]:
            res[k] = dm[m][k]
    if dm.beam.particle == "electron":
        pass
    elif dm.beam.particle == "proton":
        pass
    else:
        if dm.beam.particle != "other":
            raise AssertionError(f"Invalid particle type: {dm.beam.particle}")
    del res["particle"]
    return res


def _generate_lattice(util, beamline_id, result):
    beamline = util.id_map[abs(beamline_id)]
    output_ids = set(
        impact.parsers.FORT_STAT_TYPES
        + impact.parsers.FORT_DIPOLE_STAT_TYPES
        + impact.parsers.FORT_PARTICLE_TYPES
        + impact.parsers.FORT_STAT_TYPES
    )

    for idx, item_id in enumerate(beamline["items"]):
        item = util.id_map[abs(item_id)]
        if "type" in item:
            el = f'type="{item.type.lower()}",\n'
            if item.type == "WAKEFIELD":
                z = beamline.positions[idx].elemedge
                el += f"s_begin={z},\n"
                el += f"s={z + item.l},\n"
            elif item.type in _S_ELEMENTS:
                el += f"s={beamline.positions[idx].elemedge},\n"
            else:
                el += f"zedge={beamline.positions[idx].elemedge},\n"
            for f, d in SCHEMA.model[item.type].items():
                if d[1] == "OutputFile":
                    item[f] = f"fort.{_next_output_id(output_ids)}"
                el += _format_field(item.type, f, d[1], item[f])
            result.append(el)
        else:
            _generate_lattice(util, item.id, result)
    return result


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    util = sirepo.template.lattice.LatticeUtil(data, SCHEMA)
    v.lattice = _generate_lattice(util, util.select_beamline().id, [])
    v.archiveFile = _ARCHIVE_FILE
    v.numProcs = sirepo.mpi.cfg().cores
    v.impactHeader = _generate_header(data)
    return res + template_common.render_jinja(
        SIM_TYPE,
        v,
        template_common.PARAMETERS_PYTHON_FILE,
    )


def _next_output_id(output_ids):
    i = 1
    while i in output_ids:
        i += 1
        if i > _MAX_OUTPUT_ID:
            raise AssertionError("Max output files exceeded")
    output_ids.add(i)
    return i


def _output_info(data, run_dir):
    res = []
    for idx, n in enumerate(_output_names(data)):
        fn = f"{n}.h5"
        if run_dir.join(fn).exists():
            res.append(
                PKDict(
                    modelKey=f"elementAnimation{idx}",
                    reportIndex=idx,
                    report="elementAnimation",
                    name=n,
                    filename=fn,
                    frameCount=1,
                )
            )
    return res


def _output_names(data):
    res = ["initial_particles", "final_particles"]
    for el in data.models.elements:
        if el.type == "WRITE_BEAM":
            res.append(el.name)
    return res
