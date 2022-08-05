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
    if is_running:
        data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        res.percentComplete = res.frameCount * 100 / data.models.settings.batches
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
        return PKDict(filename=run_dir.join(f"{sim_in.models.tally.name}.json"))


def python_source_for_model(data, model):
    return _generate_parameters_file(data)


def stateless_compute_read_tallies(data):
    pass


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
        args += [_generate_angleribution(angle[v] for v in ["mu", "phi"])]
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
        res += f'{n} = openmc.Material(name="{v.key}")\n'
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
    v.tallyName = data.models.tally.name
    v.tallyScore = data.models.tally.score
    v.tallyAspects = data.models.tally.aspects
    v.tallyMeshLowerLeft = _generate_array(data.models.tally.meshLowerLeft)
    v.tallyMeshUpperRight = _generate_array(data.models.tally.meshUpperRight)
    v.tallyMeshCellCount = _generate_array(
        [int(v) for v in data.models.tally.meshCellCount]
    )
    return template_common.render_jinja(
        SIM_TYPE,
        v,
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
