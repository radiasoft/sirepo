# -*- coding: utf-8 -*-
"""CloudMC execution template.

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
from sirepo import simulation_db
from sirepo import util
from sirepo.template import template_common
import re
import sirepo.sim_data


VOLUME_INFO_FILE = "volumes.json"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def _percent_complete(run_dir, is_running):
    res = PKDict(
        frameCount=0,
        percentComplete=0,
    )
    with pkio.open_text(str(run_dir.join(template_common.RUN_LOG))) as f:
        for line in f:
            m = re.match(r"^ Simulating batch (\d+)", line)
            if m:
                res.frameCount = int(m.group(1))
                continue
            m = re.match(r"^\s+(\d+)/1\s+\d", line)
            if m:
                res.frameCount = int(m.group(1))
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    if is_running:
        res.percentComplete = res.frameCount * 100 / data.models.settings.batches
    if res.frameCount:
        res.tallies = data.models.settings.tallies
    return res


def background_percent_complete(report, run_dir, is_running):
    if report == "dagmcAnimation":
        if is_running:
            return PKDict(
                percentComplete=0,
                frameCount=0,
            )
        if not run_dir.join(VOLUME_INFO_FILE).exists():
            raise AssertionError("Volume extraction failed")
        return PKDict(
            percentComplete=100,
            frameCount=1,
            volumes=simulation_db.read_json(VOLUME_INFO_FILE),
        )
    return _percent_complete(run_dir, is_running)


def get_data_file(run_dir, model, frame, options):
    sim_in = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    if model == "dagmcAnimation":
        return PKDict(filename=run_dir.join(f"{frame}.zip"))
    if model == "openmcAnimation":
        if options.suffix == "log":
            return template_common.text_data_file(template_common.RUN_LOG, run_dir)
        return _statepoint_filename(
            simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        )
    raise AssertionError("no data file for model={model} and options={options}")


def post_execution_processing(
    success_exit=True, is_parallel=True, run_dir=None, **kwargs
):
    if success_exit:
        return None
    return _parse_run_log(run_dir)


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def stateless_compute_read_tallies(data):
    pass


def sim_frame(frame_args):
    import openmc

    t = openmc.StatePoint(
        frame_args.run_dir.join(_statepoint_filename(frame_args.sim_in))
    ).get_tally(name=frame_args.tally)
    f = str(frame_args.run_dir.join(f"{frame_args.tally}.vtk"))
    try:
        # openmc doesn't have a has_filter() api
        t.find_filter(openmc.MeshFilter)
    except ValueError:
        return PKDict(error=f"Tally {t.name} contains no Mesh")
    try:
        t.find_filter(openmc.MeshFilter).mesh.write_data_to_vtk(
            filename=f,
            datasets={
                frame_args.aspect: getattr(t, frame_args.aspect)[
                    :, :, t.get_score_index(frame_args.score)
                ],
            },
        )
    except RuntimeError as e:
        if re.search(r"should be equal to the number of cells", str(e)):
            return PKDict(
                error=f"Tally {frame_args.tally} contains a Mesh and another multi-binned Filter"
            )
        raise
    return PKDict(
        content=_grid_to_poly(f),
    )


def stateless_compute_validate_material_name(data):
    import openmc

    res = PKDict()
    m = openmc.Material(name="test")
    method = getattr(m, data.component)
    try:
        if data.component == "add_macroscopic":
            method(data.name)
        elif data.component == "add_nuclide":
            method(data.name, 1)
            if not re.search(r"^[^\d]+\d+$", data.name):
                raise ValueError("invalid nuclide name")
        elif data.component == "add_s_alpha_beta":
            method(data.name)
        elif data.component == "add_elements_from_formula":
            method(data.name)
        elif data.component == "add_element":
            method(data.name, 1)
        else:
            raise AssertionError(f"unknown material component: {data.component}")
    except ValueError as e:
        res.error = "invalid material name"
    return res


def write_parameters(data, run_dir, is_parallel):
    pkio.write_text(
        run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
        _generate_parameters_file(data),
    )


def _generate_angle(angle):
    if angle._type == "None":
        return angle._type
    args = []
    if angle._type == "isotropic":
        pass
    elif angle._type == "monodirectional":
        args.append(_generate_array(angle.reference_uvw))
    elif angle._type == "polarAzimuthal":
        args += [_generate_distribution(angle[v]) for v in ["mu", "phi"]]
        args.append(_generate_array(angle.reference_uvw))
    else:
        raise AssertionError("unknown angle type: {}".format(angle._type))
    return _generate_call(angle._type, args)


def _generate_array(arr):
    return "[" + ", ".join([str(v) for v in arr]) + "]"


def _generate_call(name, args):
    return "openmc.stats." + name[0].upper() + name[1:] + "(" + ", ".join(args) + ")"


def _generate_distribution(dist):
    if dist._type == "None":
        return dist._type
    args = []
    if "probabilityValue" in dist:
        x = []
        p = []
        for v in dist.probabilityValue:
            if "p" not in v:
                break
            x.append(v.x)
            p.append(v.p)
        for v in (x, p):
            args.append(_generate_array(v))
    if dist._type == "discrete":
        pass
    elif dist._type == "legendre":
        args.append(_generate_array([c.coefficient for c in dist.coefficient]))
    elif dist._type == "maxwell":
        args.append(str(dist.theta))
    elif dist._type == "muir":
        args += [str(v) for v in [dist.e0, dist.m_rat, dist.kt]]
    elif dist._type == "normal":
        args += [str(v) for v in [dist.mean_value, dist.std_dev]]
    elif dist._type == "powerLaw":
        args += [str(v) for v in [dist.a, dist.b, dist.n]]
    elif dist._type == "tabular":
        args += [
            f'"{dist.interpolation}"',
            "True" if dist.ignore_negative == "1" else "False",
        ]
    elif dist._type == "uniform" or dist._type == "watt":
        args += [str(v) for v in [dist.a, dist.b]]
    else:
        raise AssertionError("unknown distribution type: {}".format(dist._type))
    return _generate_call(dist._type, args)


def _generate_materials(data):
    res = ""
    material_vars = []
    for v in data.models.volumes.values():
        if "material" not in v:
            continue
        n = f"m{v.volId}"
        material_vars.append(n)
        res += f"# {v.name}\n"
        res += f'{n} = openmc.Material(name="{v.key}", material_id={v.volId})\n'
        res += f'{n}.set_density("{v.material.density_units}", {v.material.density})\n'
        if v.material.depletable == "1":
            res += f"{n}.depletable = True\n"
        if "temperator" in v and v.material:
            res += f"{n}.temperature = {v.material.temperature}\n"
        if "volume" in v and v.volume:
            res += f"{n}.volume = {v.material.volume}\n"
        for c in v.material.components:
            if (
                c.component == "add_element"
                or c.component == "add_elements_from_formula"
            ):
                if c.component == "add_element":
                    res += (
                        f'{n}.{c.component}("{c.name}", {c.percent}, "{c.percent_type}"'
                    )
                else:
                    res += f'{n}.{c.component}("{c.name}", "{c.percent_type}"'
                if "enrichment" in c and c.enrichment:
                    res += f", enrichment={c.enrichment}"
                if "enrichment_target" in c and c.enrichment_target:
                    res += f', enrichment_target="{c.enrichment_target}"'
                if "enrichment_target" in c and c.enrichment_type:
                    res += f', enrichment_type="{c.enrichment_type}"'
                res += ")\n"
            elif c.component == "add_macroscopic":
                res += f'{n}.{c.component}("{c.name}")\n'
            elif c.component == "add_nuclide":
                res += (
                    f'{n}.{c.component}("{c.name}", {c.percent}, "{c.percent_type}")\n'
                )
            elif c.component == "add_s_alpha_beta":
                res += f'{n}.{c.component}("{c.name}", {c.fraction})\n'
    if not len(material_vars):
        raise AssertionError(f"No materials defined for volumes")
    res += "materials = openmc.Materials([" + ", ".join(material_vars) + "])\n"
    return res


def _generate_parameters_file(data):
    report = data.get("report", "")
    res, v = template_common.generate_parameters_file(data)
    if report == "dagmcAnimation":
        return ""
    v.dagmcFilename = _SIM_DATA.dagmc_filename(data)
    v.materials = _generate_materials(data)
    v.sources = _generate_sources(data)
    v.tallies = _generate_tallies(data)
    return template_common.render_jinja(
        SIM_TYPE,
        v,
    )


def _generate_range(filter):
    return "numpy.{}({}, {}, {})".format(
        "linspace" if filter.space == "linear" else "logspace",
        filter.start,
        filter.stop,
        filter.num,
    )


def _generate_source(source):
    return f"""openmc.Source(
    space={_generate_space(source.space)},
    angle={_generate_angle(source.angle)},
    energy={_generate_distribution(source.energy)},
    time={_generate_distribution(source.time)},
    strength={source.strength},
    particle="{source.particle}",
)"""


def _generate_sources(data):
    if not len(data.models.settings.sources):
        raise AssertionError(f"No Settings Sources defined")
    return ",\n".join([_generate_source(s) for s in data.models.settings.sources])


def _generate_space(space):
    if space._type == "None":
        return space._type
    args = []
    if space._type == "box":
        args += [
            _generate_array(space.lower_left),
            _generate_array(space.upper_right),
            f'only_fissionable={space.only_fissionable == "1"}',
        ]
    elif space._type == "cartesianIndependent":
        args += [_generate_distribution(space[v]) for v in ["x", "y", "z"]]
    elif space._type == "cylindricalIndependent":
        args += [_generate_distribution(space[v]) for v in ["r", "phi", "z"]]
        args.append(f"origin={_generate_array(space.origin)}")
    elif space._type == "point":
        args.append(_generate_array(space.xyz))
    elif space._type == "sphericalIndependent":
        args += [_generate_distribution(space[v]) for v in ["r", "theta", "phi"]]
        args.append(f"origin={_generate_array(space.origin)}")
    else:
        raise AssertionError("unknown space type: {}".format(space._type))
    return _generate_call(space._type, args)


def _generate_tallies(data):
    if not len(data.models.settings.tallies):
        raise AssertionError(f"No Tallies defined")
    return (
        "\n".join(
            [
                _generate_tally(t, data.models.volumes)
                for t in data.models.settings.tallies
            ]
        )
        + f"""
