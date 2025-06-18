"""OpenMC execution template.

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcompat
from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
from sirepo import simulation_db
from sirepo.template import template_common
import CAD_to_OpenMC.assembly
import gzip
import h5py
import math
import numpy
import os
import re
import shutil
import sirepo.feature_config
import sirepo.mpi
import sirepo.sim_data
import sirepo.sim_run
import subprocess

STANDARD_MATERIALS_DB = "pnnl-materials.h5"
_STANDARD_MATERIALS_DB_GZ = f"{STANDARD_MATERIALS_DB}.gz"
_OPENMC_CACHE_DIR = "openmc-cache"
_STANDARD_MATERIAL_CACHE_DIR = "openmc-standard-materials"
_OUTLINES_FILE = "outlines.h5"
_PREP_SBATCH_PREFIX = "prep-sbatch"
_VOLUME_INFO_FILE = "volumes.json"
_SIM_DATA, SIM_TYPE, SCHEMA = sirepo.sim_data.template_globals()
_WEIGHT_WINDOWS_FILE = "weight_windows.h5"
_MGXS_FILE = "mgxs.h5"


def background_percent_complete(report, run_dir, is_running):
    if report == "dagmcAnimation":
        if is_running:
            return PKDict(
                percentComplete=0,
                frameCount=0,
            )
        if not run_dir.join(_VOLUME_INFO_FILE).exists():
            return PKDict(percentComplete=100, frameCount=0)
        return PKDict(
            percentComplete=100,
            frameCount=1,
            volumes=simulation_db.read_json(_VOLUME_INFO_FILE),
        )
    return _percent_complete(run_dir, is_running)


def get_data_file(run_dir, model, frame, options):
    sim_in = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    if model == "geometry3DReport":
        return _SIM_DATA.get_geometry_input_filenames(sim_in)[0]
    if model == "dagmcAnimation":
        return f"{frame}.zip"
    if model == "openmcAnimation":
        if options.suffix == "log":
            return template_common.text_data_file(template_common.RUN_LOG, run_dir)
        if options.suffix in ("ww", "mgxs"):
            return template_common.JobCmdFile(
                reply_uri=_format_file_name(
                    sim_in.models.simulation.name, options.suffix
                ),
                reply_path=run_dir.join(
                    _MGXS_FILE if options.suffix == "mgxs" else _WEIGHT_WINDOWS_FILE
                ),
            )
        return _statepoint_filename(
            simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
        )
    raise AssertionError(f"invalid model={model} options={options}")


def post_execution_processing(
    compute_model, sim_id, success_exit, is_parallel, run_dir, **kwargs
):
    if success_exit:
        if compute_model == "dagmcAnimation":
            l = pkio.sorted_glob(run_dir.join("*.ply"))
            d, s = _SIM_DATA.get_geometry_input_filenames(
                simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
            )
            if s:
                l.append(run_dir.join(d))
            for f in l:
                _SIM_DATA.put_sim_file(sim_id, f, f.basename)
        return None
    return _parse_openmc_log(run_dir)


def prepare_for_save(data, qcall):
    # materialsFile is used only once to setup initial volume materials.
    # it isn't reusable across simulations
    if data.models.get("volumes") and data.models.geometryInput.get("materialsFile"):
        if _SIM_DATA.lib_file_exists(_SIM_DATA.materials_filename(data), qcall=qcall):
            pkio.unchecked_remove(
                _SIM_DATA.lib_file_abspath(
                    _SIM_DATA.materials_filename(data), qcall=qcall
                )
            )
        data.models.geometryInput.materialsFile = ""
    return data


def python_source_for_model(data, model, qcall, **kwargs):
    return _generate_parameters_file(data, qcall=qcall)


def sim_frame(frame_args):
    import openmc

    if frame_args.frameReport == "energyAnimation":
        frame_args.sim_in.models.energyAnimation = (
            template_common.model_from_frame_args(frame_args)
        )
        return _energy_plot(
            frame_args.run_dir, frame_args.sim_in, frame_args.frameIndex
        )
    if frame_args.frameReport == "outlineAnimation":
        res = PKDict()
        with h5py.File(_OUTLINES_FILE, "r") as f:
            s = f[frame_args.tally][frame_args.axis][str(frame_args.frameIndex)]
            points = s["points"]
            for volId in s["volumes"]:
                res[volId] = []
                for idx in s["volumes"][volId]:
                    res[volId].append(points[idx[0] : idx[0] + idx[1]].tolist())
        return PKDict(
            outlines=res,
        )

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

    def _tally_index(frame_args):
        for tally in frame_args.sim_in.models.settings.tallies:
            if tally.name == frame_args.tally:
                for i, s in enumerate(tally.scores):
                    if s.score == frame_args.score:
                        return i
        raise AssertionError(
            f"Could not find index for tally={frame_args.tally} score={frame_args.score}"
        )

    # need to cleanup previous files in case sim is canceled
    _cleanup_statepoint_files(
        frame_args.run_dir, frame_args.sim_in, frame_args.frameIndex + 1, 0
    )
    t = openmc.StatePoint(
        frame_args.run_dir.join(
            _statepoint_filename(frame_args.sim_in, frame_args.frameIndex)
        )
    ).get_tally(name=frame_args.tally)
    try:
        # openmc doesn't have a has_filter() api
        t.find_filter(openmc.MeshFilter)
    except ValueError:
        return PKDict(error=f"Tally {t.name} contains no Mesh")
    v = getattr(t, frame_args.aspect)[:, :, _tally_index(frame_args)].ravel()
    if t.contains_filter(openmc.EnergyFilter):
        tally = _get_tally(frame_args.sim_in.models.settings.tallies, frame_args.tally)
        v = _sum_energy_bins(
            v,
            _get_filter(tally, "meshFilter"),
            _get_filter(tally, "energyFilter"),
            frame_args.energyRangeSum,
        )

    # pjm: removed this to match results from openmc plotter
    # # volume normalize copied from openmc.UnstructuredMesh.write_data_to_vtk()
    # v /= t.find_filter(openmc.MeshFilter).mesh.volumes.ravel()
    return PKDict(
        field_data=v.tolist(),
        min_field=v.min(),
        max_field=v.max(),
        num_particles=frame_args.sim_in.models.settings.particles,
        summaryData=PKDict(
            tally=frame_args.tally,
            sourceParticles=_sample_sources(
                _source_filename(frame_args.sim_in),
                frame_args.numSampleSourceParticles,
            ),
        ),
    )


def stateful_compute_verify_geometry(data, **kwargs):
    """Ensures the standard material db is available and returns the state of the
    geometry animation directory.
    """

    # TODO(pjm): the MGXS energy list should be a dynamically computed enum
    # import openmc.mgxs

    # def sort_name(value):
    #     m = re.search(r'^(.*?)\-(\d+)', value)
    #     assert m
    #     return f"{m.group(1)} {m.group(2).zfill(5)}"

    # enum.EnergyGroup = [n[0] for n in sorted(
    #     map(lambda v: [v, sort_name(v)], openmc.mgxs.GROUP_STRUCTURES.keys()),
    #     key=lambda v: v[1],
    # )]

    _standard_material_path()
    return PKDict(
        hasGeometry=simulation_db.simulation_dir(SIM_TYPE, sid=data.simulationId)
        .join(data.args.modelName)
        .exists()
    )


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


def stateful_compute_get_standard_material_names(data, **kwargs):
    res = []
    with _standard_material_open() as f:
        return PKDict(names=tuple(f))


def stateful_compute_get_standard_material(data, **kwargs):
    v = None
    with _standard_material_open() as f:
        g = f[f"/{data.args.name}"]
        v = PKDict(
            density_g_cc=g.attrs["density_g_cc"],
            elements=[[pkcompat.from_bytes(x[0]), x[1]] for x in g["elements"][:]],
            nuclides=[[pkcompat.from_bytes(x[0]), x[1]] for x in g["nuclides"][:]],
        )
    res = PKDict(
        density=v.density_g_cc,
        density_units="g/cc",
        components=[],
    )
    m, c = (
        ("add_element", "elements")
        if data.args.wantElements
        else ("add_nuclide", "nuclides")
    )
    for e in v[c]:
        res.components.append(
            _SIM_DATA.model_defaults("materialComponent").pkupdate(
                component=m,
                name=e[0],
                percent=e[1],
            ),
        )
    return PKDict(
        material=res,
    )


def stateful_compute_save_weight_windows_file_to_lib(data, **kwargs):
    n = _format_file_name(data.args.name, "ww")
    _SIM_DATA.lib_file_write(
        _SIM_DATA.lib_file_name_with_model_field(
            "settings",
            "weightWindowsFile",
            n,
        ),
        simulation_db.simulation_dir(SIM_TYPE, data.simulationId).join(
            _WEIGHT_WINDOWS_FILE
        ),
    )
    return PKDict(filename=n)


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
    if file_type == "geometryInput-dagmcFile":
        t = _SIM_DATA.get_input_file_type(str(path))
        if t == _SIM_DATA.INPUT_DAGMC and not h5py.is_hdf5(path):
            return "File is not a valid hdf5 file."
        if t == _SIM_DATA.INPUT_STEP:
            try:
                a = CAD_to_OpenMC.assembly.Assembly([path])
                a.load_stp_file(path)
            except Exception as e:
                pkdlog(
                    "path={} is not a valid step file error={} stack={}",
                    path,
                    e,
                    pkdexc(),
                )
                return "File is not a valid step file."
        # TODO(pjm): validate MCNP input file
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
                    cacheDir=sirepo.sim_run.cache_dir(_OPENMC_CACHE_DIR),
                    numThreads=data.models.openmcAnimation.ompThreads,
                    saveWeightWindowsFile=_generate_save_weight_windows(data),
                ),
                "openmc-sbatch.py",
            ),
        )
    else:
        # TODO(pjm): this can be combined after python version is updated,
        #   openmc is updated and FreeCAD is available
        if (
            _SIM_DATA.get_input_file_type(data.models.geometryInput.dagmcFile)
            == _SIM_DATA.INPUT_MCNP
        ):
            p = "new_python_required.py"
            pkio.write_text(
                run_dir.join(p),
                template_common.render_jinja(
                    SIM_TYPE,
                    PKDict(
                        mcnpFilename=_SIM_DATA.lib_file_name_with_model_field(
                            "geometryInput",
                            "dagmcFile",
                            data.models.geometryInput.dagmcFile,
                        ),
                    ),
                    "convert_mcnp.py",
                ),
            )
            with pkio.open_text(run_dir.join(f"x.log"), mode="w") as l:
                # TODO(pjm): this is a hacky work-around until we have a newer python
                #   when new python is available, the convert_mcnp.py.jinja can be combined
                #   with parameters.py.jinja
                subprocess.run(
                    ["/home/vagrant/.pyenv/versions/3.11.9/bin/python", p],
                    check=True,
                    stderr=l,
                    stdout=l,
                )
        pkio.write_text(
            run_dir.join(template_common.PARAMETERS_PYTHON_FILE),
            _generate_parameters_file(data, run_dir=run_dir),
        )
    if is_parallel:
        return template_common.get_exec_parameters_cmd()


def write_volume_outlines():
    import trimesh
    import dagmc_geometry_slice_plotter

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

    def _is_skip_dimension(tally_range, dim):
        # if more than 2 dimensions are below the minTallyResolution
        # then include all dimensions, see #7482
        m = SCHEMA.constants.minTallyResolution
        c = 0
        for idx in range(len(tally_range)):
            if len(tally_range[idx]) >= m:
                c += 1
        if c < 2:
            return False
        d1 = 1 if dim == "x" else 0
        d2 = 1 if dim == "z" else 2
        return len(tally_range[d1]) < m or len(tally_range[d2]) < m

    basis_vects = numpy.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    rots = numpy.array(
        [
            [[0, 1], [1, 0]],
            [[0, -1], [1, 0]],
            [[-1, 0], [0, 1]],
        ]
    )
    scale = SCHEMA.constants.geometryScale
    vol_meshes = PKDict()
    for mf in pkio.sorted_glob("*.ply"):
        vol_id = mf.purebasename
        with open(mf, "rb") as f:
            vol_meshes[vol_id] = trimesh.Trimesh(**trimesh.exchange.ply.load_ply(f))

    with h5py.File(_OUTLINES_FILE, "w") as hf:
        for tally_name, tally_mesh in _get_meshes():
            tally_grp = hf.create_group(tally_name)
            tally_ranges = [_center_range(tally_mesh, i) for i in range(3)]
            for i, dim in enumerate(["x", "y", "z"]):
                # don't include outlines of low resolution dimensions
                if _is_skip_dimension(tally_ranges, dim):
                    continue
                dim_grp = tally_grp.create_group(dim)
                for sl, pos in enumerate(tally_ranges[i]):
                    slice_grp = dim_grp.create_group(str(sl))
                    vol_group = slice_grp.create_group("volumes")
                    idx = 0
                    points = []
                    for vol_id, vol_mesh in vol_meshes.items():
                        indices = []
                        try:
                            polys = dagmc_geometry_slice_plotter.get_slice_coordinates(
                                dagmc_file_or_trimesh_object=vol_mesh,
                                plane_origin=pos * basis_vects[i],
                                plane_normal=basis_vects[i],
                            )
                            for poly in [scale * p.T for p in polys]:
                                pts = [numpy.dot(rots[i], p).tolist() for p in poly]
                                indices.append([idx, len(pts)])
                                idx += len(pts)
                                for pt in pts:
                                    points.append(pt)
                        except ValueError:
                            # no intersection at this plane position
                            pass
                        if len(indices):
                            vol_group.create_dataset(vol_id, data=indices)
                    slice_grp.create_dataset("points", data=points)


def _batch_sequence(settings):
    res = []
    b = 1
    if settings.run_mode == "eigenvalue":
        b += settings.inactive
    while b < settings.batches:
        res.append(b)
        b += settings.outputInterval
    res.append(settings.batches)
    return res


def _cleanup_statepoint_files(run_dir, data, frame_count, is_running):
    s = run_dir.join(_statepoint_filename(data, frame_count - 1))
    if s.exists():
        t = s.mtime()
        for f in pkio.sorted_glob(run_dir.join("statepoint.*")):
            t2 = f.mtime()
            if t2 < t:
                if is_running and t - t2 < 15:
                    # keep files around for 15 seconds extra if running
                    # to prevent deletions from happening while the requested plot is processed
                    continue
                pkio.unchecked_remove(f)


def _energy_plot(run_dir, data, frame_index):
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
    t = openmc.StatePoint(
        run_dir.join(_statepoint_filename(data, frame_index))
    ).get_tally(name=tally_name)
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


def _generate_angle(angle, qcall):
    if angle._type == "None":
        return angle._type
    args = []
    if angle._type == "isotropic":
        pass
    elif angle._type == "monodirectional":
        args.append(_generate_array(angle.reference_uvw))
    elif angle._type == "polarAzimuthal":
        args += [_generate_distribution(angle[v], qcall) for v in ["mu", "phi"]]
        args.append(_generate_array(angle.reference_uvw))
    else:
        raise AssertionError("unknown angle type: {}".format(angle._type))
    return _generate_call(angle._type, args)


def _generate_array(arr):
    return "[" + ", ".join([str(v) for v in arr]) + "]"


def _generate_call(name, args):
    return "openmc.stats." + name[0].upper() + name[1:] + "(" + ", ".join(args) + ")"


def _generate_distribution(dist, qcall):
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
                    ),
                    qcall=qcall,
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


def _generate_materials(data, errors):
    res = ""
    material_vars = []
    is_mgxs = data.models.settings.materialDefinition == "mgxs"
    for v in data.models.volumes.values():
        if "material" not in v:
            continue
        n = f"m{v.volId}"
        material_vars.append(n)
        res += f"# {v.name}\n"
        res += f'{n} = openmc.Material(name="{v.key}", material_id={v.volId})\n'
        if is_mgxs:
            res += f'{n}.set_density("macro", 1.0)\n'
            res += f'{n}.add_macroscopic(openmc.Macroscopic("{v.key}"))\n'
            continue
        if v.material.get("density"):
            res += (
                f'{n}.set_density("{v.material.density_units}", {v.material.density})\n'
            )
        if v.material.depletable == "1":
            res += f"{n}.depletable = True\n"
        if "temperature" in v.material and v.material.temperature:
            res += f"{n}.temperature = {v.material.temperature}\n"
        if "volume" in v.material and v.material.volume:
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
        errors.append("No materials defined for volumes")
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


def _generate_parameters_file(data, run_dir=None, qcall=None):
    report = data.get("report", "")
    if report == "tallyReport":
        return ""
    res, v = template_common.generate_parameters_file(data)
    v.dagmcFilename, intermediate = _SIM_DATA.get_geometry_input_filenames(data)
    if intermediate:
        if _SIM_DATA.get_input_file_type(intermediate) == _SIM_DATA.INPUT_STEP:
            v.stepFilename = intermediate
        elif _SIM_DATA.get_input_file_type(intermediate) == _SIM_DATA.INPUT_MCNP:
            v.mcnpFilename = intermediate
            data.models.geometryInput.materialsFile = None
            v.materialsFile = "materials2.xml"
    if report == "dagmcAnimation":
        v.volumeInfoFile = _VOLUME_INFO_FILE
        if data.models.geometryInput.materialsFile:
            v.materialsFile = _SIM_DATA.materials_filename(data)
        return template_common.render_jinja(SIM_TYPE, v, "extract_dagmc.py")
    v.isPythonSource = False if run_dir else True
    if v.isPythonSource:
        v.materialDirectory = "."
        v.isSBATCH = False
    else:
        v.materialDirectory = sirepo.sim_run.cache_dir(_OPENMC_CACHE_DIR)
        v.isSBATCH = _is_sbatch_run_mode(data)
    if data.models.settings.materialDefinition == "mgxs":
        v.mgxsFile = _SIM_DATA.lib_file_name_with_model_field(
            "settings",
            "mgxsFile",
            data.models.settings.mgxsFile,
        )
    else:
        v.mgxsFile = _MGXS_FILE
    v.batchSequence = _batch_sequence(data.models.settings)
    v.weightWindowsMesh = _generate_mesh(data.models.weightWindowsMesh)
    v.weightWindowsFile = _SIM_DATA.lib_file_name_with_model_field(
        "settings",
        "weightWindowsFile",
        data.models.settings.weightWindowsFile,
    )
    v.runCommand = _generate_run_mode(data, v)
    errors = []
    v.materials = _generate_materials(data, errors)
    v.sources = _generate_sources(data, errors, qcall)
    v.sourceFile = _source_filename(data)
    v.maxSampleSourceParticles = SCHEMA.model.openmcAnimation.numSampleSourceParticles[
        5
    ]
    v.tallies = _generate_tallies(data, errors)
    v.hasGraveyard = _has_graveyard(data)
    v.region = _region(data)
    v.planes = _planes(data)
    v.generateMGXS = (
        data.models.settings.materialDefinition == "library"
        and data.models.settings.generateMGXS == "1"
    )
    if len(errors):
        e = ", ".join(errors)
        return f'raise AssertionError("Unable to generate sim: {e}")'
    if not v.isSBATCH and not v.isPythonSource:
        v.saveWeightWindowsFile = _generate_save_weight_windows(data)
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


def _generate_save_weight_windows(data):
    if data.models.settings.varianceReduction in (
        "weight_windows_mesh",
        "weight_windows_tally",
    ):
        return f"""
