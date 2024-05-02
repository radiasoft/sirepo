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
import numpy
import re
import sirepo.feature_config
import sirepo.mpi
import sirepo.sim_data
import sirepo.sim_run
import subprocess

_CACHE_DIR = "cloudmc-cache"
_OUTLINES_FILE = "outlines.json"
_PREP_SBATCH_PREFIX = "prep-sbatch"
_VOLUME_INFO_FILE = "volumes.json"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()


def _percent_complete(run_dir, is_running):
    RE_F = "\d*\.\d+"

    def _get_groups(match, *args):
        res = []
        for i in args:
            g = match.group(i)
            if g is not None:
                res.append(g.strip())
        return res

    res = PKDict(
        frameCount=0,
        percentComplete=0,
    )
    log = run_dir.join(template_common.RUN_LOG)
    if not log.exists():
        return res
    with pkio.open_text(log) as f:
        res.eigenvalue = None
        res.results = None
        has_results = False
        for line in f:
            m = re.match(r"^ Simulating batch (\d+)", line)
            if m:
                res.frameCount = int(m.group(1))
                continue
            m = re.match(
                rf"^\s+(\d+)/1\s+({RE_F})\s*({RE_F})?\s*(\+/-)?\s*({RE_F})?", line
            )
            if m:
                res.frameCount = int(m.group(1))
                res.eigenvalue = res.eigenvalue or []
                res.eigenvalue.append(
                    PKDict(
                        batch=res.frameCount,
                        val=_get_groups(m, 2, 3, 5),
                    )
                )
                continue
            if not has_results:
                has_results = re.match(r"\s*=+>\s+RESULTS\s+<=+\s*", line)
                if not has_results:
                    continue
            m = re.match(rf"^\s+(.+)\s=\s({RE_F})\s+\+/-\s+({RE_F})", line)
            if m:
                res.results = res.results or []
                res.results.append(_get_groups(m, 1, 2, 3))

    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    if is_running:
        res.percentComplete = res.frameCount * 100 / data.models.settings.batches
    if res.frameCount:
        res.tallies = data.models.settings.tallies
    return res


def stateful_compute_check_animation_dir(data, **kwargs):
    return PKDict(
        animationDirExists=simulation_db.simulation_dir(
            "cloudmc", sid=data.simulationId
        )
        .join(data.args.modelName)
        .exists()
    )


def background_percent_complete(report, run_dir, is_running):
    if report == "dagmcAnimation":
        if is_running:
            return PKDict(
                percentComplete=0,
                frameCount=0,
            )
        if not run_dir.join(_VOLUME_INFO_FILE).exists():
            raise AssertionError("Volume extraction failed")
        return PKDict(
            percentComplete=100,
            frameCount=1,
            volumes=simulation_db.read_json(_VOLUME_INFO_FILE),
        )
    return _percent_complete(run_dir, is_running)


def extract_report_data(run_dir, sim_in):
    # dummy result
    if sim_in.report == "tallyReport":
        template_common.write_sequential_result(PKDict(x_range=[]))


def get_data_file(run_dir, model, frame, options):
    sim_in = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    if model == "geometry3DReport":
        return _SIM_DATA.dagmc_filename(sim_in)
    if model == "dagmcAnimation":
        return f"{frame}.zip"
    if model == "openmcAnimation":
        if options.suffix == "log":
            return template_common.text_data_file(template_common.RUN_LOG, run_dir)
        return _statepoint_filename(
            simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        )
    raise AssertionError(f"invalid model={model} options={options}")


def post_execution_processing(
    compute_model, sim_id, success_exit, is_parallel, run_dir, **kwargs
):
    if success_exit:
        if compute_model == "dagmcAnimation":
            ply_files = pkio.sorted_glob(run_dir.join("*.ply"))
            for f in ply_files:
                _SIM_DATA.put_sim_file(sim_id, f, f.basename)
        return None
    return _parse_cloudmc_log(run_dir)


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data)


def stateful_compute_download_remote_lib_file(data, **kwargs):
    _SIM_DATA.lib_file_save_from_url(
        "{}/{}".format(
            sirepo.feature_config.for_sim_type(SIM_TYPE).data_storage_url,
            data.args.exampleURL,
        ),
        "geometryInput",
        "dagmcFile",
    )
    return PKDict()