tallies = openmc.Tallies([
    {','.join(['t' + str(tally._index + 1) for tally in data.models.settings.tallies])}
])
tallies.export_to_xml()
"""
    )


def _generate_tally(tally, volumes):
    has_mesh = False
    res = ""
    for i in range(1, SCHEMA.constants.maxFilters + 1):
        f = tally[f"filter{i}"]
        if f._type != "meshFilter":
            continue
        if has_mesh:
            raise AssertionError("Only one mesh may defined per filter")
        has_mesh = True
        res += f"""
m = openmc.RegularMesh()
m.dimension = {_generate_array([int(v) for v in f.dimension])}
m.lower_left = {_generate_array(f.lower_left)}
m.upper_right = {_generate_array(f.upper_right)}
"""
    res += f"""t{tally._index + 1} = openmc.Tally(name='{tally.name}')
t{tally._index + 1}.filters = ["""
    for i in range(1, SCHEMA.constants.maxFilters + 1):
        f = tally[f"filter{i}"]
        if f._type == "None":
            continue
        if f._type == "materialFilter":
            res += f"""
    openmc.MaterialFilter([{",".join([volumes[v.value].volId for v in f.bins])}]),
"""
        elif f._type == "meshFilter":
            res += f"""
    openmc.MeshFilter(m),
"""
        elif f._type == "energyFilter":
            res += f"""
    openmc.EnergyFilter({_generate_range(f)}),
"""
        elif f._type == "energyoutFilter":
            res += f"""
    openmc.EnergyoutFilter({_generate_range(f)}),
"""
        elif f._type == "particleFilter":
            res += f"""
    openmc.ParticleFilter([{'"' + '","'.join(v.value for v in f.bins) + '"'}]),
"""
        else:
            raise AssertionError("filter not yet implemented: {}".format(f._type))
    res += f"""]