import sirepo.sim_data
sirepo.sim_data.get_class("{ SIM_TYPE }").put_sim_file(
    "{ data.models.simulation.simulationId }",
    "{ _WEIGHT_WINDOWS_FILE }",
    "{ _WEIGHT_WINDOWS_FILE }",
)
"""
    return ""


def _generate_source(source, qcall):
    if source.get("type") == "file" and source.get("file"):
        return f"openmc.FileSource(\"{_SIM_DATA.lib_file_name_with_model_field('source', 'file', source.file)}\")"
    if source.space._type == "box":
        # TODO(pjm): move only_fissionable outside of box
        c = f"{{'fissionable': {source.space.only_fissionable == '1'}}}"
    else:
        c = "None"
    return f"""openmc.IndependentSource(
        space={_generate_space(source.space, qcall)},
        angle={_generate_angle(source.angle, qcall)},
        energy={_generate_distribution(source.energy, qcall)},
        time={_generate_distribution(source.time, qcall)},
        strength={source.strength},
        particle="{source.particle}",
        constraints={c},
    )"""


def _generate_sources(data, errors, qcall):
    if not len(data.models.settings.sources):
        errors.append("No Settings Sources defined")
        return
    return ",\n".join(
        [_generate_source(s, qcall) for s in data.models.settings.sources]
    )


def _generate_space(space, qcall):
    if space._type == "None":
        return space._type
    args = []
    if space._type == "box":
        args += [
            _generate_array(space.lower_left),
            _generate_array(space.upper_right),
        ]
    elif space._type == "cartesianIndependent":
        args += [_generate_distribution(space[v], qcall) for v in ["x", "y", "z"]]
    elif space._type == "cylindricalIndependent":
        args += [_generate_distribution(space[v], qcall) for v in ["r", "phi", "z"]]
        args.append(f"origin={_generate_array(space.origin)}")
    elif space._type == "point":
        args.append(_generate_array(space.xyz))
    elif space._type == "sphericalIndependent":
        args += [_generate_distribution(space[v], qcall) for v in ["r", "theta", "phi"]]
        args.append(f"origin={_generate_array(space.origin)}")
    else:
        raise AssertionError("unknown space type: {}".format(space._type))
    return _generate_call(space._type, args)


def _generate_tallies(data, errors):
    if not len(data.models.settings.tallies):
        errors.append("No Tallies defined")
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
            raise AssertionError("Unknown filter selected: {}".format(f._type))
    if not len(tally.scores):
        raise AssertionError(f"Tally {tally.name} has no scores defined")
    res += f"""]