def sim_frame(frame_args):
    import openmc

    if frame_args.frameReport == "energyAnimation":
        frame_args.sim_in.models.energyAnimation = (
            template_common.model_from_frame_args(frame_args)
        )
        return _energy_plot(frame_args.run_dir, frame_args.sim_in)

    def _sample_sources(filename, num_samples):
        samples = []
        try:
            b = template_common.read_dict_from_h5(filename).get("source_bank", [])[
                :num_samples
            ]
            return [
                PKDict(
                    direction=p.u,
                    energy=p.E,
                    position=p.r,
                    type=openmc.ParticleType(p.particle).name,
                )
                for p in [openmc.SourceParticle(*p) for p in b]
            ]
        except:
            pass
        return samples

    def _sum_energy_bins(values, mesh_filter, energy_filter, sum_range):
        bins = numpy.ceil(
            (energy_filter.num - 1)
            * numpy.abs(numpy.array(sum_range) - energy_filter.start)
            / numpy.abs(energy_filter.stop - energy_filter.start)
        ).astype(int)
        vv = numpy.reshape(values, (*mesh_filter.dimension, -1))
        z = numpy.zeros((*mesh_filter.dimension, 1))
        for i in range(len(vv)):
            for j in range(len(vv[i])):
                for k in range(len(vv[i][j])):
                    z[i][j][k][0] = numpy.sum(vv[i][j][k][bins[0] : bins[1]])
        return z.ravel()

    t = openmc.StatePoint(
        frame_args.run_dir.join(_statepoint_filename(frame_args.sim_in))
    ).get_tally(name=frame_args.tally)
    try:
        # openmc doesn't have a has_filter() api
        t.find_filter(openmc.MeshFilter)
    except ValueError:
        return PKDict(error=f"Tally {t.name} contains no Mesh")

    v = getattr(t, frame_args.aspect)[:, :, t.get_score_index(frame_args.score)].ravel()

    if t.contains_filter(openmc.EnergyFilter):
        tally = _get_tally(frame_args.sim_in.models.settings.tallies, frame_args.tally)
        v = _sum_energy_bins(
            v,
            _get_filter(tally, "meshFilter"),
            _get_filter(tally, "energyFilter"),
            frame_args.energyRangeSum,
        )

    # volume normalize copied from openmc.UnstructuredMesh.write_data_to_vtk()
    v /= t.find_filter(openmc.MeshFilter).mesh.volumes.ravel()
    o = simulation_db.read_json(frame_args.run_dir.join(_OUTLINES_FILE))
    return PKDict(
        field_data=v.tolist(),
        min_field=v.min(),
        max_field=v.max(),
        num_particles=frame_args.sim_in.models.settings.particles,
        summaryData=PKDict(
            tally=frame_args.tally,
            outlines=o[frame_args.tally] if frame_args.tally in o else {},
            sourceParticles=_sample_sources(
                _source_filename(frame_args.sim_in),
                frame_args.numSampleSourceParticles,
            ),
        ),
    )


def stateless_compute_validate_material_name(data, **kwargs):
    import openmc

    res = PKDict()
    m = openmc.Material(name="test")
    method = getattr(m, data.args.component)
    try:
        if data.args.component == "add_macroscopic":
            method(data.args.name)
        elif data.args.component == "add_nuclide":
            method(data.args.name, 1)
            if not re.search(r"^[^\d]+\d+$", data.args.name):
                raise ValueError("invalid nuclide name")
        elif data.args.component == "add_s_alpha_beta":
            method(data.args.name)
        elif data.args.component == "add_elements_from_formula":
            method(data.args.name)
        elif data.args.component == "add_element":
            method(data.args.name, 1)
        else:
            raise AssertionError(f"unknown material component: {data.args.component}")
    except ValueError as e:
        res.error = "invalid material name"
    return res


def validate_file(file_type, path):
    import h5py

    if file_type == "geometryInput-dagmcFile":
        if not h5py.is_hdf5(path):
            return "dagmcFile must be valid hdf5 file"
    return None


