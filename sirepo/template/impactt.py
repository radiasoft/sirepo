# -*- coding: utf-8 -*-
"""Impact-T execution template.
:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
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
import sirepo.mpi
import sirepo.sim_data
import sirepo.template.lattice
import time


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_ARCHIVE_FILE = "impact.h5"
_MAX_OUTPUT_ID = 100
_S_ELEMENTS = set(
    [
        "OFFSET_BEAM",
        "WRITE_BEAM",
        "CHANGE_TIMESTEP",
        "ROTATIONALLY_SYMMETRIC_TO_3D",
        "WAKEFIELD",
        "STOP",
        "SPACECHARGE",
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
    return PKDict(
        percentComplete=100, frameCount=1, reports=_particle_plot_info(data, run_dir)
    )


def _particle_plot_info(data, run_dir):
    names = ["initial_particles", "final_particles"]
    for el in data.models.elements:
        if el.type == "WRITE_BEAM":
            names.append(el.name)
    res = []
    for n in names:
        fn = f"{n}.h5"
        if run_dir.join(fn).exists():
            res.append(
                PKDict(
                    report="particleAnimation",
                    filename=fn,
                )
            )
    return res


def prepare_for_client(data, qcall, **kwargs):
    code_var(data.models.rpnVariables).compute_cache(data, SCHEMA)
    return data


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


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