t{tally._index + 1}.scores = [{','.join(["'" + s.score + "'" for s in tally.scores])}]
"""
    if tally.estimator != "default":
        res += f"""t{tally._index + 1}.estimator = "{tally.estimator}"
"""
    if len(tally.nuclides):
        res += f"""
t{tally._index + 1}.nuclides = [{','.join(["'" + s.nuclide + "'" for s in tally.nuclides if s.nuclide])}]
"""
    return res


def _get_batch(count, data):
    settings = data.models.settings
    c = 0
    iterations = 1
    if settings.varianceReduction == "weight_windows_tally":
        iterations = data.models.weightWindows.iterations
    for i in range(iterations):
        b = 1
        if settings.run_mode == "eigenvalue":
            b += settings.inactive
        while b < settings.batches:
            c += 1
            if c == count:
                return b
            b += settings.outputInterval
            if b > settings.batches:
                b = settings.batches
        c += 1
        if c == count:
            return b
    raise AssertionError(f"Count outside of batch window: {count}")


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


def _parse_openmc_log(run_dir, log_filename="run.log"):
    return template_common.LogParser(
        run_dir,
        log_filename=log_filename,
        default_msg="An unknown error occurred, check OpenMC log for details",
        # ERROR: Cannot tally flux for an individual nuclide.
        error_patterns=(
            re.compile(r"^\s*ValueError:\s*(.*)$", re.IGNORECASE),
            re.compile(r"^\s*Error:\s*(.*)$", re.IGNORECASE),
            re.compile(r"AssertionError: (.*)"),
        ),
    ).parse_for_errors()


def _parse_run_stats(run_dir, out):
    def _get_groups(match, *args):
        res = []
        for i in args:
            g = match.group(i)
            if g is not None:
                res.append(g.strip())
        return res

    RE_F = "\d*\.\d+"
    log = run_dir.join(template_common.RUN_LOG)
    if not log.exists():
        return
    out.iteration = 0
    mode = "start"
    with pkio.open_text(log) as f:
        for line in f:
            if mode in ("start", "results") and re.search(
                r" FIXED SOURCE TRANSPORT SIMULATION", line
            ):
                mode = "fixed"
                out.iteration += 1
            elif mode in ("start", "results") and re.search(
                r" K EIGENVALUE SIMULATION", line
            ):
                mode = "eigen"
                out.iteration += 1
                out.eigenvalue = []
            elif mode in ("fixed", "eigen") and re.search(
                r"\s*=+>\s+RESULTS\s+<=+\s*", line
            ):
                mode = "results"
                out.results = []
            elif mode == "fixed":
                m = re.match(r"^ Simulating batch (\d+)", line)
                if m:
                    out.batch = int(m.group(1))
            elif mode == "eigen":
                m = re.match(
                    rf"^\s+(\d+)/1\s+({RE_F})\s*({RE_F})?\s*(\+/-)?\s*({RE_F})?", line
                )
                if m:
                    out.batch = int(m.group(1))
                    out.eigenvalue.append(
                        PKDict(
                            batch=out.batch,
                            val=_get_groups(m, 2, 3, 5),
                        )
                    )
            elif mode == "results":
                m = re.match(rf"^\s+(.+)\s=\s({RE_F})\s+\+/-\s+({RE_F})", line)
                if m:
                    out.results.append(_get_groups(m, 1, 2, 3))


def _format_file_name(name, suffix):
    return name.strip().replace(" ", "-") + f"-{suffix}.h5"


def _frame_count_for_batch(batch, data):
    settings = data.models.settings
    c = 0
    iterations = 1
    if settings.varianceReduction == "weight_windows_tally":
        iterations = data.models.weightWindows.iterations
    for i in range(iterations):
        b = 1
        if settings.run_mode == "eigenvalue":
            b += settings.inactive
        if batch < settings.batches * i + b:
            return c
        while b < settings.batches:
            c += 1
            b += settings.outputInterval
            if b > settings.batches:
                b = settings.batches
            if batch < settings.batches * i + b:
                return c
        c += 1
    return c


def _percent_complete(run_dir, is_running):
    res = PKDict(
        frameCount=0,
        percentComplete=0,
        iteration=0,
        batch=0,
    )
    _parse_run_stats(run_dir, res)
    data = simulation_db.read_json(run_dir.join(template_common.INPUT_BASE_NAME))
    batches = data.models.settings.batches
    if res.iteration > 0:
        res.frameCount = _frame_count_for_batch(
            res.batch + (res.iteration - 1) * batches,
            data,
        )
    if is_running:
        if res.batch == 1 or (
            _frame_count_for_batch(res.batch - 1 + (res.iteration - 1) * batches, data)
            != res.frameCount
        ):
            if res.frameCount > 0:
                res.frameCount -= 1
        total = batches
        if data.models.settings.varianceReduction == "weight_windows_tally":
            total *= data.models.weightWindows.iterations
        res.percentComplete = (res.batch + (res.iteration - 1) * batches) * 100 / total
        if res.percentComplete < 0:
            res.percentComplete = 0
    if res.frameCount:
        _cleanup_statepoint_files(run_dir, data, res.frameCount, is_running)
        res.tallies = data.models.settings.tallies
        if not is_running:
            res.hasWeightWindowsFile = run_dir.join(_WEIGHT_WINDOWS_FILE).exists()
            res.hasMGXSFile = run_dir.join(_MGXS_FILE).exists()

    return res


def _planes(data):
    res = ""
    for i, p in enumerate(data.models.reflectivePlanes.planesList):
        res += f"""
    p{i + 1} = openmc.Plane(
        a={p.A},
        b={p.B},
        c={p.C},
        d={p.D},
        boundary_type="reflective",
    )