def write_parameters(data, run_dir, is_parallel):
    if _is_sbatch_run_mode(data):
        pkio.write_text(
            run_dir.join(f"{_PREP_SBATCH_PREFIX}.py"),
            _generate_parameters_file(data, run_dir=run_dir),
        )
        with pkio.open_text(run_dir.join(f"{_PREP_SBATCH_PREFIX}.log"), mode="w") as l:
            subprocess.run(
                ["python", f"{_PREP_SBATCH_PREFIX}.py"],
                check=True,
                stderr=l,
                stdout=l,
            )
        pkio.write_text(
            run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
            template_common.render_jinja(
                SIM_TYPE,
                PKDict(
                    cacheDir=sirepo.sim_run.cache_dir(_CACHE_DIR),
                    numThreads=data.models.openmcAnimation.ompThreads,
                ),
                "openmc-sbatch.py",
            ),
        )
    else:
        pkio.write_text(
            run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
            _generate_parameters_file(data, run_dir=run_dir),
        )
    if is_parallel:
        return template_common.get_exec_parameters_cmd()


def write_volume_outlines():
    import trimesh
    import dagmc_geometry_slice_plotter

    _MIN_RES = SCHEMA.constants.minTallyResolution

    def _center_range(mesh, dim):
        f = (
            0.5
            * abs(mesh.upper_right[dim] - mesh.lower_left[dim])
            / mesh.dimension[dim]
        )
        return numpy.linspace(
            mesh.lower_left[dim] + f,
            mesh.upper_right[dim] - f,
            mesh.dimension[dim],
        )

    def _get_meshes():
        tallies = simulation_db.read_json(
            template_common.INPUT_BASE_NAME
        ).models.settings.tallies
        for t in tallies:
            for f in [x for x in t if x.startswith("filter")]:
                if t[f]._type == "meshFilter":
                    yield t.name, t[f]

    def _is_skip_dimension(tally_range, dim1, dim2):
        return len(tally_ranges[dim1]) < _MIN_RES or len(tally_ranges[dim2]) < _MIN_RES

    all_outlines = PKDict()
    for tally_name, tally_mesh in _get_meshes():
        tally_ranges = [_center_range(tally_mesh, i) for i in range(3)]
        # don't include outlines of low resolution dimensions
        skip_dimensions = PKDict(
            x=_is_skip_dimension(tally_ranges, 1, 2),
            y=_is_skip_dimension(tally_ranges, 0, 2),
            z=_is_skip_dimension(tally_ranges, 0, 1),
        )
        outlines = PKDict()
        all_outlines[tally_name] = outlines
        basis_vects = numpy.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        rots = [
            numpy.array([[1, 0], [0, 1]]),
            numpy.array([[0, -1], [1, 0]]),
            numpy.array([[0, 1], [-1, 0]]),
        ]
        for mf in pkio.sorted_glob("*.ply"):
            vol_id = mf.purebasename
            vol_mesh = None
            outlines[vol_id] = PKDict(x=[], y=[], z=[])
            with open(mf, "rb") as f:
                vol_mesh = trimesh.Trimesh(**trimesh.exchange.ply.load_ply(f))
            for i, dim in enumerate(outlines[vol_id].keys()):
                if skip_dimensions[dim]:
                    outlines[vol_id][dim] = []
                    continue
                n = basis_vects[i]
                r = rots[i]
                for pos in tally_ranges[i]:
                    coords = []
                    try:
                        coords = dagmc_geometry_slice_plotter.get_slice_coordinates(
                            dagmc_file_or_trimesh_object=vol_mesh,
                            plane_origin=pos * n,
                            plane_normal=n,
                        )
                        # get_slice_coordinates returns a list of "TrackedArrays",
                        # arranged for use in matplotlib
                        ct = []
                        for c in [
                            (SCHEMA.constants.geometryScale * x.T) for x in coords
                        ]:
                            ct.append([numpy.dot(r, x).tolist() for x in c])
                        coords = ct
                    except ValueError:
                        # no intersection at this plane position
                        pass
                    outlines[vol_id][dim].append(coords)
    simulation_db.write_json(_OUTLINES_FILE, all_outlines)


def _dagmc_animation_python(filename):
    return f"""
import sirepo.pkcli.cloudmc
import sirepo.simulation_db

sirepo.simulation_db.write_json(
    "{_VOLUME_INFO_FILE}",
    sirepo.pkcli.cloudmc.extract_dagmc("{filename}"),
)
"""