t{tally._index + 1}.scores = [{','.join(["'" + s.score + "'" for s in tally.scores])}]
"""
    if len(tally.nuclides):
        res += f"""
t{tally._index + 1}.nuclides = [{','.join(["'" + s.nuclide + "'" for s in tally.nuclides if s.nuclide])}]
"""
    return res


def _grid_to_poly(path):
    def _poly_lines(nx, ny, nz):
        l = []
        for k in range(nz):
            # only rects
            z = k * (nx + 1) * (ny + 1)
            for j in range(ny):
                y = j * (nx + 1)
                d = y + z
                c = [0, 1, nx + 2, nx + 1]
                for i in range(nx):
                    l.append("4 ")
                    for n in range(len(c)):
                        l.append(f"{c[n] + d + i} ")
                    l.append("\n")
        return l

    with pkio.open_text(path) as f:
        state = "header"
        lines = []
        for line in f:
            # force version 4.1
            if line.startswith("# vtk DataFile Version"):
                lines.append("# vtk DataFile Version 4.1\n")
                continue
            # only polydata is allowed
            if line.startswith("DATASET STRUCTURED_GRID"):
                lines.append("DATASET POLYDATA\n")
                continue
            if line.startswith("DIMENSIONS"):
                continue
            if "POINTS" in line:
                state = "points"
                lines.append("POINTS 0 double\nPOLYGONS 0 0\n")
            if "CELL_DATA" in line:
                state = "cells"
            if state != "points":
                lines.append(line)
    return "".join(lines)


def _parse_run_log(run_dir):
    res = ""
    p = run_dir.join(template_common.RUN_LOG)
    if not p.exists():
        return res
    with pkio.open_text(p) as f:
        for line in f:
            # ERROR: Cannot tally flux for an individual nuclide.
            m = re.match(r"^\s*Error:\s*(.*)$", line, re.IGNORECASE)
            if m:
                res = m.group(1)
                break
    if res:
        return res
    return "An unknown error occurred, check CloudMC log for details"


def _statepoint_filename(data):
    return f"statepoint.{data.models.settings.batches}.h5"