"""
    return res


def _region(data):
    res = ""
    for i, p in enumerate(data.models.reflectivePlanes.planesList):
        if res:
            res += " & "
        if p.inside == "1":
            res += f"+p{i + 1}"
        else:
            res += f"-p{i + 1}"
    return res


def _source_filename(data):
    return f"source.{data.models.settings.batches}.h5"


def _standard_material_open():
    return h5py.File(_standard_material_path(), mode="r")


def _standard_material_path():
    def _remote_uri(base):
        return "/".join(
            sirepo.feature_config.for_sim_type(SIM_TYPE).data_storage_url,
            base,
        )

    m = sirepo.sim_run.cache_dir(_STANDARD_MATERIAL_CACHE_DIR).join(
        STANDARD_MATERIALS_DB
    )
    if m.exists():
        return m
    n = STANDARD_MATERIALS_DB_GZ
    if not _SIM_DATA.lib_file_exists(n):
        c = _SIM_DATA.sim_db_client(n)
        c.save_from_url(_remote_uri(), c.uri(_SIM_DATA.LIB_DIR, n))
    with gzip.open(str(_SIM_DATA.lib_file_abspath(n)), "rb") as f:
        m.write_binary(f)
    return m


def _statepoint_filename(data, frame_index=None):
    b = data.models.settings.batches
    if frame_index is not None:
        b = str(_get_batch(frame_index + 1, data)).zfill(int(math.log10(b) + 1))
    return f"statepoint.{b}.h5"


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
        if i == {ww.iterations - 1}:
            openmc.lib.export_weight_windows(filename="{_WEIGHT_WINDOWS_FILE}")
        wws.update_magic(tally)
        openmc.lib.settings.weight_windows_on = True
"""