def _energy_plot(run_dir, data):
    import openmc

    def _bin(val, mesh, idx):
        # mesh units are in cm
        return numpy.floor(
            mesh.dimension[idx]
            * abs(val * 1e2 - mesh.lower_left[idx])
            / abs(mesh.upper_right[idx] - mesh.lower_left[idx])
        ).astype(int)

    plots = []
    tally_name = data.models.energyAnimation.tally
    t = openmc.StatePoint(run_dir.join(_statepoint_filename(data))).get_tally(
        name=tally_name
    )
    try:
        e_f = t.find_filter(openmc.EnergyFilter)
    except ValueError:
        return PKDict(error=f"No energy filter defined for tally {tally_name}")

    tally = _get_tally(data.models.settings.tallies, tally_name)
    mesh = _get_filter(tally, "meshFilter")
    e = _get_filter(tally, "energyFilter")
    r = data.models.energyAnimation
    mean = numpy.reshape(
        getattr(t, "mean")[:, :, t.get_score_index(r.score)].ravel(),
        (*mesh.dimension, -1),
    )
    # std_dev = getattr(t, "std_dev")[:, :, t.get_score_index(r.score)].ravel()

    x = e_f.values.tolist()
    y = mean[_bin(r.x, mesh, 0)][_bin(r.y, mesh, 1)][_bin(r.z, mesh, 2)].tolist()
    x1 = []
    y1 = []
    for i in range(len(y)):
        if i > 0 and y[i - 1] == y[i]:
            pass
        else:
            x1.append(x[i])
            y1.append(y[i])
        x1.append(x[i + 1])
        y1.append(y[i])
    return template_common.parameter_plot(
        x1,
        [
            PKDict(
                points=y1,
                label=r.score,
            ),
        ],
        PKDict(),
        PKDict(
            title=f"Energy Spectrum at ({round(r.x, ndigits=4)}, {round(r.y, ndigits=4)}, {round(r.z, ndigits=4)})",
            x_label="Energy [eV]",
        ),
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
    import sirepo.csv

    if dist._type == "None":
        return dist._type
    t = dist._type
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
    if "file" in dist:
        for v in numpy.array(
            sirepo.csv.read_as_number_list(
                _SIM_DATA.lib_file_abspath(
                    _SIM_DATA.lib_file_name_with_model_field(
                        dist._type, "file", dist.file
                    )
                )
            )
        ).T.tolist():
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
    elif dist._type in ("tabular", "tabularFromFile"):
        if dist._type == "tabularFromFile":
            t = "tabular"
        args += [
            f'"{dist.interpolation}"',
            "True" if dist.ignore_negative == "1" else "False",
        ]
    elif dist._type == "uniform" or dist._type == "watt":
        args += [str(v) for v in [dist.a, dist.b]]
    else:
        raise AssertionError("unknown distribution type: {}".format(dist._type))
    return _generate_call(t, args)


def _generate_materials(data, j2_ctx):
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
        j2_ctx.incomplete_data_msg += " No materials defined for volumes,"
        return
    res += "materials = openmc.Materials([" + ", ".join(material_vars) + "])\n"
    return res


def _generate_mesh(mesh):
    return f"""
m = openmc.RegularMesh()
m.dimension = {_generate_array([int(v) for v in mesh.dimension])}
m.lower_left = {_generate_array(mesh.lower_left)}
m.upper_right = {_generate_array(mesh.upper_right)}
"""


def _generate_parameters_file(data, run_dir=None):
    report = data.get("report", "")
    if report == "dagmcAnimation":
        return _dagmc_animation_python(_SIM_DATA.dagmc_filename(data))
    if report == "tallyReport":
        return ""
    res, v = template_common.generate_parameters_file(data)
    v.dagmcFilename = _SIM_DATA.dagmc_filename(data)
    v.isPythonSource = False if run_dir else True
    if v.isPythonSource:
        v.materialDirectory = "."
        v.isSBATCH = False
    else:
        v.materialDirectory = sirepo.sim_run.cache_dir(_CACHE_DIR)
        v.isSBATCH = _is_sbatch_run_mode(data)
    v.weightWindowsMesh = _generate_mesh(data.models.weightWindowsMesh)
    v.runCommand = _generate_run_mode(data, v)
    v.incomplete_data_msg = ""
    v.materials = _generate_materials(data, v)
    v.sources = _generate_sources(data, v)
    v.sourceFile = _source_filename(data)
    v.maxSampleSourceParticles = SCHEMA.model.openmcAnimation.numSampleSourceParticles[
        5
    ]
    v.tallies = _generate_tallies(data, v)
    v.hasGraveyard = _has_graveyard(data)
    if v.incomplete_data_msg:
        return (
            f'raise AssertionError("Unable to generate sim: {v.incomplete_data_msg}")'
        )
    return template_common.render_jinja(
        SIM_TYPE,
        v,
    )


def _generate_energy_range(filter):
    space = "linspace"
    start = filter.start * 1e6
    stop = filter.stop * 1e6
    if filter.space == "log" and filter.start > 0:
        space = "logspace"
        start = numpy.log10(start)
        stop = numpy.log10(stop)
    return "numpy.{}({}, {}, {})".format(space, start, stop, filter.num)


def _generate_run_mode(data, v):
    r = data.models.openmcAnimation.jobRunMode
    cores = 1 if r == "sequential" else sirepo.mpi.cfg().cores
    if v.isPythonSource:
        cores = 0
    if data.models.settings.varianceReduction == "weight_windows_tally":
        if v.isSBATCH:
            raise AssertionError("Weight Windows are not yet available with sbatch")
        v.settings_particles = v.weightWindows_particles
        if cores:
            # the only way to set threading for run_in_memory() is with an environment variable
            v.weightWindowsThreadLimit = f'os.environ["OMP_NUM_THREADS"] = "{cores}"'
        return _weight_windows_run_command(data)
    if v.isSBATCH:
        return ""
    if v.isPythonSource:
        return "openmc.run()"
    return f"openmc.run(threads={cores})"


def _generate_source(source):
    if source.get("type") == "file" and source.get("file"):
        return f"openmc.IndependentSource(filename=\"{_SIM_DATA.lib_file_name_with_model_field('source', 'file', source.file)}\")"
    return f"""openmc.IndependentSource(
        space={_generate_space(source.space)},
        angle={_generate_angle(source.angle)},
        energy={_generate_distribution(source.energy)},
        time={_generate_distribution(source.time)},
        strength={source.strength},
        particle="{source.particle}",
    )"""


def _generate_sources(data, j2_ctx):
    if not len(data.models.settings.sources):
        j2_ctx.incomplete_data_msg += " No Settings Sources defined,"
        return
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


def _generate_tallies(data, j2_ctx):
    if not len(data.models.settings.tallies):
        j2_ctx.incomplete_data_msg += " No Tallies defined"
        return
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
        res += _generate_mesh(f)
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
    openmc.EnergyFilter({_generate_energy_range(f)}),
"""
        elif f._type == "energyoutFilter":
            res += f"""
    openmc.EnergyoutFilter({_generate_energy_range(f)}),
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


def _get_filter(tally, type):
    for i in range(1, SCHEMA.constants.maxFilters + 1):
        f = tally[f"filter{i}"]
        if f._type == type:
            return f
    return None


def _get_tally(tallies, name):
    f = [x for x in tallies if x.name == name]
    return f[0] if len(f) else None


def _has_graveyard(data):
    for v in data.models.volumes.values():
        if v.name and v.name.lower() == "graveyard":
            return True
    return False


def _is_sbatch_run_mode(data):
    return data.models.openmcAnimation.jobRunMode == "sbatch"


def _parse_cloudmc_log(run_dir, log_filename="run.log"):
    return template_common.LogParser(
        run_dir,
        log_filename=log_filename,
        default_msg="An unknown error occurred, check CloudMC log for details",
        # ERROR: Cannot tally flux for an individual nuclide.
        error_patterns=(
            re.compile(r"^\s*Error:\s*(.*)$", re.IGNORECASE),
            re.compile(r"AssertionError: (.*)"),
        ),
    ).parse_for_errors()


def _source_filename(data):
    return f"source.{data.models.settings.batches}.h5"


def _statepoint_filename(data):
    return f"statepoint.{data.models.settings.batches}.h5"


def _weight_windows_run_command(data):
    ww = data.models.weightWindows
    idx = 0
    for idx, t in enumerate(data.models.settings.tallies):
        if ww.tally == t.name:
            break
    return f"""
with openmc.lib.run_in_memory():
    tally = openmc.lib.tallies[{idx + 1}]
    wws = openmc.lib.WeightWindows.from_tally(tally, particle="{ww.particle}")

    for i in range({ww.iterations}):
        openmc.lib.reset()
        openmc.lib.run()
        wws.update_magic(tally)
        openmc.lib.settings.weight_windows_on = True
"""
