# -*- coding: utf-8 -*-
"""Impact-T execution template.
:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pmd_beamphysics.labels import mathlabel
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo.template import code_variable
from sirepo.template import template_common
import impact
import impact.fieldmaps
import impact.parsers
import numpy
import pmd_beamphysics
import re
import sirepo.mpi
import sirepo.sim_data
import sirepo.template.lattice
import time


_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
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
                if "mean_z" in d and len(d["mean_z"]) > 10:
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


def bunch_plot(model, frame_index, particle_group):
    def _label(name):
        if name == "delta_z":
            return "z -〈z〉"
        if name == "energy":
            return "E"
        return name

    return template_common.heatmap(
        values=[particle_group[model.x], particle_group[model.y]],
        model=model,
        plot_fields=PKDict(
            x_label=f"{_label(model.x)} [{particle_group.units(model.x)}]",
            y_label=f"{_label(model.y)} [{particle_group.units(model.y)}]",
            title=_PLOT_TITLE.get(f"{model.x}-{model.y}", f"{model.x} - {model.y}"),
            threshold=[1e-20, 1e20],
        ),
        # weights=particle_group.weight,
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
        frame_args.frameIndex,
        pmd_beamphysics.ParticleGroup(
            str(frame_args.run_dir.join(_file_name_for_element_animation(frame_args)))
        ),
    )


def stat_animation(I, frame_args):
    stats = I.output["stats"]
    plots = PKDict()
    if frame_args.x == "none":
        frame_args.x = "mean_z"
    for f in ("x", "y1", "y2", "y3", "y4", "y5"):
        if frame_args[f] == "none":
            continue
        units = I.units(frame_args[f])
        if units and str(units) != "1":
            units = f" [{units}]"
        else:
            units = ""
        if frame_args[f] in ("Bz", "Ez"):
            zlist = I.stat("mean_z")
            tlist = I.stat("t")
            eles = [
                ele
                for ele in I.lattice
                if ele["type"] in impact.fieldmaps.FIELD_CALC_ELE_TYPES
            ]
            p = numpy.array(
                [
                    impact.fieldmaps.lattice_field(
                        eles,
                        z=z,
                        x=0,
                        y=0,
                        t=t,
                        component=frame_args[f],
                        fmaps=I.fieldmaps,
                    )
                    for z, t in zip(zlist, tlist)
                ]
            )

        else:
            p = stats[frame_args[f]]
        plots[f] = PKDict(
            label=f"{_plot_label(frame_args[f])}{units}",
            dim=f,
            points=p.tolist(),
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


def sim_frame_statAnimation(frame_args):
    # TODO(pjm): monkey patch to avoid shape errors when loading during updates
    impact.parsers.load_many_fort = _patched_load_many_fort
    I = impact.Impact(
        use_temp_dir=False,
        workdir=str(frame_args.run_dir),
    )
    I.load_input(I._workdir + "/ImpactT.in")
    I.load_output()
    return stat_animation(I, frame_args)


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


def _format_field(code_var, name, field, field_type, value):
    if field == "_super":
        return ""
    if field == "l":
        field = "L"
    if field_type == "InputFile":
        if name == "WAKEFIELD":
            # TODO(pjm): handle wakefield filename
            return ""
        value = f'prep_input_file("{_SIM_DATA.lib_file_name_with_model_field(name, field, value)}")'
    elif field_type == "RPNValue":
        # TODO(pjm): eval RPNValue
        value = float(value)
    elif field_type == "Integer":
        pass
    else:
        value = f'"{value}"'
    return f"{field}={value},\n"


def _generate_header(data):
    dm = data.models
    res = PKDict()
    for m in ("beam", "distribution", "simulationSettings"):
        s = SCHEMA.model[m]
        for k in dm[m]:
            if s[k][1] == "RPNValue":
                res[k] = float(dm[m][k])
            else:
                res[k] = dm[m][k]
    if dm.beam.particle in ("electron", "proton"):
        res["Bmass"], res["Bcharge"] = SCHEMA.constants.particleMassAndCharge[
            dm.beam.particle
        ]
    else:
        if dm.beam.particle != "other":
            raise AssertionError(f"Invalid particle type: {dm.beam.particle}")
    del res["particle"]
    del res["filename"]
    return res


def _generate_lattice(util, beamline_id, result):
    beamline = util.id_map[abs(beamline_id)]
    cv = code_var(util.data.models.rpnVariables)
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
                el += _format_field(cv, item.type, f, d[1], item[f])
            result.append(el)
        else:
            _generate_lattice(util, item.id, result)
    return result


def _generate_parameters_file(data):
    res, v = template_common.generate_parameters_file(data)
    util = sirepo.template.lattice.LatticeUtil(data, SCHEMA)
    v.lattice = _generate_lattice(util, util.select_beamline().id, [])
    v.numProcs = sirepo.mpi.cfg().cores
    v.distributionFilename = _SIM_DATA.get_distribution_file(data)
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


def output_info(data):
    res = []
    for idx, n in enumerate(_output_names(data)):
        res.append(
            PKDict(
                modelKey=f"elementAnimation{idx}",
                reportIndex=idx,
                report="elementAnimation",
                name=n,
                frameCount=1,
            )
        )
    return res


def _output_info(data, run_dir):
    res = []
    for r in output_info(data):
        fn = f"{r.name}.h5"
        if run_dir.join(fn).exists():
            r.filename = fn
            res.append(r)
    return res


# This method is copied, modified and monkey patched from the impact.parsers module.
# The method can be called while files are still being written, so the size is adjusted
# if later files have a longer length.
#
def _patched_load_many_fort(path, types=impact.parsers.FORT_STAT_TYPES, verbose=False):
    """
    Loads a large dict with data from many fort files.
    Checks that keys do not conflict.

    Default types are for typical statistical information along the simulation path.

    """
    fortfiles = impact.parsers.fort_files(path)
    alldat = {}
    size = None
    for f in fortfiles:
        file_type = impact.parsers.fort_type(f, verbose=False)
        if file_type not in types:
            continue

        dat = impact.parsers.load_fort(f, type=file_type, verbose=verbose)
        for k in dat:
            if isinstance(dat[k], dict):
                alldat[k] = dat[k]
                continue
            if size is None:
                size = len(dat[k])
            elif len(dat[k]) > size:
                dat[k] = dat[k][:size]
            if k not in alldat:
                alldat[k] = dat[k]

            elif numpy.allclose(alldat[k], dat[k], atol=1e-20):
                # If the difference between alldat-dat < 1e-20,
                # move on to next key without error.
                # https://numpy.org/devdocs/reference/generated/numpy.isclose.html#numpy.isclose
                pass

            else:
                # Data is not close enough to ignore differences.
                # Check that this data is the same as what's already in there
                assert numpy.all(alldat[k] == dat[k]), "Conflicting data for key:" + k

    return alldat


def _plot_label(field):
    l = mathlabel(field)
    if re.search(r"mathrm|None", l):
        return field
    return l


def _watches_in_beamline_order(data, beamline_id, result):
    util = sirepo.template.lattice.LatticeUtil(data, SCHEMA)
    beamline = util.id_map[abs(beamline_id)]
    for item_id in beamline["items"]:
        item = util.id_map[abs(item_id)]
        if "type" in item:
            if item.type == "WRITE_BEAM":
                if item.name not in result:
                    result.append(item.name)
        else:
            _watches_in_beamline_order(data, item_id, result)
    return result


def _output_names(data):
    return _watches_in_beamline_order(
        data,
        data.models.simulation.visualizationBeamlineId,
        ["initial_particles", "final_particles"],
    )
