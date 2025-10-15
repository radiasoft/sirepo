# -*- coding: utf-8 -*-
"""Impact-T execution template.
:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pmd_beamphysics.labels import mathlabel
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
import pykern.pkio
import pykern.pkjson
import re
import sirepo.mpi
import sirepo.sim_data
import sirepo.template.lattice


_CACHED_STAT_COLUMNS = "stat-columns.json"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_MAX_OUTPUT_ID = 100
_NONE = "None"
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
_HEADER_M = set(["sigx", "xmu1", "sigy", "ymu1", "sigz", "zmu1"])


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
                        reports=[_stat_report_info(run_dir)],
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
        if name == "delta_energy":
            return "E -〈E〉"
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
            z_units="pC",
        ),
        # scale to pC
        weights=particle_group.weight * 1e12,
    )


def code_var(variables):
    return code_variable.CodeVar(variables, code_variable.PurePythonEval())


def get_data_file(run_dir, model, frame, options):
    if frame < 0:
        return template_common.text_data_file(template_common.RUN_LOG, run_dir)
    raise AssertionError(f"unknown model={model}")


def output_info(data):
    def _default_columns(info):
        if info.name == "final_particles":
            info.x = "delta_z"
            info.y = "delta_energy"
        else:
            info.x = "x"
            info.y = "y"
        return info

    res = []
    for idx, n in enumerate(_output_names(data)):
        res.append(
            _default_columns(
                PKDict(
                    modelKey=f"elementAnimation{idx}",
                    reportIndex=idx,
                    report="elementAnimation",
                    name=n,
                    frameCount=1,
                    isHistogram=True,
                    columns=[
                        # Could get this from lume-impact metadata
                        "x",
                        "px",
                        "y",
                        "py",
                        "z",
                        "pz",
                        "energy",
                        "delta_energy",
                        "delta_z",
                    ],
                )
            )
        )
    return res


def post_execution_processing(success_exit, run_dir, **kwargs):

    def _parse_log(default_msg=None):
        p = template_common.LogParser(
            run_dir,
            error_patterns=(
                r"\s+Error: (.*)",
                r"(Note: .*)",
                r"=\s+(BAD TERMINATION.*)",
                r"Fortran runtime error: (.*)",
            ),
        )
        if default_msg is not None:
            p.default_msg = default_msg
        return p.parse_for_errors()

    # Impact-T may fail but return a success, so it can't be trusted
    if success_exit:
        return _parse_log(default_msg="")
    return _parse_log()


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


def sim_frame_statAnimation(frame_args):
    return stat_animation(_patch_stat_parser(frame_args.run_dir), frame_args)


def stat_animation(I, frame_args):
    stats = I.output["stats"]
    plots = PKDict()
    if frame_args.x == _NONE:
        frame_args.x = "mean_z"
    for f in ("x", "y1", "y2", "y3", "y4", "y5"):
        if frame_args[f] == _NONE:
            continue
        units = I.units(frame_args[f])
        if units and str(units) and str(units) != "1":
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


def write_parameters(data, run_dir, is_parallel):
    pykern.pkio.write_text(
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


def _generate_distgen_xyfile(data, v):
    d = data.models.distribution
    if d.Flagdist != "distgen_xyfile":
        return
    v.distgenXYFile = _SIM_DATA.get_distgen_file(data, True)
    v.distgenYAML = template_common.render_jinja(
        SIM_TYPE,
        v,
        "distgen_xyfile.yaml",
    )
    d.Flagdist = "16"
    d.filename = ""
    # these must be non-zero or Impact-T will crash, even though they are not used for file distributions
    d.sigx = d.sigy = d.sigz = 1


def _generate_header(data):
    dm = data.models
    res = PKDict()
    for m in ("beam", "distribution", "simulationSettings"):
        s = SCHEMA.model[m]
        for k in dm[m]:
            n = f"{k}(m)" if k in _HEADER_M else k
            if s[k][1] == "RPNValue":
                res[n] = float(dm[m][k])
            else:
                res[n] = dm[m][k]
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
    v.distributionFilename = (
        _SIM_DATA.get_distribution_file(data, True)
        if data.models.distribution.Flagdist == "16"
        else None
    )
    _generate_distgen_xyfile(data, v)
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
    for r in output_info(data):
        fn = f"{r.name}.h5"
        if run_dir.join(fn).exists():
            r.filename = fn
            res.append(r)
    return res


def _output_names(data):
    return _watches_in_beamline_order(
        data,
        data.models.simulation.visualizationBeamlineId,
        ["initial_particles", "final_particles"],
    )


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


def _patch_stat_parser(run_dir):
    # TODO(pjm): monkey patch to avoid shape errors when loading during updates
    impact.parsers.load_many_fort = _patched_load_many_fort
    I = impact.Impact(
        use_temp_dir=False,
        workdir=str(run_dir),
    )
    I.load_input(I._workdir + "/ImpactT.in")
    I.load_output()
    return I


def _plot_label(field):
    l = mathlabel(field)
    if field == "norm_emit_z":
        return r"$\epsilon_{n, z}$"
    if re.search(r"mathrm|None", l):
        return field
    return l


def stat_columns(impact_model):
    return [_NONE, "Bz", "Ez"] + sorted(impact_model.output["stats"].keys())


def _stat_report_info(run_dir):
    n = run_dir.join(_CACHED_STAT_COLUMNS)
    if n.exists():
        c = pykern.pkjson.load_any(n)
    else:
        c = stat_columns(_patch_stat_parser(run_dir))
        pykern.pkjson.dump_pretty(c, filename=n)
    return PKDict(
        columns=c,
        name="Beam Variables",
        modelKey="statAnimation",
        report="statAnimation",
        x="mean_z",
        y1="norm_emit_x",
        y2="norm_emit_y",
        y3="sigma_x",
        y4="sigma_y",
        y5="sigma_z",
    )


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
